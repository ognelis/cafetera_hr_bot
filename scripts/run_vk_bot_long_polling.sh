#!/usr/bin/env bash
set -euo pipefail

# Get project directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Source common utilities
source "$SCRIPT_DIR/common.sh"

# Set trap for cleanup on exit
trap cleanup EXIT

# Check prerequisites
check_prerequisites

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

if ! grep -q 'RAG_SERVICE_API_KEY=.' .env 2>/dev/null; then
  log "WARNING: RAG_SERVICE_API_KEY is not set in .env"
  log "FIX:     Add RAG_SERVICE_API_KEY=<your-secret> to .env"
  log "         The RAG service will run without authentication."
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
load_env_var OLLAMA_NUM_GPU
load_env_var DATABASE_URL
load_env_var RAG_SERVICE_URL
load_env_var RAG_SERVICE_API_KEY
load_env_var LLM_NUM_CTX
load_env_var LLM_DISABLE_THINKING
load_env_var EMBED_CTX_SIZE
load_env_var EMBED_UBATCH_SIZE
load_env_var RERANKING_ENABLED
load_env_var RERANKER_URL

log "Loaded .env overrides (if any)"

# Set URL defaults after loading from .env
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
MINIO_URL="${S3_ENDPOINT_URL:-${MINIO_URL:-http://localhost:9000}}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
RAG_SERVICE_URL="${RAG_SERVICE_URL:-http://localhost:8001}"

# Interactive provider selection (functions from common.sh)
select_llm_provider "vk-bot"
select_embedding_provider "vk-bot"

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

# Reranker — start if enabled and URL is local (local mode: RAG service runs on host)
start_reranker_if_needed "$PROJECT_DIR" "${RERANKING_ENABLED:-false}" "${RERANKER_URL:-http://localhost:8082}" "false"

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
log "Starting VK bot (Long Poll mode)"
log "=========================================="
log "VK Bot:      Polling mode (no webhook needed)"
log "RAG Service: $RAG_SERVICE_URL"
log "Qdrant:      $QDRANT_URL"
log "MinIO:       $MINIO_URL"
log "PostgreSQL:  $(mask_credentials "${DATABASE_URL:-postgresql://localhost:5432/cafetera}")"
log "LLM:         $LLM_PROVIDER ($LLM_MODEL)"
log "Embedding:   $EMBEDDING_PROVIDER ($EMBEDDING_MODEL)"
if [[ "${RERANKING_ENABLED:-false}" == "true" ]]; then
  log "Reranker:    ${RERANKER_URL:-http://localhost:8082}"
fi
if [[ "$LLM_PROVIDER" == "ollama" || "$EMBEDDING_PROVIDER" == "ollama" ]]; then
  log "Ollama:      $OLLAMA_URL"
fi
log "=========================================="
echo
log "Press Ctrl+C to stop"
echo

# Start VK bot in Long Poll mode (foreground)
uv run python scripts/polling_vk.py
