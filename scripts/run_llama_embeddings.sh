#!/usr/bin/env bash
set -euo pipefail

# ── Load from .env (if present; existing env vars take priority) ──────────
_load_env_var() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    local val
    val=$(grep -E "^${var_name}=" "${BASH_SOURCE[0]%/*}/../.env" 2>/dev/null | head -1 | cut -d= -f2- | sed "s/^[\"']*//;s/[\"']*$//") || true
    if [[ -n "${val:-}" ]]; then
      export "$var_name=$val"
    fi
  fi
}

_load_env_var EMBED_MODEL_PATH
_load_env_var EMBED_MODEL_URL
_load_env_var EMBED_CTX_SIZE
_load_env_var EMBED_N_GPU_LAYERS
_load_env_var EMBED_UBATCH_SIZE

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
  metal|cuda) _DEFAULT_GPU_LAYERS=99 ;;
  *)          _DEFAULT_GPU_LAYERS=0  ;;
esac

EMBED_MODEL_PATH="${EMBED_MODEL_PATH:-./models/Qwen3-Embedding-0.6B-f16.gguf}"
EMBED_MODEL_URL="${EMBED_MODEL_URL:-https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/Qwen3-Embedding-0.6B-f16.gguf}"
EMBED_HOST="${EMBED_HOST:-127.0.0.1}"
EMBED_PORT="${EMBED_PORT:-8090}"
EMBED_CTX_SIZE="${EMBED_CTX_SIZE:-2048}"
EMBED_N_GPU_LAYERS="${EMBED_N_GPU_LAYERS:-$_DEFAULT_GPU_LAYERS}"
EMBED_UBATCH_SIZE="${EMBED_UBATCH_SIZE:-2048}"

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
echo "UBATCH_SIZE=$EMBED_UBATCH_SIZE"
echo "CPU_COUNT=$CPU_COUNT"
echo "THREADS=$THREADS"
echo "GPU: $DETECTED_GPU → offloading $EMBED_N_GPU_LAYERS layers"

exec llama-server \
  --model "$EMBED_MODEL_PATH" \
  --host "$EMBED_HOST" \
  --port "$EMBED_PORT" \
  --ctx-size "$EMBED_CTX_SIZE" \
  --ubatch-size "$EMBED_UBATCH_SIZE" \
  --threads "$THREADS" \
  --n-gpu-layers "$EMBED_N_GPU_LAYERS" \
  --embedding \
  --pooling mean
