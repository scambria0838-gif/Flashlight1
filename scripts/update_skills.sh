#!/usr/bin/env bash
# Re-sync the vendored skills/ directory from the upstream repository:
# https://github.com/addyosmani/agent-skills (MIT). Review the diff and
# commit afterwards.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "==> Fetching latest addyosmani/agent-skills"
git clone --depth 1 https://github.com/addyosmani/agent-skills.git "${TMP_DIR}/agent-skills"

echo "==> Syncing into ${REPO_ROOT}/skills"
rm -rf "${REPO_ROOT}/skills"
mkdir -p "${REPO_ROOT}/skills"
cp -r "${TMP_DIR}/agent-skills/skills/." "${REPO_ROOT}/skills/"
cp "${TMP_DIR}/agent-skills/LICENSE" "${REPO_ROOT}/skills/LICENSE"

echo "==> Done. Vendored skills:"
ls "${REPO_ROOT}/skills"
echo "Review with: git diff --stat skills/"
