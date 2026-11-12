#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
set -euo pipefail

PACKAGE_ROOT="${AGENT_CONTEXT_APM_PACKAGE_ROOT:?set AGENT_CONTEXT_APM_PACKAGE_ROOT}"
SETUP_SCRIPT="${AGENT_CONTEXT_SETUP_SCRIPT:-/usr/local/share/agent-context/setup_apm.sh}"
apm --version | grep -F 'version 0.35.0'
TEST_ROOT=$(mktemp -d /tmp/agent-context-apm-test.XXXXXX)
trap 'rm -rf "$TEST_ROOT"' EXIT
HOME_DIR="${TEST_ROOT}/home"
CONSUMER_DIR="${TEST_ROOT}/consumer"
VSCODE_AGENT_FOLDER="${HOME_DIR}/.vscode-server"

mkdir -p "${HOME_DIR}/bin" "${VSCODE_AGENT_FOLDER}/data/User" "${CONSUMER_DIR}"
printf '#!/bin/sh\nexit 0\n' > "${HOME_DIR}/bin/copilot"
printf '#!/bin/sh\nexit 0\n' > "${HOME_DIR}/bin/graphify-codegraph"
chmod +x "${HOME_DIR}/bin/copilot"
chmod +x "${HOME_DIR}/bin/graphify-codegraph"
printf '{"inputs":[],"servers":{"existing-server":{"type":"stdio","command":"existing"},"score-codegraph":{"type":"stdio","command":"/usr/local/bin/graphify-codegraph"}}}\n' \
    > "${VSCODE_AGENT_FOLDER}/data/User/mcp.json"
printf 'consumer fixture\n' > "${CONSUMER_DIR}/README.md"

(
    cd "${CONSUMER_DIR}"
    HOME="${HOME_DIR}" \
    VSCODE_AGENT_FOLDER="${VSCODE_AGENT_FOLDER}" \
    AGENT_CONTEXT_APM_PACKAGE_ROOT="${PACKAGE_ROOT}" \
    PATH="${HOME_DIR}/bin:${PATH}" \
        bash "${SETUP_SCRIPT}"
)

python3 - "${HOME_DIR}" "${CONSUMER_DIR}" <<'PY'
import json
import selectors
import subprocess
import sys
from pathlib import Path

home = Path(sys.argv[1])
consumer = Path(sys.argv[2])
config_path = home / ".vscode-server/data/User/mcp.json"
config = json.loads(config_path.read_text(encoding="utf-8"))
servers = config["servers"]
assert set(servers) == {"existing-server", "graphify-codegraph", "apm-setup"}, servers
assert config["inputs"] == []
assert servers["graphify-codegraph"]["type"] == "stdio"
assert servers["graphify-codegraph"]["args"] == ["--repo-path", str(consumer.resolve())]
assert Path(servers["graphify-codegraph"]["command"]).is_file()
assert servers["apm-setup"]["type"] == "stdio"
assert Path(servers["apm-setup"]["command"]).is_file()
assert Path(servers["apm-setup"]["args"][2]).is_dir()
assert len(list((home / ".agents/skills").rglob("SKILL.md"))) == 2
assert (home / ".apm/apm.yml").is_file()
assert not (home / ".copilot/mcp-config.json").exists()
assert sorted(path.name for path in consumer.iterdir()) == ["README.md"]

setup_server = servers["apm-setup"]
process = subprocess.Popen(
    [setup_server["command"], *setup_server["args"]],
    cwd=consumer,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
try:
    for request in (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "feature-test", "version": "1.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ):
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()
        if "id" not in request:
            continue
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                assert selector.select(timeout=30), "apm-setup MCP server timed out"
                response = json.loads(process.stdout.readline())
                if response.get("id") != request["id"]:
                    continue
                assert "error" not in response, response
                if request["id"] == 2:
                    assert {tool["name"] for tool in response["result"]["tools"]} == {
                        "setup_graphify",
                        "setup_context_discipline",
                        "verify_setup",
                    }
                break
finally:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
PY

echo "APM skills and VS Code user MCP setup passed"
