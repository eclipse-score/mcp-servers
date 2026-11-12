#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
set -euo pipefail

config_dir="${VSCODE_AGENT_FOLDER:-${HOME}/.vscode-server}/data/User"
mkdir -p "${config_dir}"
printf '{"inputs":[],"servers":{"existing-server":{"type":"stdio","command":"existing"},"score-codegraph":{"type":"stdio","command":"/usr/local/bin/graphify-codegraph"}}}\n' \
    > "${config_dir}/mcp.json"
