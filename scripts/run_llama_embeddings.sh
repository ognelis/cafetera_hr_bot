#!/usr/bin/env bash
set -euo pipefail

EMBED_MODEL_PATH="${EMBED_MODEL_PATH:-./models/Qwen3-Embedding-4B-Q4_K_M.gguf}"
EMBED_MODEL_URL="${EMBED_MODEL_URL:-https://huggingface.co/Qwen/Qwen3-Embedding-4B-GGUF/resolve/main/Qwen3-Embedding-4B-Q4_K_M.gguf}"
EMBED_HOST="${EMBED_HOST:-127.0.0.1}"
EMBED_PORT="${EMBED_PORT:-8090}"
EMBED_CTX_SIZE="${EMBED_CTX_SIZE:-2048}"
EMBED_N_GPU_LAYERS="${EMBED_N_GPU_LAYERS:-0}"

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

if [ ! -f "$EMBED_MODEL_PATH" ]; then
  echo "Model file not found: $EMBED_MODEL_PATH"
  echo "Downloading from $EMBED_MODEL_URL ..."
  mkdir -p "$(dirname "$EMBED_MODEL_PATH")"
  if command -v curl >/dev/null 2>&1; then
    curl -L --progress-bar -o "$EMBED_MODEL_PATH" "$EMBED_MODEL_URL"
  elif command -v wget >/dev/null 2>&1; then
    wget --show-progress -O "$EMBED_MODEL_PATH" "$EMBED_MODEL_URL"
  else
    echo "Error: neither curl nor wget found. Install one or download manually:"
    echo "  $EMBED_MODEL_URL"
    exit 1
  fi
  if [ ! -f "$EMBED_MODEL_PATH" ]; then
    echo "Error: download failed"
    exit 1
  fi
  echo "Download complete: $EMBED_MODEL_PATH"
fi

echo "Starting llama-server (Embeddings)"
echo "MODEL_PATH=$EMBED_MODEL_PATH"
echo "HOST=$EMBED_HOST"
echo "PORT=$EMBED_PORT"
echo "CTX_SIZE=$EMBED_CTX_SIZE"
echo "CPU_COUNT=$CPU_COUNT"
echo "THREADS=$THREADS"
echo "N_GPU_LAYERS=$EMBED_N_GPU_LAYERS"

exec llama-server \
  --model "$EMBED_MODEL_PATH" \
  --host "$EMBED_HOST" \
  --port "$EMBED_PORT" \
  --ctx-size "$EMBED_CTX_SIZE" \
  --threads "$THREADS" \
  --n-gpu-layers "$EMBED_N_GPU_LAYERS" \
  --embedding \
  --pooling mean
