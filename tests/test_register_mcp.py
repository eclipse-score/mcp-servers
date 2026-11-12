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

from ruamel.yaml import YAML

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
    assert opencode["mcp"]["servers"]["score-codegraph"]["command"] == [command]
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


def test_registers_shared_server_for_remote_user(tmp_path: Path) -> None:
    assert register_mcp.register(
        tmp_path, installed("claude", "graphify-codegraph")
    ) == ["claude"]
    config = json.loads((tmp_path / ".claude.json").read_text())
    assert config["mcpServers"]["score-codegraph"]["command"] == (
        "/usr/bin/graphify-codegraph"
    )


def test_feature_test_project_is_discoverable() -> None:
    project = SCRIPT.parents[2]
    tests = project / "test/agent-context"
    assert (tests / "test.sh").is_file()
    scenarios = json.loads((tests / "scenarios.json").read_text())
    assert scenarios
    for name, scenario in scenarios.items():
        assert (tests / f"{name}.sh").is_file()
        assert "agent-context" in scenario["features"]
        assert "|| true" not in scenario.get("postCreateCommand", "")


def test_feature_workflow_does_not_hide_failures() -> None:
    workflow = YAML(typ="safe").load(
        (SCRIPT.parents[3] / ".github/workflows/test-feature.yaml").read_text()
    )
    for job in workflow["jobs"].values():
        assert not job.get("continue-on-error", False)
        for step in job["steps"]:
            assert not step.get("continue-on-error", False)
            command = step.get("run", "")
            assert "--platform" not in command
            if "devcontainer features test" in command:
                assert "--project-folder features" in command
    consumer = workflow["jobs"]["consumer-test"]
    commands = "\n".join(step.get("run", "") for step in consumer["steps"])
    assert "devcontainer up --workspace-folder" in commands
    assert "devcontainer exec --workspace-folder" in commands
    assert "docker images" not in commands
