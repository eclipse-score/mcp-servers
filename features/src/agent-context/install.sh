#!/usr/bin/env bash
# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************
set -euo pipefail

SOURCE=git+https://github.com/eclipse-score/mcp-servers@8f359bdea137d9f54c30a680b8eaebebe1a6fd7c#subdirectory=packages/graphify-codegraph # v0.2.5
SHARE=/usr/local/share/agent-context

if ! command -v python3 >/dev/null 2>&1 || \
   ! command -v curl >/dev/null 2>&1 || \
   ! command -v git >/dev/null 2>&1; then
    apt-get update
    apt-get install -y --no-install-recommends ca-certificates curl git python3
fi

# Install uv if not present
UV="$(command -v uv || true)"
if [ -z "${UV}" ]; then
    echo "agent-context: installing uv..." >&2
    # Install uv to a system-wide location that persists in the final image
    curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh
    UV="/usr/local/bin/uv"
    if [ ! -x "${UV}" ]; then
        echo "agent-context: failed to install uv" >&2
        exit 1
    fi
fi

install -d -m 0755 "${SHARE}"
install -m 0644 "$(dirname "$0")/register_mcp.py" "${SHARE}/register_mcp.py"
UV_TOOL_DIR="${SHARE}/tools" \
UV_TOOL_BIN_DIR=/usr/local/bin \
UV_PYTHON_INSTALL_DIR="${SHARE}/python" \
    "${UV}" tool install --python 3.12 --force "${SOURCE}"
