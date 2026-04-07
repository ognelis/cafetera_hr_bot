#!/usr/bin/env bash
set -euo pipefail
echo "This script has been split. Please use:"
echo "  ./scripts/run_llama_llm.sh        — Start LLM inference server"
echo "  ./scripts/run_llama_embeddings.sh  — Start embedding server"
echo
echo "Starting both sequentially..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/run_llama_embeddings.sh" &
exec "$SCRIPT_DIR/run_llama_llm.sh"
