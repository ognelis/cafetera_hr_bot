#!/usr/bin/env bash
set -euo pipefail

# Get project directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Configuration
ADMIN_HOST="${ADMIN_HOST:-127.0.0.1}"
ADMIN_PORT="${ADMIN_PORT:-8000}"

HEALTH_RETRIES=30
HEALTH_INTERVAL=2

log() {
  echo "[admin] $*"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

mask_credentials() {
  # Strip userinfo (user:password@) from URLs for safe logging
  echo "$1" | sed -E 's|://[^@]+@|://***@|'
}

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

# PIDs of background processes to kill on exit
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

# Set trap for cleanup on exit
trap cleanup EXIT

# Check prerequisites
log "Checking prerequisites..."

if ! command_exists docker; then
  log "ERROR: docker is not installed or not in PATH"
  log "FIX:   Install Docker Desktop: https://docs.docker.com/get-docker/"
  exit 1
fi

if ! command_exists uv; then
  log "ERROR: uv is not installed or not in PATH"
  log "FIX:   Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

if [[ ! -f ".env" ]]; then
  log "ERROR: .env file not found in project root ($PROJECT_DIR)"
  log "FIX:   Copy the example and fill in your values:"
  log "       cp .env.example .env && nano .env"
  exit 1
fi

if ! grep -q 'ADMIN_API_KEY=.' .env 2>/dev/null; then
  log "WARNING: ADMIN_API_KEY is not set in .env"
  log "FIX:     Add ADMIN_API_KEY=<your-secret> to .env"
  log "         The admin server will refuse to start without it."
fi

log "Prerequisites OK"

# Load configuration from .env (lower priority than environment variables)
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

load_env_var LLM_PROVIDER
load_env_var LLM_MODEL
load_env_var LLM_BASE_URL
load_env_var LLM_API_KEY
load_env_var EMBEDDING_PROVIDER
load_env_var EMBEDDING_MODEL
load_env_var EMBEDDING_BASE_URL
load_env_var EMBEDDING_API_KEY
load_env_var QDRANT_URL
load_env_var S3_ENDPOINT_URL
load_env_var OLLAMA_URL
load_env_var LLM_N_GPU_LAYERS
load_env_var EMBED_N_GPU_LAYERS
load_env_var OLLAMA_NUM_GPU
load_env_var DATABASE_URL

log "Loaded .env overrides (if any)"

# Set URL defaults after loading from .env
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
MINIO_URL="${S3_ENDPOINT_URL:-${MINIO_URL:-http://localhost:9000}}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

# Interactive provider selection
select_llm_provider() {
  echo
  log "Select LLM provider:"
  echo "  1) ollama (default)"
  echo "  2) openai"
  echo "  3) llamacpp"
  read -r -p "[admin] Enter choice [1-3, Enter=1]: " llm_choice

  case "${llm_choice:-1}" in
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
      read -rs -p "[admin] Enter OpenAI API key: " LLM_API_KEY
      echo
      ;;
    3|llamacpp)
      LLM_PROVIDER="llamacpp"
      LLM_MODEL="${LLM_MODEL:-local-model}"
      LLM_BASE_URL="http://localhost:8080"
      LLM_API_KEY=""
      ;;
    *)
      log "Invalid choice, using ollama"
      LLM_PROVIDER="ollama"
      LLM_MODEL="${LLM_MODEL:-qwen3.5:4b-q4_K_M}"
      LLM_BASE_URL="http://localhost:11434"
      LLM_API_KEY=""
      ;;
  esac

  export LLM_PROVIDER LLM_MODEL LLM_BASE_URL LLM_API_KEY
  log "Selected LLM provider: $LLM_PROVIDER"
}

select_embedding_provider() {
  echo
  log "Select Embedding provider:"
  echo "  1) ollama (default)"
  echo "  2) openai"
  echo "  3) llamacpp"
  read -r -p "[admin] Enter choice [1-3, Enter=1]: " embed_choice

  case "${embed_choice:-1}" in
    1|ollama)
      EMBEDDING_PROVIDER="ollama"
      EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding:4b-q4_K_M}"
      EMBEDDING_BASE_URL="http://localhost:11434"
      EMBEDDING_API_KEY=""
      ;;
    2|openai)
      EMBEDDING_PROVIDER="openai"
      EMBEDDING_MODEL="${EMBEDDING_MODEL:-text-embedding-3-small}"
      EMBEDDING_BASE_URL="https://api.openai.com/v1"
      read -rs -p "[admin] Enter OpenAI API key: " EMBEDDING_API_KEY
      echo
      ;;
    3|llamacpp)
      EMBEDDING_PROVIDER="llamacpp"
      EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding}"
      EMBEDDING_BASE_URL="http://localhost:8090/v1"
      EMBEDDING_API_KEY=""
      ;;
    *)
      log "Invalid choice, using ollama"
      EMBEDDING_PROVIDER="ollama"
      EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding:4b-q4_K_M}"
      EMBEDDING_BASE_URL="http://localhost:11434"
      EMBEDDING_API_KEY=""
      ;;
  esac

  export EMBEDDING_PROVIDER EMBEDDING_MODEL EMBEDDING_BASE_URL EMBEDDING_API_KEY
  log "Selected Embedding provider: $EMBEDDING_PROVIDER"
}

select_llm_provider
select_embedding_provider

# Sync dependencies (all LLM/embedding providers are now included in cafetera-core)
log "Syncing Python dependencies..."
if ! uv sync; then
  log "ERROR: Failed to sync Python dependencies"
  log "FIX:   Check pyproject.toml is valid and uv.lock is not corrupted"
  log "       Try: uv lock --upgrade && uv sync"
  exit 1
fi
log "Dependencies OK"

# Start infrastructure
log "Starting infrastructure via docker compose..."
docker compose up -d qdrant minio postgres

# Wait for PostgreSQL
if ! wait_for_postgres; then
  log "ERROR: PostgreSQL failed to start"
  log "FIX:   Check docker logs: docker compose logs postgres"
  log "       Make sure port 5432 is not in use: lsof -i :5432"
  exit 1
fi

# Wait for Qdrant
if ! wait_for_service "Qdrant" "${QDRANT_URL}/healthz"; then
  log "ERROR: Qdrant failed to start at ${QDRANT_URL}"
  log "FIX:   Check docker logs: docker compose logs qdrant"
  log "       Make sure port 6333 is not in use: lsof -i :6333"
  exit 1
fi

# Wait for MinIO
if ! wait_for_service "MinIO" "${MINIO_URL}/minio/health/live"; then
  log "ERROR: MinIO failed to start at ${MINIO_URL}"
  log "FIX:   Check docker logs: docker compose logs minio"
  log "       Make sure port 9000 is not in use: lsof -i :9000"
  exit 1
fi

# Start local LLM and embedding providers if needed
start_ollama_providers() {
  log "Checking Ollama at $OLLAMA_URL..."
  if ! curl -sf "$OLLAMA_URL" >/dev/null 2>&1; then
    if ! command_exists ollama; then
      log "ERROR: Ollama is not installed and not running at $OLLAMA_URL"
      log "FIX:   Install Ollama: https://ollama.com/download"
      log "       Then re-run this script."
      exit 1
    fi
    log "Ollama is not running. Starting Ollama server..."
    OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}" ollama serve >/tmp/ollama.log 2>&1 &
    BG_PIDS+=("$!")
    if ! wait_for_service "Ollama" "$OLLAMA_URL" 30 1; then
      log "ERROR: Ollama failed to start. Check /tmp/ollama.log"
      exit 1
    fi
  else
    log "Ollama is already running"
  fi

  # Pull LLM model if ollama is used for LLM
  if [[ "$LLM_PROVIDER" == "ollama" ]]; then
    log "Ensuring LLM model '$LLM_MODEL' is available..."
    if ! ollama list 2>/dev/null | awk '{print $1}' | grep -Fxq "$LLM_MODEL"; then
      log "Pulling LLM model '$LLM_MODEL'..."
      if ! ollama pull "$LLM_MODEL"; then
        log "ERROR: Failed to pull LLM model '$LLM_MODEL'"
        log "FIX:   Check model name is correct: ollama list"
        log "       Available models: https://ollama.com/library"
        exit 1
      fi
    fi
    # Verify model is usable
    if ! ollama list 2>/dev/null | awk '{print $1}' | grep -Fxq "$LLM_MODEL"; then
      log "ERROR: LLM model '$LLM_MODEL' not found in Ollama after pull"
      log "FIX:   Check model name spelling (must include quantization suffix)"
      log "       Run: ollama list  — to see available models"
      exit 1
    fi
    log "LLM model '$LLM_MODEL' is ready"
  fi

  # Pull embedding model if ollama is used for embeddings
  if [[ "$EMBEDDING_PROVIDER" == "ollama" ]]; then
    log "Ensuring embedding model '$EMBEDDING_MODEL' is available..."
    if ! ollama list 2>/dev/null | awk '{print $1}' | grep -Fxq "$EMBEDDING_MODEL"; then
      log "Pulling embedding model '$EMBEDDING_MODEL'..."
      if ! ollama pull "$EMBEDDING_MODEL"; then
        log "ERROR: Failed to pull embedding model '$EMBEDDING_MODEL'"
        log "FIX:   Check model name is correct: ollama list"
        log "       Available models: https://ollama.com/library"
        exit 1
      fi
    fi
    # Verify model is usable
    if ! ollama list 2>/dev/null | awk '{print $1}' | grep -Fxq "$EMBEDDING_MODEL"; then
      log "ERROR: Embedding model '$EMBEDDING_MODEL' not found in Ollama after pull"
      log "FIX:   Check model name spelling (must include quantization suffix)"
      log "       Run: ollama list  — to see available models"
      exit 1
    fi
    log "Embedding model '$EMBEDDING_MODEL' is ready"
  fi
}

start_llamacpp_providers() {
  if ! command_exists llama-server; then
    log "ERROR: llama-server not found in PATH"
    log "FIX:   Install llama.cpp: https://github.com/ggerganov/llama.cpp"
    exit 1
  fi

  LLAMACPP_LLM_URL="http://localhost:8080"
  LLAMACPP_EMBED_URL="http://localhost:8090"

  # Start LLM server if not running
  if [[ "$LLM_PROVIDER" == "llamacpp" ]]; then
    log "Checking llamacpp LLM server at $LLAMACPP_LLM_URL..."
    if ! curl -sf "$LLAMACPP_LLM_URL" >/dev/null 2>&1; then
      log "Starting llamacpp LLM server in background..."
      "$SCRIPT_DIR/run_llama_llm.sh" >/tmp/llama_llm.log 2>&1 &
      BG_PIDS+=("$!")
      if ! wait_for_service "llamacpp LLM" "$LLAMACPP_LLM_URL" 30 2; then
        log "ERROR: llamacpp LLM server failed to start. Check /tmp/llama_llm.log"
        exit 1
      fi
    else
      log "llamacpp LLM server is already running"
    fi
    # Verify LLM server loaded model and responds
    log "Verifying llamacpp LLM server has a loaded model..."
    if ! curl -sf "${LLAMACPP_LLM_URL}/v1/models" >/dev/null 2>&1; then
      log "WARNING: Could not verify model on llamacpp LLM server"
      log "FIX:    Check /tmp/llama_llm.log for errors"
      log "        Ensure model file exists in models/"
    else
      log "llamacpp LLM server model verified"
    fi
  fi

  # Start embedding server if not running
  if [[ "$EMBEDDING_PROVIDER" == "llamacpp" ]]; then
    log "Checking llamacpp embedding server at $LLAMACPP_EMBED_URL..."
    if ! curl -sf "$LLAMACPP_EMBED_URL" >/dev/null 2>&1; then
      log "Starting llamacpp embedding server in background..."
      "$SCRIPT_DIR/run_llama_embeddings.sh" >/tmp/llama_embed.log 2>&1 &
      BG_PIDS+=("$!")
      if ! wait_for_service "llamacpp Embedding" "$LLAMACPP_EMBED_URL" 30 2; then
        log "ERROR: llamacpp embedding server failed to start. Check /tmp/llama_embed.log"
        exit 1
      fi
    else
      log "llamacpp embedding server is already running"
    fi
    # Verify embedding server loaded model and responds
    log "Verifying llamacpp embedding server has a loaded model..."
    if ! curl -sf "${LLAMACPP_EMBED_URL}/v1/models" >/dev/null 2>&1; then
      log "WARNING: Could not verify model on llamacpp embedding server"
      log "FIX:    Check /tmp/llama_embed.log for errors"
      log "        Ensure embedding model file exists in models/"
    else
      log "llamacpp embedding server model verified"
    fi
  fi
}

# Launch providers based on selection
if [[ "$LLM_PROVIDER" == "ollama" || "$EMBEDDING_PROVIDER" == "ollama" ]]; then
  start_ollama_providers
fi

if [[ "$LLM_PROVIDER" == "llamacpp" || "$EMBEDDING_PROVIDER" == "llamacpp" ]]; then
  start_llamacpp_providers
fi

if [[ "$LLM_PROVIDER" == "openai" ]]; then
  log "LLM provider: OpenAI (remote, no local server needed)"
fi
if [[ "$EMBEDDING_PROVIDER" == "openai" ]]; then
  log "Embedding provider: OpenAI (remote, no local server needed)"
fi

# Print startup info
echo
log "=========================================="
log "Starting admin server"
log "=========================================="
log "Admin UI:    http://${ADMIN_HOST}:${ADMIN_PORT}/documents"
log "API docs:    http://${ADMIN_HOST}:${ADMIN_PORT}/docs"
log "Qdrant:      $QDRANT_URL"
log "MinIO:       $MINIO_URL"
log "PostgreSQL:  $(mask_credentials "${DATABASE_URL:-postgresql://localhost:5432/cafetera}")"
log "LLM:         $LLM_PROVIDER ($LLM_MODEL)"
log "Embedding:   $EMBEDDING_PROVIDER ($EMBEDDING_MODEL)"
if [[ "$LLM_PROVIDER" == "ollama" || "$EMBEDDING_PROVIDER" == "ollama" ]]; then
  log "Ollama:      $OLLAMA_URL"
fi
log "=========================================="
echo
log "Press Ctrl+C to stop"
echo

# Start admin server (foreground)
uv run python scripts/admin_server.py
