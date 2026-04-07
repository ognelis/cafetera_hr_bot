#!/usr/bin/env bash
set -euo pipefail
echo "This script has been split. Please use:"
echo "  ./scripts/run_ollama_llm.sh        — Set up Ollama LLM model"
echo "  ./scripts/run_ollama_embeddings.sh  — Set up Ollama embedding model"
echo
echo "Running both..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/run_ollama_llm.sh"
"$SCRIPT_DIR/run_ollama_embeddings.sh"
