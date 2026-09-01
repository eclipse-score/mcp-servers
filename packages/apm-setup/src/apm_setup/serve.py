#!/usr/bin/env python3
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

"""Small stdio MCP server for explicit local APM setup operations."""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

TOOLS = [
    {
        "name": "setup_graphify",
        "description": (
            "Install graphify when requested and generate the repository graph."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "install_graphify": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "setup_context_discipline",
        "description": "Create local working-memory storage for a repository.",
        "inputSchema": {
            "type": "object",
            "properties": {"repo_path": {"type": "string"}},
        },
    },
    {
        "name": "verify_setup",
        "description": "Check graphify and local working-memory setup state.",
        "inputSchema": {
            "type": "object",
            "properties": {"repo_path": {"type": "string"}},
        },
    },
]


def repo_from(arguments: dict[str, Any]) -> Path:
    return Path(arguments.get("repo_path", ".")).expanduser().resolve()


def add_gitignore_entry(repo: Path, entry: str) -> None:
    gitignore = repo / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""
    lines = existing.splitlines()
    if entry not in lines:
        prefix = "" if not existing or existing.endswith("\n") else "\n"
        gitignore.write_text(existing + prefix + entry + "\n")


def setup_graphify(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = repo_from(arguments)
    if not (repo / ".git").exists():
        raise ValueError(f"Not a git repository: {repo}")

    graphify = shutil.which("graphify")
    installed = False
    if graphify is None and arguments.get("install_graphify", False):
        subprocess.run(["uv", "tool", "install", "graphifyy[mcp]==0.9.53"], check=True)
        graphify = shutil.which("graphify")
        installed = True
    if graphify is None:
        return {
            "ok": False,
            "repo_path": str(repo),
            "graphify_installed": False,
            "graph_path": str(repo / "graphify-out/graph.json"),
            "next": "Call setup_graphify with install_graphify=true.",
        }

    subprocess.run([graphify, "extract", str(repo), "--code-only"], check=True)
    add_gitignore_entry(repo, "graphify-out/")
    return {
        "ok": True,
        "repo_path": str(repo),
        "graphify_installed": True,
        "installed_now": installed,
        "graph_path": str(repo / "graphify-out/graph.json"),
    }


def setup_context_discipline(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = repo_from(arguments)
    if not (repo / ".git").exists():
        raise ValueError(f"Not a git repository: {repo}")
    (repo / ".score-local").mkdir(exist_ok=True)
    add_gitignore_entry(repo, ".score-local/")
    return {
        "ok": True,
        "repo_path": str(repo),
        "local_store": str(repo / ".score-local"),
    }


def verify_setup(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = repo_from(arguments)
    return {
        "ok": True,
        "repo_path": str(repo),
        "graphify_installed": shutil.which("graphify") is not None,
        "graph_exists": (repo / "graphify-out/graph.json").exists(),
        "context_store_exists": (repo / ".score-local").is_dir(),
    }


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "setup_graphify":
        return setup_graphify(arguments)
    if name == "setup_context_discipline":
        return setup_context_discipline(arguments)
    if name == "verify_setup":
        return verify_setup(arguments)
    raise ValueError(f"Unknown tool: {name}")


def response(
    request_id: Any, result: Any = None, error: dict[str, Any] | None = None
) -> str:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is None:
        payload["result"] = result
    else:
        payload["error"] = error
    return json.dumps(payload)


def handle(request: dict[str, Any]) -> str | None:
    if request.get("method") == "notifications/initialized":
        return None
    request_id = request.get("id")
    method = request.get("method")
    if method == "initialize":
        return response(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "apm-setup", "version": "0.1.0"},
            },
        )
    if method == "tools/list":
        return response(request_id, {"tools": TOOLS})
    if method == "tools/call":
        params = request.get("params", {})
        try:
            result = call_tool(params["name"], params.get("arguments", {}))
            return response(
                request_id, {"content": [{"type": "text", "text": json.dumps(result)}]}
            )
        except (KeyError, OSError, subprocess.CalledProcessError, ValueError) as exc:
            return response(request_id, error={"code": -32000, "message": str(exc)})
    return response(
        request_id, error={"code": -32601, "message": f"Unknown method: {method}"}
    )


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            output = handle(json.loads(line))
        except (json.JSONDecodeError, TypeError) as exc:
            output = response(
                None,
                error={"code": -32700, "message": f"Invalid JSON-RPC request: {exc}"},
            )
        if output is not None:
            sys.stdout.write(output + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
