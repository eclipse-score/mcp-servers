#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
set -euo pipefail

MARKETPLACE_NAME=eclipse-score-apm-marketplace
MARKETPLACE_SOURCE=https://github.com/eclipse-score/mcp-servers
APM_SOURCE_REF="${AGENT_CONTEXT_APM_REF:-main}"
PACKAGE_ROOT="${AGENT_CONTEXT_APM_PACKAGE_ROOT:-}"
export AGENT_CONTEXT_WORKSPACE="${AGENT_CONTEXT_WORKSPACE:-$(pwd -P)}"
VSCODE_AGENT_FOLDER="${VSCODE_AGENT_FOLDER:-${HOME}/.vscode-server}"
if [[ -z "${PACKAGE_ROOT}" && -d /usr/local/share/agent-context/apm-packages ]]; then
    PACKAGE_ROOT=/usr/local/share/agent-context/apm-packages
fi

if [[ ! -d "${VSCODE_AGENT_FOLDER}" && -z "${PACKAGE_ROOT}" ]]; then
    echo "agent-context: no VS Code server profile found; skipping Copilot APM setup"
    exit 0
fi

git_version=$(git version | awk '{print $3}')
minimum_git_version=2.26.0
minimum_found=$(printf '%s\n' "${minimum_git_version}" "${git_version}" | sort -V | head -n 1)
if [[ "${minimum_found}" != "${minimum_git_version}" ]]; then
    echo "agent-context: APM ${APM_VERSION} requires Git ${minimum_git_version} " \
        "or newer; found ${git_version}" >&2
    exit 1
fi

if [[ -n "${PACKAGE_ROOT}" ]]; then
    packages=(
        "${PACKAGE_ROOT}/graphify-codegraph"
        "${PACKAGE_ROOT}/apm-setup"
    )
    for package in "${packages[@]}"; do
        if [[ ! -f "${package}/apm.yml" ]]; then
            echo "agent-context: missing APM package manifest: ${package}/apm.yml" >&2
            exit 1
        fi
    done
else
    apm marketplace add "${MARKETPLACE_SOURCE}" \
        --name "${MARKETPLACE_NAME}" --ref "${APM_SOURCE_REF}"
    packages=(
        "graphify-codegraph@${MARKETPLACE_NAME}"
        "apm-setup@${MARKETPLACE_NAME}"
    )
fi

cd "${HOME}"
apm install "${packages[@]}" --target agent-skills --only apm --global
python3 "$(dirname "$(readlink -f "$0")")/register_mcp.py"