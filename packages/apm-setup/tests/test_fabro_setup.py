# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


@pytest.fixture
def setup_module() -> ModuleType:
    source = Path(__file__).resolve().parents[1] / "src" / "apm_setup" / "serve.py"
    spec = importlib.util.spec_from_file_location("apm_setup_fabro_under_test", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_setup_fabro_reports_missing_cli_without_running_anything(
    setup_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(setup_module.shutil, "which", lambda _name: None)

    def forbidden(command: list[str], **kwargs: Any) -> None:
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(setup_module.subprocess, "run", forbidden)
    result = setup_module.setup_fabro({})

    assert result["ok"] is False
    assert result["fabro_installed"] is False
    assert result["installed_now"] is False
    assert "install_fabro=true" in result["next"]


def test_setup_fabro_reads_version_from_installed_cli(
    setup_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(setup_module.shutil, "which", lambda _name: "/bin/fabro")
    calls: list[list[str]] = []

    def fake_version(
        command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="fabro 0.0.0-test\n")

    monkeypatch.setattr(setup_module.subprocess, "run", fake_version)
    result = setup_module.setup_fabro({})

    assert calls == [["/bin/fabro", "--version"]]
    assert result["ok"] is True
    assert result["fabro_version"] == "fabro 0.0.0-test"
    assert result["installed_now"] is False


def test_install_fabro_uses_documented_homebrew_command(
    setup_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    installed = {"done": False}

    def which(name: str) -> str | None:
        if name == "fabro":
            return "/usr/local/bin/fabro" if installed["done"] else None
        if name == "brew":
            return "/usr/local/bin/brew"
        return None

    commands: list[list[str]] = []

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if command[0] == "brew":
            commands.append(command)
            if command[1] == "install":
                installed["done"] = True
            return subprocess.CompletedProcess(command, 0)
        assert command == ["/usr/local/bin/fabro", "--version"]
        return subprocess.CompletedProcess(command, 0, stdout="fabro 0.0.0-test\n")

    monkeypatch.setattr(setup_module.shutil, "which", which)
    monkeypatch.setattr(setup_module.subprocess, "run", run)
    result = setup_module.setup_fabro({"install_fabro": True})

    assert commands == [
        ["brew", "tap", "fabro-sh/tap"],
        ["brew", "trust", "--formula", "fabro-sh/tap/fabro-nightly"],
        ["brew", "install", "fabro-sh/tap/fabro-nightly"],
    ]
    assert result["ok"] is True
    assert result["installed_now"] is True


def test_install_fabro_refuses_without_homebrew(
    setup_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(setup_module.shutil, "which", lambda _name: None)
    with pytest.raises(ValueError, match="Homebrew is required"):
        setup_module.setup_fabro({"install_fabro": True})


def test_verify_setup_includes_fabro_status(
    setup_module: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setattr(setup_module.shutil, "which", lambda _name: None)

    status = setup_module.verify_setup({"repo_path": str(repo)})

    assert status["fabro_installed"] is False
    assert status["fabro_path"] is None
    assert status["fabro_version"] is None


def test_setup_fabro_is_exposed_as_mcp_tool(setup_module: ModuleType) -> None:
    listed = json.loads(
        setup_module.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) or "{}"
    )
    names = {tool["name"] for tool in listed["result"]["tools"]}

    assert "setup_fabro" in names
    assert "verify_setup" in names
