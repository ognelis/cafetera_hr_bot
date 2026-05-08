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

# Load ONLY model names and URLs from .env (provider will be selected interactively)
load_env_var LLM_MODEL
load_env_var LLM_BASE_URL
load_env_var LLM_API_KEY
load_env_var EMBEDDING_MODEL
load_env_var EMBEDDING_BASE_URL
load_env_var EMBEDDING_API_KEY
load_env_var OLLAMA_URL
load_env_var OLLAMA_NUM_GPU
load_env_var RAG_SERVICE_API_KEY
load_env_var RERANKING_ENABLED
load_env_var RERANKER_URL
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

# Interactive provider selection (functions from common.sh)
# URLs are always localhost. configure_docker_urls() converts for Docker.
select_llm_provider "run-all"
select_embedding_provider "run-all"

# Configure Docker URLs BEFORE starting containers
configure_docker_urls "$LLM_PROVIDER" "$LLM_BASE_URL" "$EMBEDDING_PROVIDER" "$EMBEDDING_BASE_URL" "${RERANKER_URL:-http://localhost:8082}"

# Start infrastructure
log "Starting infrastructure via docker compose..."
docker compose down 2>/dev/null
docker compose up -d

# Note: Docker services use CPU-only PyTorch (configured via [tool.uv.sources])

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

# Wait for RAG service (uses docker-compose healthcheck)
if ! wait_for_healthy "rag-service" 60 3; then
  log "ERROR: RAG service failed to become healthy"
  log "FIX:   Check docker logs: docker compose logs rag-service"
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

# Reranker — start if enabled and URL is local
start_reranker_if_needed "$PROJECT_DIR" "${RERANKING_ENABLED:-false}" "${RERANKER_URL:-}"

# docker-compose.yml handles env_file and service URLs directly

# Print startup info
echo
log "=========================================="
log "Starting Cafetera HR Bot System"
log "=========================================="
log "Admin UI:     http://${ADMIN_HOST}:${ADMIN_PORT}/documents"
log "API docs:     http://${ADMIN_HOST}:${ADMIN_PORT}/docs"
log "VK Bot:       Polling mode (no webhook needed)"
log "RAG Service:  http://localhost:8001"
log
echo
log "Docker Services Configuration:"
log "  LLM:        $DOCKER_LLM_BASE_URL"
log "  Embedding:  $DOCKER_EMBEDDING_BASE_URL"
log "  Reranker:   $DOCKER_RERANKER_BASE_URL"
log ""
log "Infrastructure:"
log "  Qdrant:      $(mask_credentials "$QDRANT_URL") (host) / $(mask_credentials "$QDRANT_CONTAINER_URL") (container)"
log "  MinIO:       $(mask_credentials "$MINIO_URL") (host) / $(mask_credentials "$MINIO_CONTAINER_URL") (container)"
log "  PostgreSQL:  $(mask_credentials "$DATABASE_CONTAINER_URL")"
log ""
log "AI Services:"
log "  LLM:         $LLM_PROVIDER ($LLM_MODEL)"
log "  Embedding:   $EMBEDDING_PROVIDER ($EMBEDDING_MODEL)"
if [[ "${RERANKING_ENABLED:-false}" == "true" ]]; then
  log "  Reranker:    ${RERANKER_URL}"
fi
if [[ "$LLM_PROVIDER" == "ollama" || "$EMBEDDING_PROVIDER" == "ollama" ]]; then
  log "  Ollama:      $OLLAMA_URL"
fi
if [[ "$LLM_PROVIDER" == "llamacpp" || "$EMBEDDING_PROVIDER" == "llamacpp" ]]; then
  log "  llama.cpp:   LLM=$LLM_BASE_URL, Embed=$EMBEDDING_BASE_URL"
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
log "RAG Service: http://localhost:8001"
log ""
log "View logs:"
log "  docker compose logs -f"
log ""
log "Stop:      Press Ctrl+C"
log "=========================================="
echo

# Follow compose logs, keeping the script alive until Ctrl+C
docker compose logs -f
