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

# ─── Helpers ─────────────────────────────────────────────────────────────────

HEALTH_RETRIES=30
HEALTH_INTERVAL=2

log() {
  echo "[ragas] $*"
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

# ─── Cleanup trap ────────────────────────────────────────────────────────────

BG_PIDS=()
INTERRUPTED=0

cleanup() {
  log "Shutting down..."
  for pid in ${BG_PIDS[@]+"${BG_PIDS[@]}"}; do
    if kill -0 "$pid" 2>/dev/null; then
      log "Stopping background process (PID=$pid)"
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
  log "Stopping docker services (qdrant)..."
  docker compose down qdrant 2>/dev/null || true
}

on_interrupt() {
  INTERRUPTED=1
  echo
  log "Interrupted by user (Ctrl+C). Cleaning up..."
  # Exit with 130 (standard code for SIGINT); EXIT trap will run cleanup.
  exit 130
}

on_terminate() {
  INTERRUPTED=1
  echo
  log "Received SIGTERM. Cleaning up..."
  exit 143
}

trap cleanup EXIT
trap on_interrupt INT
trap on_terminate TERM

# ─── Load environment ────────────────────────────────────────────────────────

load_env_var() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]] && grep -qE "^${var_name}=" .env 2>/dev/null; then
    local val
    val=$(grep -E "^${var_name}=" .env | head -1 | cut -d= -f2- | sed 's/^["'\'']*//;s/["'\'']*$//')
    if [[ -n "$val" ]]; then
      export "$var_name=$val"
    fi
  fi
}

load_env_var LLM_PROVIDER
load_env_var LLM_MODEL
load_env_var LLM_MODEL_PATH
load_env_var LLM_MODEL_URL
load_env_var LLM_BASE_URL
load_env_var LLM_API_KEY
load_env_var EMBEDDING_PROVIDER
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

# Set URL defaults after loading env
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

# ─── Check prerequisites ─────────────────────────────────────────────────────

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
  log "Checking Ollama at ${OLLAMA_URL}..."
  if ! curl -sf "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
    if command_exists ollama; then
      log "Ollama is not running. Starting Ollama server..."
      OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}" ollama serve >/tmp/ollama.log 2>&1 &
      BG_PIDS+=("$!")
      if ! wait_for_service "Ollama" "${OLLAMA_URL}/api/tags" 30 1; then
        log "ERROR: Ollama failed to start. Check /tmp/ollama.log"
        exit 1
      fi
    else
      log "ERROR: Ollama is not reachable at ${OLLAMA_URL} and 'ollama' command not found"
      log "FIX:   Install Ollama: https://ollama.com/download"
      log "       Then start it with: ollama serve"
      exit 1
    fi
  else
    log "Ollama is already running at ${OLLAMA_URL}"
  fi
fi

# llama.cpp — only if needed
if [[ "${LLM_PROVIDER}" == "llamacpp" || "${EMBEDDING_PROVIDER}" == "llamacpp" ]]; then
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
      "$SCRIPT_DIR/../scripts/run_llama_llm.sh" >/tmp/llama_llm.log 2>&1 &
      BG_PIDS+=("$!")
      if ! wait_for_service "llamacpp LLM" "$LLAMACPP_LLM_URL" 30 2; then
        log "ERROR: llamacpp LLM server failed to start. Check /tmp/llama_llm.log"
        exit 1
      fi
    else
      log "llamacpp LLM server is already running"
    fi
    log "Verifying llamacpp LLM server has a loaded model..."
    if ! curl -sf "${LLAMACPP_LLM_URL}/v1/models" >/dev/null 2>&1; then
      log "WARNING: Could not verify model on llamacpp LLM server"
      log "FIX:    Check /tmp/llama_llm.log for errors"
    else
      log "llamacpp LLM server model verified"
    fi
  fi

  # Start embedding server if not running
  if [[ "$EMBEDDING_PROVIDER" == "llamacpp" ]]; then
    log "Checking llamacpp embedding server at $LLAMACPP_EMBED_URL..."
    if ! curl -sf "$LLAMACPP_EMBED_URL" >/dev/null 2>&1; then
      log "Starting llamacpp embedding server in background..."
      "$SCRIPT_DIR/../scripts/run_llama_embeddings.sh" >/tmp/llama_embed.log 2>&1 &
      BG_PIDS+=("$!")
      if ! wait_for_service "llamacpp Embedding" "$LLAMACPP_EMBED_URL" 30 2; then
        log "ERROR: llamacpp embedding server failed to start. Check /tmp/llama_embed.log"
        exit 1
      fi
    else
      log "llamacpp embedding server is already running"
    fi
    log "Verifying llamacpp embedding server has a loaded model..."
    if ! curl -sf "${LLAMACPP_EMBED_URL}/v1/models" >/dev/null 2>&1; then
      log "WARNING: Could not verify model on llamacpp embedding server"
      log "FIX:    Check /tmp/llama_embed.log for errors"
    else
      log "llamacpp embedding server model verified"
    fi
  fi
fi

# OpenAI — just log, no local server needed
if [[ "$LLM_PROVIDER" == "openai" ]]; then
  log "LLM provider: OpenAI (remote, no local server needed)"
fi
if [[ "$EMBEDDING_PROVIDER" == "openai" ]]; then
  log "Embedding provider: OpenAI (remote, no local server needed)"
fi

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
echo

if [ "$ACTION" = "generate" ] || [ "$ACTION" = "all" ]; then
  echo "=== Generating synthetic testset ==="
  uv run python ragas/generate_testset.py
fi

if [ "$ACTION" = "evaluate" ] || [ "$ACTION" = "all" ]; then
  echo "=== Running RAGAS evaluation ==="
  uv run python ragas/evaluate.py
fi
