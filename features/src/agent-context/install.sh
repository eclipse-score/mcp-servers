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

SOURCE=git+https://github.com/eclipse-score/mcp-servers@4c562c1fafa337beacd9f076d739096aca998577#subdirectory=packages/graphify-codegraph # v0.1.0
USER_NAME="${_REMOTE_USER:-vscode}"
SHARE=/usr/local/share/agent-context

UV="$(command -v uv || true)"
if [ -z "${UV}" ]; then
    echo "agent-context: uv is required, see https://docs.astral.sh/uv/" >&2
    exit 1
fi

install -d -m 0755 "${SHARE}"
install -m 0644 "$(dirname "$0")/register_mcp.py" "${SHARE}/register_mcp.py"
su - "${USER_NAME}" -c "'${UV}' tool install --force '${SOURCE}'"
