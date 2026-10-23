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

SOURCE=git+https://github.com/eclipse-score/mcp-servers@8d03dc1d61f648cf10113a0e5c6ac3fe52fc7fc3#subdirectory=packages/graphify-codegraph # v0.2.0
USER_NAME="${_REMOTE_USER:-vscode}"
SHARE=/usr/local/share/agent-context

# Check for required dependencies
PYTHON3="$(command -v python3 || true)"
if [ -z "${PYTHON3}" ]; then
    echo "agent-context: python3 is required for the postCreate hook" >&2
    exit 1
fi

UV="$(command -v uv || true)"
if [ -z "${UV}" ]; then
    echo "agent-context: uv is required, see https://docs.astral.sh/uv/" >&2
    exit 1
fi

install -d -m 0755 "${SHARE}"
install -m 0644 "$(dirname "$0")/register_mcp.py" "${SHARE}/register_mcp.py"
su - "${USER_NAME}" -c "'${UV}' tool install --force '${SOURCE}'"
