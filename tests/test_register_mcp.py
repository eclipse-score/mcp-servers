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


import importlib.util
import json
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "features"
    / "src"
    / "agent-context"
    / "register_mcp.py"
)
spec = importlib.util.spec_from_file_location("register_mcp", SCRIPT)
assert spec is not None and spec.loader is not None
register_mcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(register_mcp)


def installed(*agents: str):
    return lambda name: f"/usr/bin/{name}" if name in agents else None


def test_registers_installed_agents(tmp_path: Path) -> None:
    agents = register_mcp.register(tmp_path, installed("claude", "codex", "opencode"))
    assert agents == ["claude", "opencode", "codex"]
    claude = json.loads((tmp_path / ".claude.json").read_text())
    command = str(tmp_path / ".local/bin/graphify-codegraph")
    assert claude["mcpServers"]["score-codegraph"]["command"] == command
    opencode = json.loads((tmp_path / ".config/opencode/opencode.json").read_text())
    assert opencode["mcp"]["score-codegraph"]["command"] == [command]
    assert not (tmp_path / ".copilot").exists()


def test_keeps_other_settings_and_is_idempotent(tmp_path: Path) -> None:
    config = tmp_path / ".claude.json"
    config.write_text(json.dumps({"theme": "dark", "mcpServers": {"other": {}}}))
    codex = tmp_path / ".codex" / "config.toml"
    codex.parent.mkdir()
    codex.write_text('model = "x"\n')
    for _ in range(2):
        register_mcp.register(tmp_path, installed())
    data = json.loads(config.read_text())
    assert data["theme"] == "dark"
    assert sorted(data["mcpServers"]) == ["other", "score-codegraph"]
    assert codex.read_text().count("[mcp_servers.score-codegraph]") == 1
    assert codex.read_text().startswith('model = "x"\n')


def test_leaves_invalid_config_untouched(tmp_path: Path) -> None:
    config = tmp_path / ".claude.json"
    config.write_text("{not json")
    assert register_mcp.register(tmp_path, installed("claude")) == []
    assert config.read_text() == "{not json"


def test_nothing_installed(tmp_path: Path) -> None:
    assert register_mcp.register(tmp_path, installed()) == []
    assert list(tmp_path.iterdir()) == []
