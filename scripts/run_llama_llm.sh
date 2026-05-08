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

_load_env_var LLM_NUM_CTX
_load_env_var LLM_N_GPU_LAYERS
_load_env_var LLM_DISABLE_THINKING
_load_env_var LLM_MODEL_PATH
_load_env_var LLM_MODEL_URL

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

LLM_MODEL_PATH="${LLM_MODEL_PATH:-./models/Qwen3.5-9B-Q4_K_M.gguf}"
LLM_MODEL_URL="${LLM_MODEL_URL:-https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-Q4_K_M.gguf}"
LLM_HOST="${LLM_HOST:-127.0.0.1}"
LLM_PORT="${LLM_PORT:-8080}"
# Full context window shared across all parallel slots.
# With --parallel N, each request slot holds LLM_CTX_SIZE/N tokens.
# Default 32768 keeps ≥6500 tokens per slot at LLM_PARALLEL=5 (production)
# and the full window available at LLM_PARALLEL=1 (RAGAS / single-user).
LLM_CTX_SIZE="${LLM_NUM_CTX:-32768}"
LLM_N_GPU_LAYERS="${LLM_N_GPU_LAYERS:-$_DEFAULT_GPU_LAYERS}"
# KV Cache quantization: q8_0 saves 50% VRAM with <1% quality loss
LLM_CACHE_TYPE_K="${LLM_CACHE_TYPE_K:-q8_0}"
LLM_CACHE_TYPE_V="${LLM_CACHE_TYPE_V:-q8_0}"
# Parallel requests: limits concurrent generations to control KV Cache usage
# Default 5 balances throughput and VRAM (adjust based on your GPU capacity)
LLM_PARALLEL="${LLM_PARALLEL:-5}"

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

LLM_DISABLE_THINKING="${LLM_DISABLE_THINKING:-true}"

REASONING_ARGS=""
if [ "$LLM_DISABLE_THINKING" = "true" ]; then
  REASONING_ARGS="--reasoning-budget 0"
fi

CHAT_TEMPLATE_KWARGS=""
if [ "$LLM_DISABLE_THINKING" = "true" ]; then
  CHAT_TEMPLATE_KWARGS=(--chat-template-kwargs '{"enable_thinking":false}')
else
  CHAT_TEMPLATE_KWARGS=(--chat-template-kwargs '{"enable_thinking":true}')
fi

echo "Starting llama-server (LLM inference)"
echo "MODEL_PATH=$LLM_MODEL_PATH"
echo "HOST=$LLM_HOST"
echo "PORT=$LLM_PORT"
echo "CTX_SIZE=$LLM_CTX_SIZE"
echo "CPU_COUNT=$CPU_COUNT"
echo "THREADS=$THREADS"
echo "GPU: $DETECTED_GPU → offloading $LLM_N_GPU_LAYERS layers"
echo "DISABLE_THINKING=$LLM_DISABLE_THINKING"
echo "KV_CACHE: q8_0 (50% VRAM savings, <1% quality loss)"
echo "PARALLEL=$LLM_PARALLEL (max concurrent requests)"

exec llama-server \
  --model "$LLM_MODEL_PATH" \
  --host "$LLM_HOST" \
  --port "$LLM_PORT" \
  --ctx-size "$LLM_CTX_SIZE" \
  --threads "$THREADS" \
  --n-gpu-layers "$LLM_N_GPU_LAYERS" \
  --cache-type-k "$LLM_CACHE_TYPE_K" \
  --cache-type-v "$LLM_CACHE_TYPE_V" \
  --parallel "$LLM_PARALLEL" \
  --n-predict -1 \
  $REASONING_ARGS \
  "${CHAT_TEMPLATE_KWARGS[@]}"
