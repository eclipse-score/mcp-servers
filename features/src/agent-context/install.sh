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

SOURCE=git+https://github.com/eclipse-score/mcp-servers@a85a027acff417ef2718c07daf62491e98cdb4fd#subdirectory=packages/graphify-codegraph # v0.2.3
USER_NAME="${_REMOTE_USER:-vscode}"
SHARE=/usr/local/share/agent-context

# Install python3 if not present
PYTHON3="$(command -v python3 || true)"
if [ -z "${PYTHON3}" ]; then
    echo "agent-context: installing python3..." >&2
    apt-get update
    apt-get install -y python3 python3-pip python3-venv
    PYTHON3="$(command -v python3)"
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
"${UV}" tool install --force "${SOURCE}"
