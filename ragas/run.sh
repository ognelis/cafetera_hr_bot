#!/usr/bin/env bash
# ─── RAGAS Evaluation Runner ────────────────────────────────────────────────
# Prerequisites:
# 1. A running LLM provider (Ollama, OpenAI, or llama.cpp)
# 2. Qdrant is started via docker compose (default: http://localhost:6333)
# 3. Documents must already be indexed in Qdrant (run admin ingestion first)
#
# Usage:
#   Interactive mode:
#     ./ragas/run.sh
#
#   CLI mode:
#     ./ragas/run.sh generate
#     ./ragas/run.sh evaluate
#     ./ragas/run.sh all
#     ./ragas/run.sh retrieval
#     ./ragas/run.sh retrieval --k 5 --size 200
#     ./ragas/run.sh retrieval --k 5 --size 200 --mode dense
#     ./ragas/run.sh optimize
#     ./ragas/run.sh optimize --variants 15 --sample-size 10
#
#   Retrieval modes (--mode): hybrid (default), dense, bm25
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
load_env_var LLM_DISABLE_THINKING
load_env_var EMBED_CTX_SIZE
load_env_var EMBED_UBATCH_SIZE
load_env_var RERANKING_ENABLED
load_env_var RERANKER_URL
load_env_var RERANKER_MODEL
load_env_var BM25_LEMMATIZE
# NOTE: LLM_PROVIDER and EMBEDDING_PROVIDER are NOT loaded from .env
# They are selected interactively below

# Set URL defaults after loading env
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

# ─── Check prerequisites ─────────────────────────────────────────────────────

check_prerequisites_no_uv

# ─── Mode selection ──────────────────────────────────────────────────────────

RETRIEVAL_K=""
RETRIEVAL_SIZE=""
RETRIEVAL_MODE=""
OPTIMIZE_VARIANTS=""
OPTIMIZE_SAMPLE_SIZE=""

if [ $# -eq 0 ]; then
  echo
  log "Select mode:"
  echo "  1) generate  — generate synthetic testset only"
  echo "  2) evaluate  — run RAGAS evaluation only"
  echo "  3) all       — generate + evaluate (default)"
  echo "  4) retrieval — offline retrieval metrics (SberQuAD, temp Qdrant)"
  echo "  5) optimize  — optimize system prompt via LLM-generated variants"
  read -r -p "[ragas] Enter choice [1-5, Enter=3]: " mode_choice

  case "${mode_choice:-3}" in
    1|generate)   ACTION="generate" ;;
    2|evaluate)   ACTION="evaluate" ;;
    3|all|"")     ACTION="all" ;;
    4|retrieval)  ACTION="retrieval" ;;
    5|optimize)   ACTION="optimize" ;;
    *) log "ERROR: Invalid choice '$mode_choice'. Use 1, 2, 3, 4, or 5."; exit 1 ;;
  esac
else
  ACTION="$1"
  # Parse optional retrieval parameters
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --k)
        RETRIEVAL_K="$2"
        shift 2
        ;;
      --size)
        RETRIEVAL_SIZE="$2"
        shift 2
        ;;
      --mode)
        RETRIEVAL_MODE="$2"
        shift 2
        ;;
      --variants)
        OPTIMIZE_VARIANTS="$2"
        shift 2
        ;;
      --sample-size)
        OPTIMIZE_SAMPLE_SIZE="$2"
        shift 2
        ;;
      *)
        log "ERROR: Unknown option '$1'. Use: --k <number> --size <number> --mode <dense|bm25|hybrid> --variants <number> --sample-size <number>"
        exit 1
        ;;
    esac
  done
fi

if [[ "$ACTION" != "generate" && "$ACTION" != "evaluate" && "$ACTION" != "all" && "$ACTION" != "retrieval" && "$ACTION" != "optimize" ]]; then
  log "ERROR: Unknown action '$ACTION'. Use: generate | evaluate | all | retrieval | optimize"
  exit 1
fi

# ─── Retrieval parameters (interactive if not provided via CLI) ──────────────

if [[ "$ACTION" == "retrieval" && -z "$RETRIEVAL_K" ]]; then
  read -r -p "[ragas] Retrieval top-k [default=10]: " input_k
  RETRIEVAL_K="${input_k:-10}"
fi

if [[ "$ACTION" == "retrieval" && -z "$RETRIEVAL_SIZE" ]]; then
  read -r -p "[ragas] SberQuAD sample size [default=0=all]: " input_size
  RETRIEVAL_SIZE="${input_size:-0}"
fi

if [[ "$ACTION" == "retrieval" && -z "$RETRIEVAL_MODE" ]]; then
  echo
  log "Retrieval mode:"
  echo "  1) hybrid  — dense + BM25 with RRF fusion (default)"
  echo "  2) dense   — dense vectors only"
  echo "  3) bm25    — BM25 sparse vectors only"
  read -r -p "[ragas] Enter choice [1-3, Enter=1]: " mode_input

  case "${mode_input:-1}" in
    1|hybrid|"")  RETRIEVAL_MODE="hybrid" ;;
    2|dense)      RETRIEVAL_MODE="dense" ;;
    3|bm25)       RETRIEVAL_MODE="bm25" ;;
    *) log "ERROR: Invalid mode choice '$mode_input'. Use 1, 2, or 3."; exit 1 ;;
  esac
fi

# Default retrieval mode to hybrid if still empty (CLI provided no --mode)
RETRIEVAL_MODE="${RETRIEVAL_MODE:-hybrid}"

# Validate retrieval mode value
if [[ "$ACTION" == "retrieval" && "$RETRIEVAL_MODE" != "hybrid" && "$RETRIEVAL_MODE" != "dense" && "$RETRIEVAL_MODE" != "bm25" ]]; then
  log "ERROR: Invalid --mode '$RETRIEVAL_MODE'. Use: dense | bm25 | hybrid"
  exit 1
fi

# ─── Interactive provider selection ──────────────────────────────────────────
if [[ "$ACTION" != "retrieval" ]]; then
  select_llm_provider "ragas"
fi
select_embedding_provider "ragas"

# ─── Start Qdrant via docker compose ─────────────────────────────────────────

if [[ "$ACTION" != "retrieval" ]]; then
  log "Starting Qdrant via docker compose..."
  docker compose up -d qdrant

  if ! wait_for_service "Qdrant" "${QDRANT_URL}/healthz"; then
    log "ERROR: Qdrant failed to start at ${QDRANT_URL}"
    log "FIX:   Check docker logs: docker compose logs qdrant"
    log "       Make sure port 6333 is not in use: lsof -i :6333"
    exit 1
  fi
fi

# ─── Start providers ─────────────────────────────────────────────────────────

# Ollama — only if needed
if [[ "${LLM_PROVIDER:-}" == "ollama" || "${EMBEDDING_PROVIDER}" == "ollama" ]]; then
  start_ollama_providers "$OLLAMA_URL" "${LLM_PROVIDER:-}" "${LLM_MODEL:-}" "$EMBEDDING_PROVIDER" "$EMBEDDING_MODEL"
fi

# OpenAI — validation only
if [[ "${LLM_PROVIDER:-}" == "openai" || "${EMBEDDING_PROVIDER}" == "openai" ]]; then
  validate_openai_providers "${LLM_PROVIDER:-}" "${LLM_API_KEY:-}" "${LLM_MODEL:-}" "$EMBEDDING_PROVIDER" "$EMBEDDING_API_KEY" "$EMBEDDING_MODEL"
fi

# llama.cpp — only if needed and URL is local
if [[ "${LLM_PROVIDER:-}" == "llamacpp" || "${EMBEDDING_PROVIDER}" == "llamacpp" ]]; then
  # RAGAS evaluates samples sequentially; force single-slot mode so each
  # request gets the full LLM_NUM_CTX. Otherwise llama-server partitions the
  # KV cache into LLM_PARALLEL slots (default 5) and Faithfulness NER output
  # runs out of room → instructor.IncompleteOutputException.
  export LLM_PARALLEL=1
  start_llamacpp_providers "$SCRIPT_DIR/../scripts" "${LLM_PROVIDER:-}" "${LLM_BASE_URL:-}" "$EMBEDDING_PROVIDER" "$EMBEDDING_BASE_URL"
fi

# OpenAI — just log, no local server needed
if [[ "${LLM_PROVIDER:-}" == "openai" ]]; then
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

if [[ "$ACTION" != "retrieval" ]]; then
  export LLM_PROVIDER LLM_MODEL LLM_BASE_URL LLM_API_KEY
fi
export EMBEDDING_PROVIDER EMBEDDING_MODEL EMBEDDING_BASE_URL EMBEDDING_API_KEY
export BM25_LEMMATIZE

echo
if [[ "$ACTION" != "retrieval" ]]; then
  log "✓ Qdrant ready at ${QDRANT_URL}"
  log "LLM:         ${LLM_PROVIDER} (${LLM_MODEL})"
fi
log "Embedding:   ${EMBEDDING_PROVIDER} (${EMBEDDING_MODEL})"
log "BM25 lemmatize: ${BM25_LEMMATIZE:-true}"
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

if [ "$ACTION" = "retrieval" ]; then
  echo "=== Running offline retrieval metrics (SberQuAD) ==="
  log "Retrieval top-k: ${RETRIEVAL_K:-10}"
  log "SberQuAD sample size: ${RETRIEVAL_SIZE:-0}"
  log "Retrieval mode: ${RETRIEVAL_MODE}"
  echo
  
  RETRIEVAL_CMD="uv run python ragas/evaluate_retrieval.py"
  
  # Append --k if specified
  if [[ -n "$RETRIEVAL_K" ]]; then
    RETRIEVAL_CMD="$RETRIEVAL_CMD --k $RETRIEVAL_K"
  fi
  
  # Append --size if specified
  if [[ -n "$RETRIEVAL_SIZE" ]]; then
    RETRIEVAL_CMD="$RETRIEVAL_CMD --size $RETRIEVAL_SIZE"
  fi
  
  # Append retrieval mode flags
  case "$RETRIEVAL_MODE" in
    dense)  RETRIEVAL_CMD="$RETRIEVAL_CMD --no-use-bm25" ;;
    bm25)   RETRIEVAL_CMD="$RETRIEVAL_CMD --no-use-dense" ;;
    hybrid) ;;  # both enabled by default, no extra flags needed
  esac
  
  eval "$RETRIEVAL_CMD"
fi

if [ "$ACTION" = "optimize" ]; then
  echo "=== Optimizing system prompt ==="
  log "Variants: ${OPTIMIZE_VARIANTS:-10} (default 10)"
  log "Sample size: ${OPTIMIZE_SAMPLE_SIZE:-0} (0 = all)"
  echo

  OPTIMIZE_CMD="uv run python ragas/optimize_prompt.py"

  # Append --variants if specified
  if [[ -n "$OPTIMIZE_VARIANTS" ]]; then
    OPTIMIZE_CMD="$OPTIMIZE_CMD --variants $OPTIMIZE_VARIANTS"
  fi

  # Append --sample-size if specified
  if [[ -n "$OPTIMIZE_SAMPLE_SIZE" ]]; then
    OPTIMIZE_CMD="$OPTIMIZE_CMD --sample-size $OPTIMIZE_SAMPLE_SIZE"
  fi

  eval "$OPTIMIZE_CMD"
fi
