#!/usr/bin/env bash
# Build the entire Flashlight ecosystem on a machine with Ollama installed:
# pulls the base model, builds every agent model, installs the CLI.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OLLAMA_HOST_URL="${OLLAMA_HOST_URL:-http://localhost:11434}"

if ! command -v ollama >/dev/null 2>&1; then
    echo "error: ollama is not installed. Install it from https://ollama.com/download" >&2
    echo "       (Linux: curl -fsSL https://ollama.com/install.sh | sh)" >&2
    exit 1
fi

if ! curl -fsS "${OLLAMA_HOST_URL}/api/version" >/dev/null 2>&1; then
    echo "error: no Ollama server at ${OLLAMA_HOST_URL}." >&2
    echo "       Start it with: ollama serve   (or: docker compose up -d)" >&2
    exit 1
fi

echo "==> Ollama server is live at ${OLLAMA_HOST_URL}"

echo "==> Pulling base model (~1 GB on first run)"
ollama pull qwen2.5:1.5b

echo "==> Building agent models from Modelfiles"
cd "${REPO_ROOT}"
scripts/build_ollama_models.sh

echo "==> Installing the Python orchestration layer"
python3 -m pip install -e "${REPO_ROOT}"

echo
echo "Setup complete. Verify the live system with:"
echo "  flashlight --check"
echo "Then try:"
echo "  flashlight \"write a python function that merges two sorted lists\""
