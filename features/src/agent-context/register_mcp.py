#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
"""Register agent-context MCP servers while preserving existing client config."""

import json
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

NAME = "score-codegraph"
Which = Callable[[str], str | None]


def warn(message: str) -> None:
    print(f"agent-context: {message}", file=sys.stderr)


def update_json(path: Path, key: str, entry: dict[str, Any]) -> bool:
    return update_json_mapping(path, key, {NAME: entry})


def update_json_mapping(
    path: Path,
    key: str,
    entries: dict[str, dict[str, Any]],
    remove_keys: tuple[str, ...] = (),
) -> bool:
    data: Any = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            warn(f"skipping {path}: not valid JSON")
            return False
    if not isinstance(data, dict):
        warn(f"skipping {path}: unexpected content")
        return False
    config: dict[str, Any] = data  # type: ignore[assignment]
    if not path.exists() and path.name == "opencode.json":
        config["$schema"] = "https://opencode.ai/config.json"
    servers = config.setdefault(key, {})
    if not isinstance(servers, dict):
        warn(f"skipping {path}: {key} is not a mapping")
        return False
    for name in remove_keys:
        servers.pop(name, None)
    servers.update(entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".agent-context")
    partial.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    # Preserve original file permissions if file exists
    if path.exists():
        original_mode = path.stat().st_mode
        partial.replace(path)
        path.chmod(original_mode)
    else:
        partial.replace(path)
    return True


def vscode_user_mcp_paths(home: Path) -> list[Path]:
    agent_folder = os.environ.get("VSCODE_AGENT_FOLDER")
    if agent_folder:
        server_roots = [Path(agent_folder).expanduser()]
    else:
        server_roots = [home / ".vscode-server", home / ".vscode-server-insiders"]
        existing_roots = [root for root in server_roots if root.exists()]
        server_roots = existing_roots or server_roots[:1]

    paths: list[Path] = []
    for server_root in server_roots:
        user_dir = server_root / "data" / "User"
        paths.append(user_dir / "mcp.json")
        profiles_dir = user_dir / "profiles"
        if profiles_dir.is_dir():
            paths.extend(sorted(profiles_dir.glob("*/mcp.json")))
    return paths


def update_vscode_user_mcp(home: Path, graph_command: str) -> list[str]:
    setup_package = home / ".apm" / "apm_modules" / "_local" / "apm-setup"
    if not setup_package.is_dir():
        warn(
            "skipping VS Code MCP registration: "
            f"APM package not found at {setup_package}"
        )
        return []

    uv_command = shutil.which("uv") or "uv"
    workspace = Path(
        os.environ.get("AGENT_CONTEXT_WORKSPACE", str(Path.cwd()))
    ).resolve()
    entries = {
        "graphify-codegraph": {
            "type": "stdio",
            "command": graph_command,
            "args": ["--repo-path", str(workspace)],
        },
        "apm-setup": {
            "type": "stdio",
            "command": uv_command,
            "args": ["run", "--project", str(setup_package), "apm-setup"],
        },
    }
    updated = []
    for path in vscode_user_mcp_paths(home):
        if update_json_mapping(
            path, "servers", entries, remove_keys=("score-codegraph",)
        ):
            updated.append("vscode-copilot-chat")
    return updated


def update_codex(path: Path, command: str) -> bool:
    """Update or add the MCP server entry in Codex TOML config."""
    import re

    text = path.read_text(encoding="utf-8") if path.exists() else ""

    # Check for existing entry (including quoted forms)
    pattern = rf'^\[mcp_servers\.["\']?{re.escape(NAME)}["\']?\]'
    if re.search(pattern, text, re.MULTILINE):
        return True

    path.parent.mkdir(parents=True, exist_ok=True)
    section = f"\n[mcp_servers.{NAME}]\ncommand = {json.dumps(command)}\n"
    path.write_text(text + section, encoding="utf-8")
    return True


def _update_opencode(path: Path, command: str) -> bool:
    """Register for OpenCode V2 (mcp.servers) and clean up V1 (mcp.<name>)."""
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            warn(f"skipping {path}: not valid JSON")
            return False
    if not isinstance(data, dict):
        warn(f"skipping {path}: unexpected content")
        return False
    if not path.exists():
        data["$schema"] = "https://opencode.ai/config.json"
    mcp = data.setdefault("mcp", {})
    if not isinstance(mcp, dict):
        warn(f"skipping {path}: mcp is not a mapping")
        return False
    # Remove legacy V1 flat entry (issue #56602)
    mcp.pop(NAME, None)
    servers = mcp.setdefault("servers", {})
    if not isinstance(servers, dict):
        warn(f"skipping {path}: mcp.servers is not a mapping")
        return False
    servers[NAME] = {
        "type": "local",
        "command": [command],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".agent-context")
    partial.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if path.exists():
        original_mode = path.stat().st_mode
        partial.replace(path)
        path.chmod(original_mode)
    else:
        partial.replace(path)
    return True


def register(home: Path, which: Which = shutil.which) -> list[str]:
    """Register the server for every agent that is installed or configured."""
    command = which("graphify-codegraph") or str(
        home / ".local" / "bin" / "graphify-codegraph"
    )
    targets: list[tuple[str, Path, Callable[[Path], bool]]] = [
        (
            "claude",
            home / ".claude.json",
            lambda p: update_json(
                p, "mcpServers", {"type": "stdio", "command": command, "args": []}
            ),
        ),
        (
            "opencode",
            home / ".config" / "opencode" / "opencode.json",
            lambda p: _update_opencode(p, command),
        ),
        ("codex", home / ".codex" / "config.toml", lambda p: update_codex(p, command)),
    ]
    registered: list[str] = []
    for agent, path, update in targets:
        present = which(agent) is not None or path.exists() or path.parent.is_dir()
        if path.parent == home:
            present = which(agent) is not None or path.exists()
        if present:
            try:
                if update(path):
                    registered.append(agent)
            except OSError as exc:
                warn(f"could not register for {agent}: {exc}")
                continue
    registered.extend(update_vscode_user_mcp(home, command))
    return registered


def main() -> int:
    home = Path.home()
    if not (
        shutil.which("graphify-codegraph")
        or (home / ".local" / "bin" / "graphify-codegraph").exists()
    ):
        warn("graphify-codegraph is not installed, nothing to register")
        return 0
    try:
        agents = register(home)
    except OSError as exc:
        warn(f"registration failed: {exc}")
        return 0
    print(f"agent-context: registered for {', '.join(agents) or 'no agent'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
