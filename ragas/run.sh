#!/usr/bin/env bash
# ─── RAGAS Evaluation Runner ────────────────────────────────────────────────
# Prerequisites:
# 1. Ollama must be running locally (default: http://localhost:11434)
# 2. Qdrant is started via docker compose (default: http://localhost:6333)
# 3. Documents must already be indexed in Qdrant (run admin ingestion first)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."   # project root

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

trap cleanup EXIT

# ─── Load environment ────────────────────────────────────────────────────────

set -a
[ -f .env.example ] && source .env.example
[ -f .env ] && source .env
set +a

# Set URL defaults after loading env
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
LLM_BASE_URL="${LLM_BASE_URL:-http://localhost:11434}"

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

# ─── Start Qdrant via docker compose ─────────────────────────────────────────

log "Starting Qdrant via docker compose..."
docker compose up -d qdrant

if ! wait_for_service "Qdrant" "${QDRANT_URL}/healthz"; then
  log "ERROR: Qdrant failed to start at ${QDRANT_URL}"
  log "FIX:   Check docker logs: docker compose logs qdrant"
  log "       Make sure port 6333 is not in use: lsof -i :6333"
  exit 1
fi

# ─── Check Ollama (runs natively, not via docker compose) ─────────────────────

log "Checking Ollama at ${LLM_BASE_URL}..."
if ! curl -sf "${LLM_BASE_URL}/api/tags" >/dev/null 2>&1; then
  if command_exists ollama; then
    log "Ollama is not running. Starting Ollama server..."
    OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}" ollama serve >/tmp/ollama.log 2>&1 &
    BG_PIDS+=("$!")
    if ! wait_for_service "Ollama" "${LLM_BASE_URL}/api/tags" 30 1; then
      log "ERROR: Ollama failed to start. Check /tmp/ollama.log"
      exit 1
    fi
  else
    log "ERROR: Ollama is not reachable at ${LLM_BASE_URL} and 'ollama' command not found"
    log "FIX:   Install Ollama: https://ollama.com/download"
    log "       Then start it with: ollama serve"
    exit 1
  fi
else
  log "Ollama is already running at ${LLM_BASE_URL}"
fi

# ─── Sync dependencies ───────────────────────────────────────────────────────

log "Syncing Python dependencies..."
uv sync

# ─── Run evaluation ──────────────────────────────────────────────────────────

ACTION="${1:-all}"  # generate | evaluate | all

echo
log "✓ Qdrant ready at ${QDRANT_URL}"
log "✓ Ollama ready at ${LLM_BASE_URL}"
echo

if [ "$ACTION" = "generate" ] || [ "$ACTION" = "all" ]; then
  echo "=== Generating synthetic testset ==="
  uv run python ragas/generate_testset.py
fi

if [ "$ACTION" = "evaluate" ] || [ "$ACTION" = "all" ]; then
  echo "=== Running RAGAS evaluation ==="
  uv run python ragas/evaluate.py
fi
