#!/usr/bin/env bash
# Build the entire Flashlight ecosystem on a machine with Ollama installed:
# pulls the base models, then creates every agent model from its Modelfile.
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

# Base models referenced by the Modelfiles. Pulled once, shared by agents.
BASES=(
    "qwen2.5:7b-instruct"
    "qwen2.5-coder:7b"
    "llama3.1:8b"
    "llama3.2:3b"
)

echo "==> Pulling base models (~18 GB total on first run)"
for base in "${BASES[@]}"; do
    echo "--- pulling ${base}"
    ollama pull "${base}"
done

echo "==> Building agent models from Modelfiles"
declare -A MODELS=(
    ["flashlight-supervisor"]="supervisor.Modelfile"
    ["flashlight-coder"]="coder.Modelfile"
    ["flashlight-unreal"]="unreal.Modelfile"
    ["flashlight-sysadmin"]="sysadmin.Modelfile"
    ["flashlight-analytics"]="analytics.Modelfile"
    ["flashlight-webseo"]="webseo.Modelfile"
    ["flashlight-finance"]="finance.Modelfile"
    ["flashlight-research"]="research.Modelfile"
    ["flashlight-media"]="media.Modelfile"
    ["flashlight-home"]="home.Modelfile"
    ["flashlight-general"]="general.Modelfile"
)

for model in "${!MODELS[@]}"; do
    modelfile="${REPO_ROOT}/modelfiles/${MODELS[$model]}"
    echo "--- creating ${model} from ${MODELS[$model]}"
    ollama create "${model}" -f "${modelfile}"
done

echo "==> Installing the Python orchestration layer"
python3 -m pip install -e "${REPO_ROOT}"

echo
echo "Setup complete. Verify the live system with:"
echo "  flashlight --check"
echo "Then try:"
echo "  flashlight \"write a python function that merges two sorted lists\""
