#!/usr/bin/env bash
set -euo pipefail

# Get project directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Source common utilities
source "$SCRIPT_DIR/common.sh"

# Configuration
ADMIN_HOST="${ADMIN_HOST:-127.0.0.1}"
ADMIN_PORT="${ADMIN_PORT:-8000}"

# Set trap for cleanup on exit
trap cleanup EXIT

# Check prerequisites
check_prerequisites

if ! grep -q 'ADMIN_API_KEY=.' .env 2>/dev/null; then
  log "WARNING: ADMIN_API_KEY is not set in .env"
  log "FIX:     Add ADMIN_API_KEY=<your-secret> to .env"
  log "         The admin server will refuse to start without it."
fi

log "Prerequisites OK"

# Load configuration from .env (lower priority than environment variables)
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
load_env_var RAG_SERVICE_URL
load_env_var RAG_SERVICE_API_KEY
load_env_var LLM_NUM_CTX
load_env_var LLM_DISABLE_THINKING
load_env_var EMBED_CTX_SIZE
load_env_var EMBED_UBATCH_SIZE

log "Loaded .env overrides (if any)"

# Set URL defaults after loading from .env
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
MINIO_URL="${S3_ENDPOINT_URL:-${MINIO_URL:-http://localhost:9000}}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
RAG_SERVICE_URL="${RAG_SERVICE_URL:-http://localhost:8001}"

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

export RAG_SERVICE_URL RAG_SERVICE_API_KEY

# Sync dependencies (all LLM/embedding providers are now included in cafetera-core)
log "Syncing Python dependencies..."
if ! uv sync; then
  log "ERROR: Failed to sync Python dependencies"
  log "FIX:   Check pyproject.toml is valid and uv.lock is not corrupted"
  log "       Try: uv lock --upgrade && uv sync"
  exit 1
fi
log "Dependencies OK"

# Auto-detect NVIDIA GPU and install CUDA-enabled PyTorch on Linux
if [[ "$(uname -s)" == "Linux" ]] && command_exists nvidia-smi && nvidia-smi >/dev/null 2>&1; then
  log "NVIDIA GPU detected — installing CUDA-enabled PyTorch..."
  if uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128 --reinstall; then
    log "CUDA PyTorch installed successfully"
  else
    log "WARNING: Failed to install CUDA PyTorch, continuing with CPU version"
  fi
fi

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
if [[ "$LLM_PROVIDER" == "ollama" || "$EMBEDDING_PROVIDER" == "ollama" ]]; then
  start_ollama_providers "$OLLAMA_URL" "$LLM_PROVIDER" "$LLM_MODEL" "$EMBEDDING_PROVIDER" "$EMBEDDING_MODEL"
fi

if [[ "$LLM_PROVIDER" == "openai" || "$EMBEDDING_PROVIDER" == "openai" ]]; then
  validate_openai_providers "$LLM_PROVIDER" "$LLM_API_KEY" "$LLM_MODEL" "$EMBEDDING_PROVIDER" "$EMBEDDING_API_KEY" "$EMBEDDING_MODEL"
fi

if [[ "$LLM_PROVIDER" == "llamacpp" || "$EMBEDDING_PROVIDER" == "llamacpp" ]]; then
  start_llamacpp_providers "$SCRIPT_DIR" "$LLM_PROVIDER" "$LLM_BASE_URL" "$EMBEDDING_PROVIDER" "$EMBEDDING_BASE_URL"
fi

if [[ "$LLM_PROVIDER" == "openai" ]]; then
  log "LLM provider: OpenAI (remote, no local server needed)"
fi
if [[ "$EMBEDDING_PROVIDER" == "openai" ]]; then
  log "Embedding provider: OpenAI (remote, no local server needed)"
fi

# Start RAG service in background
log "Starting RAG service..."
uv run python scripts/rag_server.py > /tmp/rag_server.log 2>&1 &
BG_PIDS+=("$!")
log "RAG service PID=$!"

if ! wait_for_service "RAG Service" "${RAG_SERVICE_URL}/api/health" 30 2; then
  log "ERROR: RAG service failed to start"
  log "FIX:   Check /tmp/rag_server.log for errors"
  log "       Make sure port 8001 is not in use: lsof -i :8001"
  exit 1
fi

# Print startup info
echo
log "=========================================="
log "Starting admin server"
log "=========================================="
log "Admin UI:    http://${ADMIN_HOST}:${ADMIN_PORT}/documents"
log "API docs:    http://${ADMIN_HOST}:${ADMIN_PORT}/docs"
log "RAG Service: $RAG_SERVICE_URL"
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
