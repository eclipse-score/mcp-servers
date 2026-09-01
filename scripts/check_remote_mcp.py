#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Start MCP servers from an APM-generated configuration and query their tools."""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import sys
from pathlib import Path


def main() -> int:
    config_path = Path(os.environ.get("MCP_CONFIG", ".vscode/mcp.json"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    servers = config.get("servers", config.get("mcpServers", {}))
    if not servers:
        raise RuntimeError(f"No MCP servers found in {config_path}")
    expected_servers = {"apm-setup", "graphify-codegraph", "context-discipline"}
    missing_servers = expected_servers - servers.keys()
    if missing_servers:
        raise RuntimeError(
            f"Missing expected MCP server(s): {', '.join(sorted(missing_servers))}"
        )

    for name, server in servers.items():
        command = server.get("command")
        args = server.get("args", [])
        if not command:
            raise RuntimeError(f"MCP server {name!r} has no command")
        print(f"Checking remote MCP server: {name}")
        process = subprocess.Popen(
            [command, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            assert process.stdin is not None
            assert process.stdout is not None
            requests = [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "ci-smoke-test", "version": "1.0"},
                    },
                },
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                },
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            ]
            for request in requests:
                process.stdin.write(json.dumps(request) + "\n")
                process.stdin.flush()
                if "id" not in request:
                    continue
                selector = selectors.DefaultSelector()
                selector.register(process.stdout, selectors.EVENT_READ)
                try:
                    while True:
                        if not selector.select(timeout=10):
                            raise RuntimeError(f"Timed out waiting for {name} response")
                        line = process.stdout.readline()
                        if line == "":
                            error = process.stderr.read().strip()
                            raise RuntimeError(
                                f"{name} exited before responding"
                                + (f": {error}" if error else "")
                            )
                        if not line.strip():
                            continue
                        response = json.loads(line)
                        if response.get("method", "").startswith("notifications/"):
                            continue
                        if "error" in response:
                            raise RuntimeError(f"{name} returned an error: {response}")
                        break
                finally:
                    selector.close()
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    print(f"Checked {len(servers)} remote MCP server(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
