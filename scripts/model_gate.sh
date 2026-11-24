#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# Runs the checks that gate a regenerated model before a PR is opened. The
# refresh workflow and a local dry run use the same script.

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "${root}"

uv lock --check
uv run ruff check .
uv run ruff format --check . --exclude '*.md'
uv run pyright
uv run pytest
uv run python scripts/check_pins.py

# Install from a clean copy of the tracked and new files, so git-ignored local
# environments such as package .venv folders do not reach apm.
scratch="$(mktemp -d)"
trap 'rm -rf "${scratch}"' EXIT
mkdir "${scratch}/tree" "${scratch}/consumer"
git ls-files -co --exclude-standard | tar -cf - -T - | tar -xf - -C "${scratch}/tree"
(
    cd "${scratch}/consumer"
    uv run --project "${root}" apm install \
        "${scratch}/tree/packages/context-discipline" \
        --target vscode --trust-transitive-mcp
    test -f .vscode/mcp.json
)
echo "model gate passed"
