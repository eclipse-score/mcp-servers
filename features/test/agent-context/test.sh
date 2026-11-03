#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
set -euo pipefail

command -v python3
command -v uv
uv --version
test -f /usr/local/share/agent-context/register_mcp.py
test -x /usr/local/bin/graphify-codegraph
command -v graphify
test -x /usr/local/bin/graphify
graphify --help | grep -F 'benchmark [graph.json]'
python3 /usr/local/share/agent-context/register_mcp.py
python3 - <<'PY'
import json
import selectors
import subprocess

process = subprocess.Popen(
	["/usr/local/bin/graphify-codegraph"],
	stdin=subprocess.PIPE,
	stdout=subprocess.PIPE,
	text=True,
)
try:
	requests = [
		{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
			"protocolVersion": "2024-11-05",
			"capabilities": {},
			"clientInfo": {"name": "feature-test", "version": "1.0"},
		}},
		{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
		{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
	]
	for request in requests:
		process.stdin.write(json.dumps(request) + "\n")
		process.stdin.flush()
		if "id" not in request:
			continue
		with selectors.DefaultSelector() as selector:
			selector.register(process.stdout, selectors.EVENT_READ)
			while True:
				assert selector.select(timeout=120), "MCP server did not respond"
				line = process.stdout.readline()
				assert line, "MCP server exited before responding"
				response = json.loads(line)
				if response.get("id") != request["id"]:
					continue
				assert "error" not in response, response
				if request["id"] == 2:
					assert response["result"]["tools"], "MCP server has no tools"
				break
	print("MCP initialize and tools/list passed")
finally:
	process.terminate()
	try:
		process.wait(timeout=5)
	except subprocess.TimeoutExpired:
		process.kill()
		process.wait()
PY