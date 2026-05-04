#!/usr/bin/env bash
# ─── RAGAS Evaluation Runner ────────────────────────────────────────────────
# Prerequisites:
# 1. A running LLM provider (Ollama, OpenAI, or llama.cpp)
# 2. Qdrant is started via docker compose (default: http://localhost:6333)
# 3. Documents must already be indexed in Qdrant (run admin ingestion first)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Source common utilities
source "$PROJECT_DIR/scripts/common.sh"

# Override log prefix for ragas
log() {
  echo "[ragas] $*"
}

# ─── Cleanup trap ────────────────────────────────────────────────────────────

on_interrupt() {
  INTERRUPTED=1
  echo
  log "Interrupted by user (Ctrl+C). Cleaning up..."
  exit 130
}

on_terminate() {
  INTERRUPTED=1
  echo
  log "Received SIGTERM. Cleaning up..."
  exit 143
}

trap cleanup EXIT INT TERM

# ─── Load environment ────────────────────────────────────────────────────────

# Load model names and URLs from .env (provider will be selected interactively)
load_env_var LLM_MODEL
load_env_var LLM_MODEL_PATH
load_env_var LLM_MODEL_URL
load_env_var LLM_BASE_URL
load_env_var LLM_API_KEY
load_env_var EMBEDDING_MODEL
load_env_var EMBEDDING_BASE_URL
load_env_var EMBEDDING_API_KEY
load_env_var QDRANT_URL
load_env_var OLLAMA_URL
load_env_var LLM_NUM_CTX
load_env_var LLM_N_GPU_LAYERS
load_env_var LLM_DISABLE_THINKING
load_env_var EMBED_CTX_SIZE
load_env_var EMBED_N_GPU_LAYERS
load_env_var EMBED_UBATCH_SIZE
load_env_var RERANKING_ENABLED
load_env_var RERANKER_URL
load_env_var RERANKER_MODEL
# NOTE: LLM_PROVIDER and EMBEDDING_PROVIDER are NOT loaded from .env
# They are selected interactively below

# Set URL defaults after loading env
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

# ─── Check prerequisites ─────────────────────────────────────────────────────

check_prerequisites_no_uv

# ─── Interactive provider selection ──────────────────────────────────────────

select_llm_provider() {
  echo
  log "Select LLM provider:"
  echo "  1) ollama (default)"
  echo "  2) openai"
  echo "  3) llamacpp"
  read -r -p "[ragas] Enter choice [1-3, Enter=1]: " llm_choice

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
      read -rs -p "[ragas] Enter OpenAI API key: " LLM_API_KEY
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
  read -r -p "[ragas] Enter choice [1-3, Enter=1]: " embed_choice

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
      read -rs -p "[ragas] Enter OpenAI API key: " EMBEDDING_API_KEY
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

# ─── Mode selection ──────────────────────────────────────────────────────────

if [ $# -eq 0 ]; then
  echo
  log "Select mode:"
  echo "  1) generate  — generate synthetic testset only"
  echo "  2) evaluate  — run RAGAS evaluation only"
  echo "  3) all       — generate + evaluate (default)"
  read -r -p "[ragas] Enter choice [1-3, Enter=3]: " mode_choice

  case "${mode_choice:-3}" in
    1|generate)  ACTION="generate" ;;
    2|evaluate)  ACTION="evaluate" ;;
    3|all|"")    ACTION="all" ;;
    *) log "ERROR: Invalid choice '$mode_choice'. Use 1, 2, or 3."; exit 1 ;;
  esac
else
  ACTION="$1"
fi

if [[ "$ACTION" != "generate" && "$ACTION" != "evaluate" && "$ACTION" != "all" ]]; then
  log "ERROR: Unknown action '$ACTION'. Use: generate | evaluate | all"
  exit 1
fi

# ─── Start Qdrant via docker compose ─────────────────────────────────────────

log "Starting Qdrant via docker compose..."
docker compose up -d qdrant

if ! wait_for_service "Qdrant" "${QDRANT_URL}/healthz"; then
  log "ERROR: Qdrant failed to start at ${QDRANT_URL}"
  log "FIX:   Check docker logs: docker compose logs qdrant"
  log "       Make sure port 6333 is not in use: lsof -i :6333"
  exit 1
fi

# ─── Start providers ─────────────────────────────────────────────────────────

# Ollama — only if needed
if [[ "${LLM_PROVIDER}" == "ollama" || "${EMBEDDING_PROVIDER}" == "ollama" ]]; then
  start_ollama_providers "$OLLAMA_URL" "$LLM_PROVIDER" "$LLM_MODEL" "$EMBEDDING_PROVIDER" "$EMBEDDING_MODEL"
fi

# OpenAI — validation only
if [[ "${LLM_PROVIDER}" == "openai" || "${EMBEDDING_PROVIDER}" == "openai" ]]; then
  validate_openai_providers "$LLM_PROVIDER" "$LLM_API_KEY" "$LLM_MODEL" "$EMBEDDING_PROVIDER" "$EMBEDDING_API_KEY" "$EMBEDDING_MODEL"
fi

# llama.cpp — only if needed and URL is local
if [[ "${LLM_PROVIDER}" == "llamacpp" || "${EMBEDDING_PROVIDER}" == "llamacpp" ]]; then
  start_llamacpp_providers "$SCRIPT_DIR/../scripts" "$LLM_PROVIDER" "$LLM_BASE_URL" "$EMBEDDING_PROVIDER" "$EMBEDDING_BASE_URL"
fi

# OpenAI — just log, no local server needed
if [[ "$LLM_PROVIDER" == "openai" ]]; then
  log "LLM provider: OpenAI (remote, no local server needed)"
fi
if [[ "$EMBEDDING_PROVIDER" == "openai" ]]; then
  log "Embedding provider: OpenAI (remote, no local server needed)"
fi

# Reranker — start if enabled and URL is local
# docker_mode=false: ragas runs locally (not in Docker), use localhost URLs
start_reranker_if_needed "$PROJECT_DIR" "${RERANKING_ENABLED:-false}" "${RERANKER_URL:-}" "false"

# ─── Sync dependencies ───────────────────────────────────────────────────────

log "Syncing Python dependencies..."
uv sync

# ─── Export provider vars and run ────────────────────────────────────────────

export LLM_PROVIDER LLM_MODEL LLM_BASE_URL LLM_API_KEY
export EMBEDDING_PROVIDER EMBEDDING_MODEL EMBEDDING_BASE_URL EMBEDDING_API_KEY

echo
log "✓ Qdrant ready at ${QDRANT_URL}"
log "LLM:         ${LLM_PROVIDER} (${LLM_MODEL})"
log "Embedding:   ${EMBEDDING_PROVIDER} (${EMBEDDING_MODEL})"
if [[ "${RERANKING_ENABLED:-false}" == "true" ]]; then
  log "Reranker:    ${RERANKER_URL}"
fi
echo

if [ "$ACTION" = "generate" ] || [ "$ACTION" = "all" ]; then
  echo "=== Generating synthetic testset ==="
  uv run python ragas/generate_testset.py
fi

if [ "$ACTION" = "evaluate" ] || [ "$ACTION" = "all" ]; then
  echo "=== Running RAGAS evaluation ==="
  uv run python ragas/evaluate.py
fi
