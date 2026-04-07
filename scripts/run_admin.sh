#!/usr/bin/env bash
set -euo pipefail

# Get project directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Configuration
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
MINIO_URL="${MINIO_URL:-http://localhost:9000}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
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

cleanup() {
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
      LLM_MODEL="qwen3.5:4b-q4_K_M"
      LLM_BASE_URL="http://localhost:11434"
      LLM_API_KEY=""
      ;;
    2|openai)
      LLM_PROVIDER="openai"
      LLM_MODEL="gpt-4o-mini"
      LLM_BASE_URL="https://api.openai.com/v1"
      read -r -p "[admin] Enter OpenAI API key: " LLM_API_KEY
      ;;
    3|llamacpp)
      LLM_PROVIDER="llamacpp"
      LLM_MODEL="local-model"
      LLM_BASE_URL="http://localhost:8080"
      LLM_API_KEY=""
      ;;
    *)
      log "Invalid choice, using ollama"
      LLM_PROVIDER="ollama"
      LLM_MODEL="qwen3.5:4b-q4_K_M"
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
  read -r -p "[admin] Enter choice [1-2, Enter=1]: " embed_choice

  case "${embed_choice:-1}" in
    1|ollama)
      EMBEDDING_PROVIDER="ollama"
      EMBEDDING_MODEL="qwen3-embedding:4b-q4_K_M"
      EMBEDDING_BASE_URL="http://localhost:11434"
      EMBEDDING_API_KEY=""
      ;;
    2|openai)
      EMBEDDING_PROVIDER="openai"
      EMBEDDING_MODEL="qwen3-embedding:4b-q4_K_M"
      EMBEDDING_BASE_URL="https://api.openai.com/v1"
      read -r -p "[admin] Enter OpenAI API key: " EMBEDDING_API_KEY
      ;;
    *)
      log "Invalid choice, using ollama"
      EMBEDDING_PROVIDER="ollama"
      EMBEDDING_MODEL="qwen3-embedding:4b-q4_K_M"
      EMBEDDING_BASE_URL="http://localhost:11434"
      EMBEDDING_API_KEY=""
      ;;
  esac

  export EMBEDDING_PROVIDER EMBEDDING_MODEL EMBEDDING_BASE_URL EMBEDDING_API_KEY
  log "Selected Embedding provider: $EMBEDDING_PROVIDER"
}

select_llm_provider
select_embedding_provider

# Sync dependencies with provider-specific extras
UV_EXTRAS=""
if [[ "$LLM_PROVIDER" == "ollama" || "$EMBEDDING_PROVIDER" == "ollama" ]]; then
  UV_EXTRAS="$UV_EXTRAS --extra ollama"
fi
if [[ "$LLM_PROVIDER" == "openai" || "$LLM_PROVIDER" == "llamacpp" || "$EMBEDDING_PROVIDER" == "openai" ]]; then
  UV_EXTRAS="$UV_EXTRAS --extra openai_compatible"
fi

log "Syncing Python dependencies (extras:${UV_EXTRAS:- none})..."
# shellcheck disable=SC2086
if ! uv sync $UV_EXTRAS; then
  log "ERROR: Failed to sync Python dependencies"
  log "FIX:   Check pyproject.toml is valid and uv.lock is not corrupted"
  log "       Try: uv lock --upgrade && uv sync $UV_EXTRAS"
  exit 1
fi
log "Dependencies OK"

# Start infrastructure
log "Starting infrastructure via docker compose..."
docker compose up -d

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

# Check Ollama (only if needed)
if [[ "$LLM_PROVIDER" == "ollama" || "$EMBEDDING_PROVIDER" == "ollama" ]]; then
  log "Checking Ollama at $OLLAMA_URL..."
  if curl -sf "$OLLAMA_URL" >/dev/null 2>&1; then
    log "Ollama is running"
  else
    log "WARNING: Ollama is not running at $OLLAMA_URL"
    log "WARNING: RAG features (document Q&A) will not work"
    log "FIX:    Start Ollama: ./scripts/run_ollama_qwen.sh"
    log "        Or install: https://ollama.com/download"
  fi
fi

# Check llamacpp (only if needed)
if [[ "$LLM_PROVIDER" == "llamacpp" ]]; then
  LLAMACPP_URL="http://localhost:8080"
  log "Checking llamacpp server at $LLAMACPP_URL..."
  if curl -sf "$LLAMACPP_URL" >/dev/null 2>&1; then
    log "llamacpp server is running"
  else
    log "WARNING: llamacpp server is not running at $LLAMACPP_URL"
    log "WARNING: LLM features (document Q&A) will not work"
    log "FIX:    Start llama-server: ./scripts/run_llama_qwen.sh"
    log "        Make sure the model file exists in models/"
  fi
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
