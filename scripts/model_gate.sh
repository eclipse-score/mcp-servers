#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# Runs the checks that gate a regenerated model before a PR is opened, and is also
# called from on-pr CI so both run the same verification steps. Set GITHUB_BASE_REF
# (e.g. "main") for an open pull request to turn on two extra checks that only make
# sense in a PR context: the overlay delta budget against the base branch and a
# release metadata dry run with pinned-commit verification. They are skipped when no
# base ref is set, keeping the script safe to use before any bot commit exists — e.g.
# inside the refresh workflow.

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
# environments such as package .venv folders do not reach apm. The temporary
# upstream checkout created during refresh is deleted before this step (see
# .github/workflows/refresh-model.yml) and no longer reaches the install either.
scratch="$(mktemp -d)"
trap 'rm -rf "${scratch}"' EXIT
mkdir "${scratch}/tree" "${scratch}/consumer"
git ls-files -co --exclude-standard | tar -cf - -T - | tar -xf - -C "${scratch}/tree"
(
    cd "${scratch}/consumer"
    uv run --project "${root}" --group apm apm install \
        "${scratch}/tree/packages/context-discipline" \
        --target vscode --trust-transitive-mcp
    test -f .vscode/mcp.json
)

if [ -n "${GITHUB_BASE_REF:-}" ]; then
  # Overlay data is validated in every context, but the delta budget only makes
  # sense against the base branch a PR merges into.
  uv run python scripts/validate_overlay.py --base "origin/${GITHUB_BASE_REF}"

  # Dry-run release metadata: prepare the pinned version locally, commit it on
  # top of HEAD without pushing anywhere, then check that only release metadata
  # differs from the pinned commit. Must not run against any tree the refresh bot
  # is about to push — hence it stays behind GITHUB_BASE_REF.
  version="$(uv run python scripts/prepare_release.py --plan | jq -r '.version')"
  uv run python scripts/prepare_release.py "$version"
  uv lock
  git config --local user.email "action@github.com"
  git config --local user.name "GitHub Action"
  git add -u
  git commit --allow-empty -m "Dry-run release metadata"
  uv run python scripts/check_pins.py --release
else
  # No base branch to compare against (a local dry run, the refresh workflow or
  # a fresh push): only static validation runs — no delta budget can be computed.
  uv run python scripts/validate_overlay.py
fi

echo "model gate passed"
