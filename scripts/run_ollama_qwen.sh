#!/usr/bin/env bash
set -euo pipefail

MODEL_NAME="${MODEL_NAME:-qwen3.5:4b-q4_K_M}"
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
  OLLAMA_HOST="${OLLAMA_HOST}" ollama serve >/tmp/ollama.log 2>&1 &
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

echo "Checking if model '${MODEL_NAME}' is installed..."

if ! ollama list | awk '{print $1}' | grep -Fx "${MODEL_NAME}" >/dev/null 2>&1; then
  echo "Model not found locally. Pulling '${MODEL_NAME}'..."
  ollama pull "${MODEL_NAME}"
else
  echo "Model '${MODEL_NAME}' is already installed"
fi

echo
echo "Ollama is ready."
echo "Base URL: ${OLLAMA_BASE_URL}"
echo "Model: ${MODEL_NAME}"
echo
echo "Smoke test:"
echo "curl -s ${OLLAMA_BASE_URL}/api/chat -d '{"
echo "  \"model\": \"${MODEL_NAME}\","
echo "  \"messages\": [{\"role\": \"user\", \"content\": \"Ответь одним словом: OK\"}],"
echo "  \"stream\": false"
echo "}' | jq -r '.message.content'"
