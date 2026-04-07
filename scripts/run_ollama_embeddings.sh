#!/usr/bin/env bash
set -euo pipefail

# ── GPU detection ─────────────────────────────────────────────────────────
detect_gpu() {
  if [[ "$(uname -s)" == "Darwin" ]]; then
    # macOS — Apple Silicon uses Metal automatically
    if [[ "$(uname -m)" == "arm64" ]]; then
      echo "metal"
    else
      echo "cpu"
    fi
  elif command -v nvidia-smi &>/dev/null; then
    echo "cuda"
  else
    echo "cpu"
  fi
}

DETECTED_GPU=$(detect_gpu)

case "$DETECTED_GPU" in
  metal|cuda) _DEFAULT_NUM_GPU=99 ;;
  *)          _DEFAULT_NUM_GPU=0  ;;
esac

OLLAMA_NUM_GPU="${OLLAMA_NUM_GPU:-$_DEFAULT_NUM_GPU}"

EMBEDDING_MODEL_NAME="${EMBEDDING_MODEL_NAME:-qwen3-embedding:4b-q4_K_M}"
OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
OLLAMA_BASE_URL="http://${OLLAMA_HOST}"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

wait_for_ollama() {
  local retries=30
  local delay=1

  for _ in $(seq 1 "$retries"); do
    if curl -s "${OLLAMA_BASE_URL}/api/tags" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay"
  done

  return 1
}

if ! command_exists ollama; then
  echo "Error: ollama is not installed or not in PATH"
  exit 1
fi

if ! command_exists curl; then
  echo "Error: curl is required"
  exit 1
fi

echo "Checking Ollama server at ${OLLAMA_BASE_URL}..."

if ! curl -s "${OLLAMA_BASE_URL}/api/tags" >/dev/null 2>&1; then
  echo "Ollama server is not running. Starting it in background..."
  echo "GPU: $DETECTED_GPU → OLLAMA_NUM_GPU=$OLLAMA_NUM_GPU"
  OLLAMA_NUM_GPU="${OLLAMA_NUM_GPU}" OLLAMA_HOST="${OLLAMA_HOST}" ollama serve >/tmp/ollama.log 2>&1 &
  OLLAMA_PID=$!

  if ! wait_for_ollama; then
    echo "Error: Ollama server did not start successfully"
    echo "Check logs: /tmp/ollama.log"
    exit 1
  fi

  echo "Ollama server started (PID=${OLLAMA_PID})"
else
  echo "Ollama server is already running"
fi

echo "Checking if embedding model '${EMBEDDING_MODEL_NAME}' is installed..."

if ! ollama list | awk '{print $1}' | grep -Fx "${EMBEDDING_MODEL_NAME}" >/dev/null 2>&1; then
  echo "Model not found locally. Pulling '${EMBEDDING_MODEL_NAME}'..."
  ollama pull "${EMBEDDING_MODEL_NAME}"
else
  echo "Model '${EMBEDDING_MODEL_NAME}' is already installed"
fi

echo
echo "Ollama Embeddings is ready."
echo "Base URL: ${OLLAMA_BASE_URL}"
echo "Model: ${EMBEDDING_MODEL_NAME}"
echo
echo "Smoke test:"
echo "curl -s ${OLLAMA_BASE_URL}/api/embed -d '{"
echo "  \"model\": \"${EMBEDDING_MODEL_NAME}\","
echo "  \"input\": \"test\""
echo "}'"
