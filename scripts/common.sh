#!/usr/bin/env bash
# ─── Common Shell Utilities ──────────────────────────────────────────────────
# Shared helper functions for all orchestration scripts.
# Source this file: source "$(dirname "$0")/common.sh"
# ─────────────────────────────────────────────────────────────────────────────

# ─── Logging ─────────────────────────────────────────────────────────────────

log() {
  echo "[$(basename "$0" .sh)] $*"
}

mask_credentials() {
  # Strip userinfo (user:password@) from URLs for safe logging
  echo "$1" | sed -E 's|://[^@]+@|://***@|'
}

# ─── Prerequisite Checks ─────────────────────────────────────────────────────

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

check_docker() {
  if ! command_exists docker; then
    log "ERROR: docker is not installed or not in PATH"
    log "FIX:   Install Docker Desktop: https://docs.docker.com/get-docker/"
    exit 1
  fi
}

check_uv() {
  if ! command_exists uv; then
    log "ERROR: uv is not installed or not in PATH"
    log "FIX:   Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
  fi
}

check_env_file() {
  if [[ ! -f ".env" ]]; then
    log "ERROR: .env file not found in project root ($(pwd))"
    log "FIX:   Copy the example and fill in your values:"
    log "       cp .env.example .env && nano .env"
    exit 1
  fi
}

# Check all common prerequisites at once
check_prerequisites() {
  log "Checking prerequisites..."
  check_docker
  check_uv
  check_env_file
}

# Check prerequisites for scripts that don't need uv (e.g., ragas/run.sh)
check_prerequisites_no_uv() {
  log "Checking prerequisites..."
  check_docker
  check_env_file
}

# Validate that required environment variables are set
check_required_env_vars() {
  local missing=0
  for var in "$@"; do
    if [[ -z "${!var:-}" ]]; then
      log "ERROR: Required environment variable $var is not set"
      missing=1
    fi
  done
  if [[ $missing -eq 1 ]]; then
    log "FIX:   Check your .env file or set the missing variables"
    exit 1
  fi
}

# ─── Environment Variable Loading ────────────────────────────────────────────

load_env_var() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]] && grep -qE "^${var_name}=" .env 2>/dev/null; then
    local val
    val=$(grep -E "^${var_name}=" .env | head -1 | cut -d= -f2- | sed 's/^["'\''"]*//;s/["'\''"]*$//')
    if [[ -n "$val" ]]; then
      export "$var_name=$val"
    fi
  fi
}

# ─── Service Health Checks ───────────────────────────────────────────────────

HEALTH_RETRIES="${HEALTH_RETRIES:-30}"
HEALTH_INTERVAL="${HEALTH_INTERVAL:-2}"

# Longer timeout for llama.cpp servers (models may need to download first)
LLAMACPP_HEALTH_RETRIES="${LLAMACPP_HEALTH_RETRIES:-300}"
LLAMACPP_HEALTH_INTERVAL="${LLAMACPP_HEALTH_INTERVAL:-3}"

wait_for_service() {
  local name="$1"
  local url="$2"
  local retries="${3:-$HEALTH_RETRIES}"
  local interval="${4:-$HEALTH_INTERVAL}"

  log "Waiting for $name at $url..."

  for i in $(seq 1 "$retries"); do
    if curl -sf "$url" >/dev/null 2>&1; then
      log "$name is ready"
      return 0
    fi
    if [[ $i -lt $retries ]]; then
      sleep "$interval"
    fi
  done

  log "ERROR: $name did not become ready after $retries attempts"
  return 1
}

wait_for_postgres() {
  local retries="${1:-$HEALTH_RETRIES}"
  local interval="${2:-$HEALTH_INTERVAL}"

  log "Waiting for PostgreSQL..."

  for i in $(seq 1 "$retries"); do
    if docker compose exec -T postgres pg_isready -U cafetera >/dev/null 2>&1; then
      log "PostgreSQL is ready"
      return 0
    fi
    if [[ $i -lt $retries ]]; then
      sleep "$interval"
    fi
  done

  log "ERROR: PostgreSQL did not become ready after $retries attempts"
  return 1
}

wait_for_healthy() {
  local service="$1"
  local retries="${2:-$HEALTH_RETRIES}"
  local interval="${3:-$HEALTH_INTERVAL}"

  log "Waiting for $service to be healthy..."

  for i in $(seq 1 "$retries"); do
    # Try JSON format first
    local health_status
    health_status=$(docker compose ps --format json "$service" 2>/dev/null | jq -r '.Health' 2>/dev/null || echo "")
    
    # Fallback to table format if jq failed
    if [[ -z "$health_status" ]]; then
      # Extract health status from "Up X minutes (health: starting)" or "healthy"
      health_status=$(docker compose ps "$service" 2>/dev/null | tail -n +2 | grep -oP 'health: \K[a-z]+' || echo "")
    fi
    
    if [[ "$health_status" == "healthy" ]]; then
      log "$service is healthy"
      return 0
    fi
    
    if [[ $i -lt $retries ]]; then
      sleep "$interval"
    fi
  done

  log "ERROR: $service did not become healthy after $retries attempts"
  log "FIX:   Check docker logs: docker compose logs $service"
  return 1
}

# ─── Host Detection (Local vs Remote) ────────────────────────────────────────

# Check if URL points to localhost (should be started locally)
# Returns 0 if local, 1 if remote/docker-internal
is_local_host() {
  local url="$1"
  # Extract host from URL (remove protocol, path, and port)
  local host
  host=$(echo "$url" | sed -E 's|https?://||' | sed -E 's|/.*||' | sed -E 's|:[0-9]+$||')
  # Check if it's localhost, 127.0.0.1, or 0.0.0.0
  if [[ "$host" == "localhost" || "$host" == "127.0.0.1" || "$host" == "0.0.0.0" ]]; then
    return 0  # true, is local
  fi
  return 1  # false, is remote or docker-internal
}

# ─── Interactive Provider Selection ─────────────────────────────────────────

# Check if interactive provider menu should be skipped (SKIP_PROVIDER_MENU=true).
# Default: false (menu is always shown).
# When enabled, select_*_provider() functions apply defaults from .env without
# prompting. Requires LLM_PROVIDER / EMBEDDING_PROVIDER set in .env; for openai
# also requires LLM_API_KEY / EMBEDDING_API_KEY.
skip_provider_menu_enabled() {
  load_env_var SKIP_PROVIDER_MENU
  case "${SKIP_PROVIDER_MENU:-false}" in
    true|TRUE|True|1|yes|YES|Yes|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

# Convert provider name to menu number
provider_to_number() {
  case "$1" in
    ollama) echo "1" ;;
    openai) echo "2" ;;
    llamacpp) echo "3" ;;
    custom) echo "4" ;;
    *) echo "1" ;;
  esac
}

# Infer provider name from URL pattern
infer_provider_from_url() {
  local url="$1"
  case "$url" in
    *localhost:11434*|*127.0.0.1:11434*) echo "ollama" ;;
    *localhost:8080*|*127.0.0.1:8080*) echo "llamacpp" ;;
    *localhost:8090*|*127.0.0.1:8090*) echo "llamacpp" ;;
    *api.openai.com*) echo "openai" ;;
    *) echo "" ;;
  esac
}

# Select LLM provider interactively
# Args: $1=log_prefix
# Always sets localhost URLs. configure_docker_urls() converts them for Docker.
# When SKIP_PROVIDER_MENU=true, applies defaults from .env without prompting.
select_llm_provider() {
  local prefix="${1:-run}"

  # Non-interactive path: honour SKIP_PROVIDER_MENU=true and use .env values.
  if skip_provider_menu_enabled; then
    local provider="${LLM_PROVIDER:-llamacpp}"
    case "$provider" in
      ollama)
        LLM_MODEL="${LLM_MODEL:-qwen3.5:4b-q4_K_M}"
        LLM_BASE_URL="http://localhost:11434"
        LLM_API_KEY=""
        ;;
      openai)
        LLM_MODEL="${LLM_MODEL:-gpt-4o-mini}"
        LLM_BASE_URL="${LLM_BASE_URL:-https://api.openai.com/v1}"
        if [[ -z "${LLM_API_KEY:-}" ]]; then
          log "ERROR: SKIP_PROVIDER_MENU=true and LLM_PROVIDER=openai, but LLM_API_KEY is not set in .env"
          log "FIX:   Set LLM_API_KEY=sk-... in .env, or unset SKIP_PROVIDER_MENU"
          exit 1
        fi
        ;;
      llamacpp)
        LLM_MODEL="${LLM_MODEL:-local-model}"
        LLM_BASE_URL="http://localhost:8080"
        LLM_API_KEY=""
        ;;
      *)
        log "ERROR: SKIP_PROVIDER_MENU=true but LLM_PROVIDER='$provider' is not supported (expected: ollama|openai|llamacpp)"
        log "FIX:   Set LLM_PROVIDER to one of the supported values in .env, or unset SKIP_PROVIDER_MENU"
        exit 1
        ;;
    esac
    export LLM_PROVIDER="$provider" LLM_MODEL LLM_BASE_URL LLM_API_KEY
    log "$prefix: SKIP_PROVIDER_MENU=true - LLM provider: $LLM_PROVIDER ($LLM_MODEL) [non-interactive]"
    return 0
  fi

  echo
  # Determine current provider from .env or infer from URL
  local current_provider="${LLM_PROVIDER:-}"
  local current_model="${LLM_MODEL:-Qwen3.5-9B-Q4_K_M}"

  if [[ -z "$current_provider" && -n "${LLM_BASE_URL:-}" ]]; then
    current_provider=$(infer_provider_from_url "${LLM_BASE_URL}")
  fi
  current_provider="${current_provider:-llamacpp}"

  log "$prefix: LLM Provider Configuration:"
  log "$prefix:   Default: $current_provider ($current_model)"
  log "$prefix:   Options:"
  echo "    1) ollama"
  echo "    2) openai"
  echo "    3) llamacpp"
  echo "    4) custom URL"
  read -r -p "[$prefix] Select LLM provider [1-4, Enter=$current_provider]: " llm_choice

  case "${llm_choice:-$(provider_to_number "$current_provider")}" in
    1|ollama)
      LLM_PROVIDER="ollama"
      LLM_MODEL="${LLM_MODEL:-qwen3.5:4b-q4_K_M}"
      LLM_BASE_URL="http://localhost:11434"
      LLM_API_KEY=""
      ;;
    2|openai)
      LLM_PROVIDER="openai"
      LLM_MODEL="${LLM_MODEL:-gpt-4o-mini}"
      LLM_BASE_URL="https://api.openai.com/v1"
      read -rs -p "[$prefix] Enter OpenAI API key: " LLM_API_KEY
      echo
      ;;
    3|llamacpp)
      LLM_PROVIDER="llamacpp"
      LLM_MODEL="${LLM_MODEL:-local-model}"
      LLM_BASE_URL="http://localhost:8080"
      LLM_API_KEY=""
      ;;
    4|custom)
      log "$prefix: Custom URL — select API format:"
      echo "    1) openai-compatible (vLLM, Together, Fireworks, etc.)"
      echo "    2) ollama (native Ollama API)"
      echo "    3) llamacpp (OpenAI-compatible via llama-server)"
      read -r -p "[$prefix] Select API format [1-3, Enter=1]: " api_choice
      case "${api_choice:-1}" in
        1) LLM_PROVIDER="openai" ;;
        2) LLM_PROVIDER="ollama" ;;
        3) LLM_PROVIDER="llamacpp" ;;
        *) LLM_PROVIDER="openai" ;;
      esac
      LLM_MODEL="${LLM_MODEL:-gpt-4o-mini}"
      read -r -p "[$prefix] Enter LLM base URL (e.g. https://api.example.com/v1): " LLM_BASE_URL
      read -rs -p "[$prefix] Enter API key (or press Enter for none): " LLM_API_KEY
      echo
      ;;
    *)
      log "Invalid choice, using: $current_provider"
      LLM_PROVIDER="$current_provider"
      LLM_MODEL="$current_model"
      LLM_BASE_URL="${LLM_BASE_URL:-http://localhost:8080}"
      ;;
  esac

  export LLM_PROVIDER LLM_MODEL LLM_BASE_URL LLM_API_KEY
  log "$prefix: LLM provider: $LLM_PROVIDER ($LLM_MODEL)"
}

# Select Embedding provider interactively
# Args: $1=log_prefix
# Always sets localhost URLs. configure_docker_urls() converts them for Docker.
# When SKIP_PROVIDER_MENU=true, applies defaults from .env without prompting.
select_embedding_provider() {
  local prefix="${1:-run}"

  # Non-interactive path: honour SKIP_PROVIDER_MENU=true and use .env values.
  if skip_provider_menu_enabled; then
    local provider="${EMBEDDING_PROVIDER:-llamacpp}"
    case "$provider" in
      ollama)
        EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding:0.6b-fp16}"
        EMBEDDING_BASE_URL="http://localhost:11434"
        EMBEDDING_API_KEY=""
        ;;
      openai)
        EMBEDDING_MODEL="${EMBEDDING_MODEL:-text-embedding-3-small}"
        EMBEDDING_BASE_URL="${EMBEDDING_BASE_URL:-https://api.openai.com/v1}"
        if [[ -z "${EMBEDDING_API_KEY:-}" ]]; then
          log "ERROR: SKIP_PROVIDER_MENU=true and EMBEDDING_PROVIDER=openai, but EMBEDDING_API_KEY is not set in .env"
          log "FIX:   Set EMBEDDING_API_KEY=sk-... in .env, or unset SKIP_PROVIDER_MENU"
          exit 1
        fi
        ;;
      llamacpp)
        EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding}"
        EMBEDDING_BASE_URL="http://localhost:8090/v1"
        EMBEDDING_API_KEY=""
        ;;
      *)
        log "ERROR: SKIP_PROVIDER_MENU=true but EMBEDDING_PROVIDER='$provider' is not supported (expected: ollama|openai|llamacpp)"
        log "FIX:   Set EMBEDDING_PROVIDER to one of the supported values in .env, or unset SKIP_PROVIDER_MENU"
        exit 1
        ;;
    esac
    export EMBEDDING_PROVIDER="$provider" EMBEDDING_MODEL EMBEDDING_BASE_URL EMBEDDING_API_KEY
    log "$prefix: SKIP_PROVIDER_MENU=true - Embedding provider: $EMBEDDING_PROVIDER ($EMBEDDING_MODEL) [non-interactive]"
    return 0
  fi

  echo
  # Determine current provider from .env or infer from URL
  local current_provider="${EMBEDDING_PROVIDER:-}"
  local current_model="${EMBEDDING_MODEL:-Qwen3-Embedding-0.6B-f16}"

  if [[ -z "$current_provider" && -n "${EMBEDDING_BASE_URL:-}" ]]; then
    current_provider=$(infer_provider_from_url "${EMBEDDING_BASE_URL}")
  fi
  current_provider="${current_provider:-llamacpp}"

  log "$prefix: Embedding Provider Configuration:"
  log "$prefix:   Default: $current_provider ($current_model)"
  log "$prefix:   Options:"
  echo "    1) ollama"
  echo "    2) openai"
  echo "    3) llamacpp"
  echo "    4) custom URL"
  read -r -p "[$prefix] Select Embedding provider [1-4, Enter=$current_provider]: " embed_choice

  case "${embed_choice:-$(provider_to_number "$current_provider")}" in
    1|ollama)
      EMBEDDING_PROVIDER="ollama"
      EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding:0.6b-fp16}"
      EMBEDDING_BASE_URL="http://localhost:11434"
      EMBEDDING_API_KEY=""
      ;;
    2|openai)
      EMBEDDING_PROVIDER="openai"
      EMBEDDING_MODEL="${EMBEDDING_MODEL:-text-embedding-3-small}"
      EMBEDDING_BASE_URL="https://api.openai.com/v1"
      read -rs -p "[$prefix] Enter OpenAI API key: " EMBEDDING_API_KEY
      echo
      ;;
    3|llamacpp)
      EMBEDDING_PROVIDER="llamacpp"
      EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding}"
      EMBEDDING_BASE_URL="http://localhost:8090/v1"
      EMBEDDING_API_KEY=""
      ;;
    4|custom)
      log "$prefix: Custom URL — select API format:"
      echo "    1) openai-compatible (vLLM, Together, Fireworks, etc.)"
      echo "    2) ollama (native Ollama API)"
      echo "    3) llamacpp (OpenAI-compatible via llama-server)"
      read -r -p "[$prefix] Select API format [1-3, Enter=1]: " api_choice
      case "${api_choice:-1}" in
        1) EMBEDDING_PROVIDER="openai" ;;
        2) EMBEDDING_PROVIDER="ollama" ;;
        3) EMBEDDING_PROVIDER="llamacpp" ;;
        *) EMBEDDING_PROVIDER="openai" ;;
      esac
      EMBEDDING_MODEL="${EMBEDDING_MODEL:-text-embedding-3-small}"
      read -r -p "[$prefix] Enter Embedding base URL (e.g. https://api.example.com/v1): " EMBEDDING_BASE_URL
      read -rs -p "[$prefix] Enter API key (or press Enter for none): " EMBEDDING_API_KEY
      echo
      ;;
    *)
      log "Invalid choice, using: $current_provider"
      EMBEDDING_PROVIDER="$current_provider"
      EMBEDDING_MODEL="$current_model"
      EMBEDDING_BASE_URL="${EMBEDDING_BASE_URL:-http://localhost:11434}"
      ;;
  esac

  export EMBEDDING_PROVIDER EMBEDDING_MODEL EMBEDDING_BASE_URL EMBEDDING_API_KEY
  log "$prefix: Embedding provider: $EMBEDDING_PROVIDER ($EMBEDDING_MODEL)"
}

# ─── Docker URL Configuration ───────────────────────────────────────────────

# Automatically set Docker-accessible URLs based on provider configuration
# This eliminates the need to manually configure DOCKER_*_BASE_URL in .env
configure_docker_urls() {
  local llm_provider="$1"
  local llm_base_url="${2:-http://localhost:8080}"
  local embedding_provider="$3"
  local embedding_base_url="${4:-http://localhost:8090/v1}"
  local reranker_url="${5:-http://localhost:8082}"

  # Helper: convert localhost URL to host.docker.internal URL
  local_to_docker_url() {
    local url="$1"
    if is_local_host "$url"; then
      # Replace localhost or 127.0.0.1 with host.docker.internal
      echo "$url" | sed 's|localhost|host.docker.internal|g; s|127\.0\.0\.1|host.docker.internal|g'
    else
      echo "$url"
    fi
  }

  # Configure LLM URL for Docker
  if [[ "$llm_provider" == "openai" ]]; then
    # OpenAI URLs are already accessible from Docker
    export DOCKER_LLM_BASE_URL="$llm_base_url"
  else
    # Convert localhost to host.docker.internal for local providers
    export DOCKER_LLM_BASE_URL="$(local_to_docker_url "$llm_base_url")"
  fi

  # Export provider names for Docker Compose
  export LLM_PROVIDER="$llm_provider"
  export EMBEDDING_PROVIDER="$embedding_provider"

  # Configure Embedding URL for Docker
  if [[ "$embedding_provider" == "openai" ]]; then
    # OpenAI URLs are already accessible from Docker
    export DOCKER_EMBEDDING_BASE_URL="$embedding_base_url"
  else
    # Convert localhost to host.docker.internal for local providers
    export DOCKER_EMBEDDING_BASE_URL="$(local_to_docker_url "$embedding_base_url")"
  fi

  # Configure Reranker URL for Docker
  export DOCKER_RERANKER_BASE_URL="$(local_to_docker_url "$reranker_url")"

  log "Docker URLs configured:"
  log "  LLM:        $DOCKER_LLM_BASE_URL"
  log "  Embedding:  $DOCKER_EMBEDDING_BASE_URL"
  log "  Reranker:   $DOCKER_RERANKER_BASE_URL"
}

# ─── Cleanup Management ──────────────────────────────────────────────────────

# Array to track background process PIDs
BG_PIDS=()

cleanup() {
  log "Shutting down..."
  for pid in ${BG_PIDS[@]+"${BG_PIDS[@]}"}; do
    if kill -0 "$pid" 2>/dev/null; then
      log "Stopping background process (PID=$pid)"
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
  log "Stopping docker services..."
  docker compose down 2>/dev/null || true
}

# ─── Ollama Provider Management ──────────────────────────────────────────────

start_ollama_providers() {
  local ollama_url="${1:-http://localhost:11434}"
  local llm_provider="$2"
  local llm_model="${3:-qwen3.5:4b-q4_K_M}"
  local embedding_provider="$4"
  local embedding_model="${5:-qwen3-embedding:0.6b-fp16}"

  log "Checking Ollama at $ollama_url..."
  if ! curl -sf "$ollama_url" >/dev/null 2>&1; then
    if ! command_exists ollama; then
      log "ERROR: Ollama is not installed and not running at $ollama_url"
      log "FIX:   Install Ollama: https://ollama.com/download"
      log "       Then re-run this script."
      exit 1
    fi
    log "Ollama is not running. Starting Ollama server..."
    OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}" ollama serve >/tmp/ollama.log 2>&1 &
    BG_PIDS+=("$!")
    if ! wait_for_service "Ollama" "$ollama_url" 30 1; then
      log "ERROR: Ollama failed to start. Check /tmp/ollama.log"
      exit 1
    fi
  else
    log "Ollama is already running"
  fi

  # Pull LLM model if ollama is used for LLM
  if [[ "$llm_provider" == "ollama" ]]; then
    log "Ensuring LLM model '$llm_model' is available..."
    if ! ollama list 2>/dev/null | awk '{print $1}' | grep -Fxq "$llm_model"; then
      log "Pulling LLM model '$llm_model'..."
      if ! ollama pull "$llm_model"; then
        log "ERROR: Failed to pull LLM model '$llm_model'"
        log "FIX:   Check model name is correct: ollama list"
        log "       Available models: https://ollama.com/library"
        exit 1
      fi
    fi
    # Verify model is usable
    if ! ollama list 2>/dev/null | awk '{print $1}' | grep -Fxq "$llm_model"; then
      log "ERROR: LLM model '$llm_model' not found in Ollama after pull"
      log "FIX:   Check model name spelling (must include quantization suffix)"
      log "       Run: ollama list  — to see available models"
      exit 1
    fi
    log "LLM model '$llm_model' is ready"
  fi

  # Pull embedding model if ollama is used for embeddings
  if [[ "$embedding_provider" == "ollama" ]]; then
    log "Ensuring embedding model '$embedding_model' is available..."
    if ! ollama list 2>/dev/null | awk '{print $1}' | grep -Fxq "$embedding_model"; then
      log "Pulling embedding model '$embedding_model'..."
      if ! ollama pull "$embedding_model"; then
        log "ERROR: Failed to pull embedding model '$embedding_model'"
        log "FIX:   Check model name is correct: ollama list"
        log "       Available models: https://ollama.com/library"
        exit 1
      fi
    fi
    # Verify model is usable
    if ! ollama list 2>/dev/null | awk '{print $1}' | grep -Fxq "$embedding_model"; then
      log "ERROR: Embedding model '$embedding_model' not found in Ollama after pull"
      log "FIX:   Check model name spelling (must include quantization suffix)"
      log "       Run: ollama list  — to see available models"
      exit 1
    fi
    log "Embedding model '$embedding_model' is ready"
  fi
}

# ─── OpenAI Provider Management ──────────────────────────────────────────────

validate_openai_providers() {
  local llm_provider="$1"
  local llm_api_key="$2"
  local llm_model="${3:-gpt-4o-mini}"
  local embedding_provider="$4"
  local embedding_api_key="$5"
  local embedding_model="${6:-text-embedding-3-small}"

  # Validate LLM API key if OpenAI is used for LLM
  if [[ "$llm_provider" == "openai" ]]; then
    if [[ -z "$llm_api_key" ]]; then
      log "ERROR: OpenAI API key is required for LLM provider"
      log "FIX:   Set OPENAI_API_KEY in your .env file"
      exit 1
    fi
    log "OpenAI LLM configured: $llm_model"
  fi

  # Validate embedding API key if OpenAI is used for embeddings
  if [[ "$embedding_provider" == "openai" ]]; then
    if [[ -z "$embedding_api_key" ]]; then
      log "ERROR: OpenAI API key is required for Embedding provider"
      log "FIX:   Set OPENAI_API_KEY in your .env file"
      exit 1
    fi
    log "OpenAI Embedding configured: $embedding_model"
  fi

  if [[ "$llm_provider" == "openai" || "$embedding_provider" == "openai" ]]; then
    log "OpenAI provider validation passed"
  fi
}

# ─── llama.cpp Provider Management ───────────────────────────────────────────

start_llamacpp_providers() {
  local script_dir="$1"
  local llm_provider="$2"
  local llm_base_url="${3:-http://localhost:8080}"
  local embedding_provider="$4"
  local embedding_base_url="${5:-http://localhost:8090/v1}"

  if ! command_exists llama-server; then
    log "ERROR: llama-server not found in PATH"
    log "FIX:   Install llama.cpp: https://github.com/ggerganov/llama.cpp"
    exit 1
  fi

  # Default URLs for local llama.cpp servers
  local llamacpp_llm_url="http://localhost:8080"
  local llamacpp_embed_url="http://localhost:8090"

  # Start LLM server if not running and URL is local
  if [[ "$llm_provider" == "llamacpp" ]]; then
    if is_local_host "$llm_base_url"; then
      log "Checking llamacpp LLM server at $llamacpp_llm_url..."
      if ! curl -sf "$llamacpp_llm_url" >/dev/null 2>&1; then
        log "Starting llamacpp LLM server in background..."
        "$script_dir/run_llama_llm.sh" >/tmp/llama_llm.log 2>&1 &
        BG_PIDS+=("$!")
        log "Waiting for llamacpp LLM server (model may be downloading)..."
        if ! wait_for_service "llamacpp LLM" "$llamacpp_llm_url" "$LLAMACPP_HEALTH_RETRIES" "$LLAMACPP_HEALTH_INTERVAL"; then
          log "ERROR: llamacpp LLM server failed to start. Check /tmp/llama_llm.log"
          exit 1
        fi
      else
        log "llamacpp LLM server is already running"
      fi
      # Verify LLM server loaded model and responds
      log "Verifying llamacpp LLM server has a loaded model..."
      if ! curl -sf "${llamacpp_llm_url}/v1/models" >/dev/null 2>&1; then
        log "WARNING: Could not verify model on llamacpp LLM server"
        log "FIX:    Check /tmp/llama_llm.log for errors"
        log "        Ensure model file exists in models/"
      else
        log "llamacpp LLM server model verified"
      fi
    else
      log "LLM base URL ($llm_base_url) is not localhost — skipping local llamacpp LLM start"
    fi
  fi

  # Start embedding server if not running and URL is local
  if [[ "$embedding_provider" == "llamacpp" ]]; then
    if is_local_host "$embedding_base_url"; then
      log "Checking llamacpp embedding server at $llamacpp_embed_url..."
      if ! curl -sf "$llamacpp_embed_url" >/dev/null 2>&1; then
        log "Starting llamacpp embedding server in background..."
        "$script_dir/run_llama_embeddings.sh" >/tmp/llama_embed.log 2>&1 &
        BG_PIDS+=("$!")
        log "Waiting for llamacpp embedding server (model may be downloading)..."
        if ! wait_for_service "llamacpp Embedding" "$llamacpp_embed_url" "$LLAMACPP_HEALTH_RETRIES" "$LLAMACPP_HEALTH_INTERVAL"; then
          log "ERROR: llamacpp embedding server failed to start. Check /tmp/llama_embed.log"
          exit 1
        fi
      else
        log "llamacpp embedding server is already running"
      fi
      # Verify embedding server loaded model and responds
      log "Verifying llamacpp embedding server has a loaded model..."
      if ! curl -sf "${llamacpp_embed_url}/v1/models" >/dev/null 2>&1; then
        log "WARNING: Could not verify model on llamacpp embedding server"
        log "FIX:    Check /tmp/llama_embed.log for errors"
        log "        Ensure embedding model file exists in models/"
      else
        log "llamacpp embedding server model verified"
      fi
    else
      log "Embedding base URL ($embedding_base_url) is not localhost — skipping local llamacpp embedding start"
    fi
  fi
}

# ─── Reranker Management ─────────────────────────────────────────────────────

start_reranker_if_needed() {
  local project_dir="$1"
  local reranking_enabled="${2:-false}"
  local reranker_url="${3:-http://localhost:8082}"
  local docker_mode="${4:-true}"  # true=Docker (host.docker.internal), false=local (localhost)

  # Early exit if reranking is not enabled
  if [[ "$reranking_enabled" != "true" ]]; then
    return 0
  fi

  if is_local_host "$reranker_url"; then
    log "Checking reranker at ${reranker_url}..."
    if ! curl -sf "${reranker_url}/health" >/dev/null 2>&1; then
      if ! command_exists llama-server; then
        log "ERROR: llama-server not found and reranker not running at ${reranker_url}"
        log "FIX:   Install llama.cpp or start reranker manually: scripts/run_llama_reranker.sh"
        exit 1
      fi
      log "Starting reranker server in background..."
      "$project_dir/scripts/run_llama_reranker.sh" >/tmp/llama_reranker.log 2>&1 &
      BG_PIDS+=("$!")
      log "Waiting for reranker server (model may be downloading)..."
      if ! wait_for_service "Reranker" "${reranker_url}/health" "$LLAMACPP_HEALTH_RETRIES" "$LLAMACPP_HEALTH_INTERVAL"; then
        log "ERROR: Reranker failed to start. Check /tmp/llama_reranker.log"
        exit 1
      fi
    else
      log "Reranker is already running at ${reranker_url}"
    fi
    # Export URL appropriate for the runtime context
    if [[ "$docker_mode" == "true" ]]; then
      export RERANKER_URL="http://host.docker.internal:8082"
    else
      export RERANKER_URL="http://localhost:8082"
    fi
  else
    log "Reranker URL ($reranker_url) is not localhost — skipping local reranker start"
  fi
}
