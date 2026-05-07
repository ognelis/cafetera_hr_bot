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

_load_env_var RERANKER_CTX_SIZE
_load_env_var RERANKER_N_GPU_LAYERS
_load_env_var RERANKER_MODEL_PATH
_load_env_var RERANKER_MODEL_URL
_load_env_var RERANKER_BATCH_SIZE
_load_env_var RERANKER_UBATCH_SIZE

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

RERANKER_MODEL_PATH="${RERANKER_MODEL_PATH:-./models/Qwen3-Reranker-0.6B-Q4_K_M.gguf}"
RERANKER_MODEL_URL="${RERANKER_MODEL_URL:-https://huggingface.co/Voodisss/Qwen3-Reranker-0.6B-GGUF-llama_cpp/resolve/main/Qwen3-Reranker-0.6B-Q4_K_M.gguf}"
RERANKER_HOST="${RERANKER_HOST:-127.0.0.1}"
RERANKER_PORT="${RERANKER_PORT:-8082}"
RERANKER_CTX_SIZE="${RERANKER_CTX_SIZE:-4096}"
RERANKER_N_GPU_LAYERS="${RERANKER_N_GPU_LAYERS:-$_DEFAULT_GPU_LAYERS}"
RERANKER_BATCH_SIZE="${RERANKER_BATCH_SIZE:-1024}"
RERANKER_UBATCH_SIZE="${RERANKER_UBATCH_SIZE:-1024}"

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

if [ ! -f "$RERANKER_MODEL_PATH" ]; then
  echo "Model file not found: $RERANKER_MODEL_PATH"
  echo "Downloading from $RERANKER_MODEL_URL ..."
  mkdir -p "$(dirname "$RERANKER_MODEL_PATH")"
  if command -v curl >/dev/null 2>&1; then
    curl -L --progress-bar -o "$RERANKER_MODEL_PATH" "$RERANKER_MODEL_URL"
  elif command -v wget >/dev/null 2>&1; then
    wget --show-progress -O "$RERANKER_MODEL_PATH" "$RERANKER_MODEL_URL"
  else
    echo "Error: neither curl nor wget found. Install one or download manually:"
    echo "  $RERANKER_MODEL_URL"
    exit 1
  fi
  if [ ! -f "$RERANKER_MODEL_PATH" ]; then
    echo "Error: download failed"
    exit 1
  fi
  echo "Download complete: $RERANKER_MODEL_PATH"
fi

echo "Starting llama-server (Reranker)"
echo "MODEL_PATH=$RERANKER_MODEL_PATH"
echo "HOST=$RERANKER_HOST"
echo "PORT=$RERANKER_PORT"
echo "CTX_SIZE=$RERANKER_CTX_SIZE"
echo "CPU_COUNT=$CPU_COUNT"
echo "THREADS=$THREADS"
echo "BATCH_SIZE=$RERANKER_BATCH_SIZE"
echo "UBATCH_SIZE=$RERANKER_UBATCH_SIZE"
echo "GPU: $DETECTED_GPU → offloading $RERANKER_N_GPU_LAYERS layers"

exec llama-server \
  --model "$RERANKER_MODEL_PATH" \
  --host "$RERANKER_HOST" \
  --port "$RERANKER_PORT" \
  --ctx-size "$RERANKER_CTX_SIZE" \
  --batch-size "$RERANKER_BATCH_SIZE" \
  --ubatch-size "$RERANKER_UBATCH_SIZE" \
  --threads "$THREADS" \
  --n-gpu-layers "$RERANKER_N_GPU_LAYERS" \
  --reranking \
  --embedding \
  --pooling rank
