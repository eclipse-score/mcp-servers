#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
"""Register the S-CORE code graph MCP server for the coding agents in this container.

Only the ``score-codegraph`` entry is added or updated, other settings are kept.
Configs that cannot be parsed are left untouched. Never fails container creation.
"""

import json
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
    servers[NAME] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".agent-context")
    partial.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    partial.replace(path)
    return True


def update_codex(path: Path, command: str) -> bool:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if f"[mcp_servers.{NAME}]" in text:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    section = f"[mcp_servers.{NAME}]\ncommand = {json.dumps(command)}\n"
    path.write_text(text + ("\n" if text else "") + section, encoding="utf-8")
    return True


def register(home: Path, which: Which = shutil.which) -> list[str]:
    """Register the server for every agent that is installed or configured."""
    command = str(home / ".local" / "bin" / "graphify-codegraph")
    targets: list[tuple[str, Path, Callable[[Path], bool]]] = [
        (
            "claude",
            home / ".claude.json",
            lambda p: update_json(
                p, "mcpServers", {"type": "stdio", "command": command, "args": []}
            ),
        ),
        (
            "copilot",
            home / ".copilot" / "mcp-config.json",
            lambda p: update_json(
                p,
                "mcpServers",
                {"type": "local", "command": command, "args": [], "tools": ["*"]},
            ),
        ),
        (
            "opencode",
            home / ".config" / "opencode" / "opencode.json",
            lambda p: update_json(
                p, "mcp", {"type": "local", "command": [command], "enabled": True}
            ),
        ),
        ("codex", home / ".codex" / "config.toml", lambda p: update_codex(p, command)),
    ]
    registered: list[str] = []
    for agent, path, update in targets:
        present = which(agent) is not None or path.exists() or path.parent.is_dir()
        if path.parent == home:
            present = which(agent) is not None or path.exists()
        if present and update(path):
            registered.append(agent)
    return registered


def main() -> int:
    home = Path.home()
    if not (home / ".local" / "bin" / "graphify-codegraph").exists():
        warn("graphify-codegraph is not installed, nothing to register")
        return 0
    try:
        agents = register(home)
    except OSError as exc:
        warn(f"registration failed: {exc}")
        return 0
    print(f"agent-context: registered {NAME} for {', '.join(agents) or 'no agent'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
