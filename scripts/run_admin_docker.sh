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
trap cleanup EXIT INT TERM

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
load_env_var OLLAMA_URL
load_env_var LLM_N_GPU_LAYERS
load_env_var EMBED_N_GPU_LAYERS
load_env_var OLLAMA_NUM_GPU
load_env_var RAG_SERVICE_API_KEY
load_env_var LLM_NUM_CTX
load_env_var LLM_DISABLE_THINKING
load_env_var EMBED_CTX_SIZE
load_env_var EMBED_UBATCH_SIZE
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
  read -r -p "[admin-docker] Enter choice [1-3, Enter=1]: " llm_choice

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
      read -rs -p "[admin-docker] Enter OpenAI API key: " LLM_API_KEY
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
  export DOCKER_LLM_BASE_URL="$LLM_BASE_URL"
  log "Selected LLM provider: $LLM_PROVIDER"
}

select_embedding_provider() {
  echo
  log "Select Embedding provider:"
  echo "  1) ollama (default)"
  echo "  2) openai"
  echo "  3) llamacpp"
  read -r -p "[admin-docker] Enter choice [1-3, Enter=1]: " embed_choice

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
      read -rs -p "[admin-docker] Enter OpenAI API key: " EMBEDDING_API_KEY
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
  export DOCKER_EMBEDDING_BASE_URL="$EMBEDDING_BASE_URL"
  log "Selected Embedding provider: $EMBEDDING_PROVIDER"
}

select_llm_provider
select_embedding_provider

# Configure Docker URLs BEFORE starting containers
configure_docker_urls "$LLM_PROVIDER" "$LLM_BASE_URL" "$EMBEDDING_PROVIDER" "$EMBEDDING_BASE_URL" "${RERANKER_URL:-http://localhost:8082}"

# Start infrastructure
log "Starting infrastructure via docker compose..."
docker compose up -d qdrant minio postgres

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

# Start RAG service via docker compose (must be healthy before admin)
log "Building and starting RAG service..."
docker compose up -d --build rag-service

if ! wait_for_healthy "rag-service" 60 3; then
  log "ERROR: RAG service failed to become healthy"
  log "FIX:   Check docker logs: docker compose logs rag-service"
  exit 1
fi

# Start admin service via docker compose
log "Building and starting admin service..."
docker compose up -d --build admin

# Note: Docker admin image uses CPU-only PyTorch (configured via [tool.uv.sources])
# For GPU support in Docker, use nvidia-docker runtime with a CUDA base image

# Print startup info
echo
log "=========================================="
log "Starting admin server via Docker Compose"
log "=========================================="
log "Admin UI:    http://${ADMIN_HOST}:${ADMIN_PORT}/documents"
log "API docs:    http://${ADMIN_HOST}:${ADMIN_PORT}/docs"
log "RAG Service: http://localhost:8001 (host) / http://rag-service:8001 (container)"
log
echo
log "Docker Services Configuration:"
log "  LLM:        $DOCKER_LLM_BASE_URL"
log "  Embedding:  $DOCKER_EMBEDDING_BASE_URL"
log "  Reranker:   $DOCKER_RERANKER_BASE_URL"
log
echo
log "Infrastructure:"
log "Qdrant:      $(mask_credentials "$QDRANT_URL") (host) / $(mask_credentials "$QDRANT_CONTAINER_URL") (container)"
log "MinIO:       $(mask_credentials "$MINIO_URL") (host) / $(mask_credentials "$MINIO_CONTAINER_URL") (container)"
log "PostgreSQL:  $(mask_credentials "$DATABASE_CONTAINER_URL")"
log "LLM:         $LLM_PROVIDER ($LLM_MODEL)"
log "Embedding:   $EMBEDDING_PROVIDER ($EMBEDDING_MODEL)"
if [[ "$LLM_PROVIDER" == "ollama" || "$EMBEDDING_PROVIDER" == "ollama" ]]; then
  log "Ollama:      $OLLAMA_URL"
fi
log "=========================================="
echo
log "Press Ctrl+C to stop"
echo

# Follow admin logs, keeping the script alive until Ctrl+C
docker compose logs -f rag-service admin
