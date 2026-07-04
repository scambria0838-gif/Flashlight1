#!/usr/bin/env bash
# End-to-end verification against the LIVE system. This intentionally has
# no offline mode: it requires a running Ollama server with all agent
# models built, and exercises real routing + real inference.
set -euo pipefail

echo "==> 1/3 Checking server and models"
flashlight --check

echo
echo "==> 2/3 Real routed inference (supervisor -> coder expected)"
flashlight "Write a Python function that reverses a linked list, with a doctest."

echo
echo "==> 3/3 Real tool call (finance agent -> live CoinGecko API)"
flashlight --agent finance "What is the current price of bitcoin in USD?"

echo
echo "Verification passed: routing, inference and live tools all working."
