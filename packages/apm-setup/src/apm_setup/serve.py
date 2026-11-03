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

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

TOOLS = [
    {
        "name": "setup_graphify",
        "description": (
            "Prepare the repository graph from the published cache, falling back "
            "to local extraction; force_local requests a local refresh."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "install_graphify": {"type": "boolean", "default": False},
                "force_local": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "setup_context_discipline",
        "description": "Create repository-keyed working-memory storage in user state.",
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


def graph_cache(repo: Path) -> Path:
    """Match the graphify runtime's repository-keyed user cache."""
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    digest = hashlib.sha256(str(repo).encode()).hexdigest()[:12]
    return Path(base) / "score-agent" / f"{repo.name}-{digest}"


def context_store(repo: Path) -> Path:
    """Match the context runtime's repository-keyed user state."""
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    if not base.is_absolute():
        base = Path.home() / ".local" / "state"
    digest = hashlib.sha256(str(repo).encode("utf-8")).hexdigest()[:16]
    return base / "score-agent" / f"{repo.name}-{digest}"


def setup_graphify(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = repo_from(arguments)
    if not (repo / ".git").exists():
        raise ValueError(f"Not a git repository: {repo}")

    cache = graph_cache(repo)
    graphify = shutil.which("graphify-codegraph")
    installed = False
    if graphify is None and arguments.get("install_graphify", False):
        source = (
            "git+https://github.com/eclipse-score/mcp-servers@"
            "a85a027acff417ef2718c07daf62491e98cdb4fd"
            "#subdirectory=packages/graphify-codegraph"
        )
        subprocess.run(
            ["uv", "tool", "install", "--with-executables-from", "graphifyy", source],
            check=True,
        )
        graphify = shutil.which("graphify-codegraph")
        installed = True
    if graphify is None:
        return {
            "ok": False,
            "repo_path": str(repo),
            "graphify_installed": False,
            "graph_path": str(cache / "graph.json"),
            "next": "Install graphify-codegraph or use install_graphify=true.",
        }

    command = [graphify, "--prepare-only", "--repo-path", str(repo)]
    if arguments.get("force_local", False):
        command.append("--force-local")
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    try:
        prepared = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("graphify-codegraph must support --prepare-only") from exc
    return {
        **prepared,
        "repo_path": str(repo),
        "graphify_installed": True,
        "installed_now": installed,
    }


def setup_context_discipline(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = repo_from(arguments)
    if not (repo / ".git").exists():
        raise ValueError(f"Not a git repository: {repo}")
    store = context_store(repo)
    store.mkdir(parents=True, exist_ok=True)
    store.chmod(0o700)
    return {
        "ok": True,
        "repo_path": str(repo),
        "local_store": str(store),
    }


def verify_setup(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = repo_from(arguments)
    graph = graph_cache(repo) / "graph.json"
    if not graph.exists():
        graph = repo / "graphify-out" / "graph.json"
    store = context_store(repo)
    return {
        "ok": True,
        "repo_path": str(repo),
        "graphify_installed": shutil.which("graphify") is not None,
        "graph_exists": graph.exists(),
        "graph_path": str(graph),
        "context_store_exists": store.is_dir(),
        "local_store": str(store),
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
