#!/usr/bin/env bash
set -euo pipefail

LLM_MODEL_PATH="${LLM_MODEL_PATH:-./models/Qwen3.5-4B-Q4_K_M.gguf}"
LLM_MODEL_URL="${LLM_MODEL_URL:-https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf}"
LLM_HOST="${LLM_HOST:-127.0.0.1}"
LLM_PORT="${LLM_PORT:-8080}"
LLM_CTX_SIZE="${LLM_CTX_SIZE:-4096}"
LLM_N_GPU_LAYERS="${LLM_N_GPU_LAYERS:-0}"

detect_cpu_count() {
  if command -v nproc >/dev/null 2>&1; then
    nproc
    return
  fi

  if command -v sysctl >/dev/null 2>&1; then
    sysctl -n hw.logicalcpu 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || true
    return
  fi

  if command -v getconf >/dev/null 2>&1; then
    getconf _NPROCESSORS_ONLN 2>/dev/null || true
    return
  fi

  echo 1
}

CPU_COUNT="$(detect_cpu_count)"
THREADS="${THREADS:-$CPU_COUNT}"

if ! command -v llama-server >/dev/null 2>&1; then
  echo "Error: llama-server not found in PATH"
  echo "Install llama.cpp and ensure llama-server is available."
  exit 1
fi

if [ ! -f "$LLM_MODEL_PATH" ]; then
  echo "Model file not found: $LLM_MODEL_PATH"
  echo "Downloading from $LLM_MODEL_URL ..."
  mkdir -p "$(dirname "$LLM_MODEL_PATH")"
  if command -v curl >/dev/null 2>&1; then
    curl -L --progress-bar -o "$LLM_MODEL_PATH" "$LLM_MODEL_URL"
  elif command -v wget >/dev/null 2>&1; then
    wget --show-progress -O "$LLM_MODEL_PATH" "$LLM_MODEL_URL"
  else
    echo "Error: neither curl nor wget found. Install one or download manually:"
    echo "  $LLM_MODEL_URL"
    exit 1
  fi
  if [ ! -f "$LLM_MODEL_PATH" ]; then
    echo "Error: download failed"
    exit 1
  fi
  echo "Download complete: $LLM_MODEL_PATH"
fi

echo "Starting llama-server (LLM inference)"
echo "MODEL_PATH=$LLM_MODEL_PATH"
echo "HOST=$LLM_HOST"
echo "PORT=$LLM_PORT"
echo "CTX_SIZE=$LLM_CTX_SIZE"
echo "CPU_COUNT=$CPU_COUNT"
echo "THREADS=$THREADS"
echo "N_GPU_LAYERS=$LLM_N_GPU_LAYERS"

exec llama-server \
  --model "$LLM_MODEL_PATH" \
  --host "$LLM_HOST" \
  --port "$LLM_PORT" \
  --ctx-size "$LLM_CTX_SIZE" \
  --threads "$THREADS" \
  --n-gpu-layers "$LLM_N_GPU_LAYERS"
