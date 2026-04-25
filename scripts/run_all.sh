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
  echo "[run-all] $*"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

mask_credentials() {
  # Strip userinfo (user:password@) from URLs for safe logging
  echo "$1" | sed -E 's|://[^@]+@|://***@|'
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

# PIDs of background processes to kill on exit
BG_PIDS=()

cleanup() {
  log "Shutting down..."
  
  log "Stopping docker compose services..."
  docker compose down 2>/dev/null || true
  
  # Kill background processes
  for pid in ${BG_PIDS[@]+"${BG_PIDS[@]}"}; do
    if kill -0 "$pid" 2>/dev/null; then
      log "Stopping background process (PID=$pid)"
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
  
  log "All services stopped"
}

# Set trap for cleanup on exit
trap cleanup EXIT INT TERM

# Check prerequisites
log "Checking prerequisites..."

if ! command_exists docker; then
  log "ERROR: docker is not installed or not in PATH"
  log "FIX:   Install Docker Desktop: https://docs.docker.com/get-docker/"
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

if ! grep -q 'VK_ACCESS_TOKEN=.' .env 2>/dev/null; then
  log "WARNING: VK_ACCESS_TOKEN is not set in .env"
  log "FIX:     Add VK_ACCESS_TOKEN=<your-token> to .env"
  log "         The VK bot will refuse to start without it."
fi

if ! grep -q 'VK_GROUP_ID=.' .env 2>/dev/null; then
  log "WARNING: VK_GROUP_ID is not set in .env"
  log "FIX:     Add VK_GROUP_ID=<your-group-id> to .env"
  log "         The VK bot needs this to connect to your VK group."
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
load_env_var OLLAMA_URL
load_env_var LLM_N_GPU_LAYERS
load_env_var EMBED_N_GPU_LAYERS
load_env_var OLLAMA_NUM_GPU
# NOTE: Do NOT load DATABASE_URL, QDRANT_URL, S3_ENDPOINT_URL from .env
# These will be overridden with Docker service names below

log "Loaded .env overrides (if any)"

# Set Docker-specific URL defaults (services accessed via Docker network)
# These URLs are used INSIDE the Docker container
QDRANT_CONTAINER_URL="http://qdrant:6333"
MINIO_CONTAINER_URL="http://minio:9000"
DATABASE_CONTAINER_URL="postgresql://cafetera:cafetera@postgres:5432/cafetera"

# Host URLs for health checks (docker-compose exposes ports to localhost)
QDRANT_URL="http://localhost:6333"
MINIO_URL="http://localhost:9000"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

# Use container URLs for the Docker environment
DATABASE_URL="${DATABASE_CONTAINER_URL}"

# Interactive provider selection
select_llm_provider() {
  echo
  log "Select LLM provider:"
  echo "  1) ollama (default)"
  echo "  2) openai"
  echo "  3) llamacpp"
  read -r -p "[run-all] Enter choice [1-3, Enter=1]: " llm_choice

  case "${llm_choice:-1}" in
    1|ollama)
      LLM_PROVIDER="ollama"
      LLM_MODEL="${LLM_MODEL:-qwen3.5:4b-q4_K_M}"
      LLM_BASE_URL="http://host.docker.internal:11434"
      LLM_API_KEY=""
      ;;
    2|openai)
      LLM_PROVIDER="openai"
      LLM_MODEL="${LLM_MODEL:-gpt-4o-mini}"
      LLM_BASE_URL="https://api.openai.com/v1"
      read -rs -p "[run-all] Enter OpenAI API key: " LLM_API_KEY
      echo
      ;;
    3|llamacpp)
      LLM_PROVIDER="llamacpp"
      LLM_MODEL="${LLM_MODEL:-local-model}"
      LLM_BASE_URL="http://host.docker.internal:8080"
      LLM_API_KEY=""
      ;;
    *)
      log "Invalid choice, using ollama"
      LLM_PROVIDER="ollama"
      LLM_MODEL="${LLM_MODEL:-qwen3.5:4b-q4_K_M}"
      LLM_BASE_URL="http://host.docker.internal:11434"
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
  read -r -p "[run-all] Enter choice [1-3, Enter=1]: " embed_choice

  case "${embed_choice:-1}" in
    1|ollama)
      EMBEDDING_PROVIDER="ollama"
      EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding:4b-q4_K_M}"
      EMBEDDING_BASE_URL="http://host.docker.internal:11434"
      EMBEDDING_API_KEY=""
      ;;
    2|openai)
      EMBEDDING_PROVIDER="openai"
      EMBEDDING_MODEL="${EMBEDDING_MODEL:-text-embedding-3-small}"
      EMBEDDING_BASE_URL="https://api.openai.com/v1"
      read -rs -p "[run-all] Enter OpenAI API key: " EMBEDDING_API_KEY
      echo
      ;;
    3|llamacpp)
      EMBEDDING_PROVIDER="llamacpp"
      EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding}"
      EMBEDDING_BASE_URL="http://host.docker.internal:8090/v1"
      EMBEDDING_API_KEY=""
      ;;
    *)
      log "Invalid choice, using ollama"
      EMBEDDING_PROVIDER="ollama"
      EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding:4b-q4_K_M}"
      EMBEDDING_BASE_URL="http://host.docker.internal:11434"
      EMBEDDING_API_KEY=""
      ;;
  esac

  export EMBEDDING_PROVIDER EMBEDDING_MODEL EMBEDDING_BASE_URL EMBEDDING_API_KEY
  log "Selected Embedding provider: $EMBEDDING_PROVIDER"
}

select_llm_provider
select_embedding_provider

# Start infrastructure
log "Starting infrastructure via docker compose..."
docker compose up -d

# Wait for PostgreSQL (uses docker compose exec)
if ! wait_for_postgres; then
  log "ERROR: PostgreSQL failed to start"
  log "FIX:   Check docker logs: docker compose logs postgres"
  log "       Make sure port 5432 is not in use: lsof -i :5432"
  exit 1
fi

# Wait for Qdrant (uses docker-compose healthcheck with bash /dev/tcp)
if ! wait_for_healthy "qdrant"; then
  log "ERROR: Qdrant failed to become healthy"
  log "FIX:   Check docker logs: docker compose logs qdrant"
  exit 1
fi

# Wait for MinIO (uses docker-compose healthcheck with mc ready local)
if ! wait_for_healthy "minio"; then
  log "ERROR: MinIO failed to become healthy"
  log "FIX:   Check docker logs: docker compose logs minio"
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

# Launch providers based on selection
if [[ "$LLM_PROVIDER" == "ollama" || "$EMBEDDING_PROVIDER" == "ollama" ]]; then
  start_ollama_providers
fi

if [[ "$LLM_PROVIDER" == "openai" ]]; then
  log "LLM provider: OpenAI (remote, no local server needed)"
fi
if [[ "$EMBEDDING_PROVIDER" == "openai" ]]; then
  log "Embedding provider: OpenAI (remote, no local server needed)"
fi

# docker-compose.yml handles env_file and service URLs directly

# Print startup info
echo
log "=========================================="
log "Starting Cafetera HR Bot System"
log "=========================================="
log "Admin UI:     http://${ADMIN_HOST}:${ADMIN_PORT}/documents"
log "API docs:     http://${ADMIN_HOST}:${ADMIN_PORT}/docs"
log "VK Bot:       Polling mode (no webhook needed)"
log ""
log "Infrastructure:"
log "  Qdrant:      $(mask_credentials "$QDRANT_URL") (host) / $(mask_credentials "$QDRANT_CONTAINER_URL") (container)"
log "  MinIO:       $(mask_credentials "$MINIO_URL") (host) / $(mask_credentials "$MINIO_CONTAINER_URL") (container)"
log "  PostgreSQL:  $(mask_credentials "$DATABASE_CONTAINER_URL")"
log ""
log "AI Services:"
log "  LLM:         $LLM_PROVIDER ($LLM_MODEL)"
log "  Embedding:   $EMBEDDING_PROVIDER ($EMBEDDING_MODEL)"
if [[ "$LLM_PROVIDER" == "ollama" || "$EMBEDDING_PROVIDER" == "ollama" ]]; then
  log "  Ollama:      $OLLAMA_URL"
fi
log "=========================================="
echo
log "Press Ctrl+C to stop all services"
echo

echo
log "=========================================="
log "All services are running!"
log "=========================================="
log "Admin UI:  http://${ADMIN_HOST}:${ADMIN_PORT}/documents"
log "VK Bot:    Running in polling mode"
log ""
log "View logs:"
log "  docker compose logs -f"
log ""
log "Stop:      Press Ctrl+C"
log "=========================================="
echo

# Follow compose logs, keeping the script alive until Ctrl+C
docker compose logs -f
