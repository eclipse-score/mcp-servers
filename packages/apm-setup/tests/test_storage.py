# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


@pytest.fixture
def setup_module() -> ModuleType:
    source = Path(__file__).resolve().parents[1] / "src" / "apm_setup" / "serve.py"
    spec = importlib.util.spec_from_file_location("apm_setup_under_test", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def consumer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / ".gitignore").write_text("existing-rule\n", encoding="utf-8")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return repo


def test_setup_preserves_consumer_and_reports_external_outputs(
    setup_module: ModuleType, consumer: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = sorted(consumer.iterdir())

    def installed_graphify(executable: str) -> str:
        return "/bin/graphify-codegraph"

    monkeypatch.setattr(setup_module.shutil, "which", installed_graphify)
    monkeypatch.setenv("GRAPHIFY_OUT", str(consumer / "unwanted-output"))

    def prepare(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert command[1:] == ["--prepare-only", "--repo-path", str(consumer)]
        assert kwargs["check"] is True
        output = setup_module.graph_cache(consumer)
        output.mkdir(parents=True)
        (output / "graph.json").write_text('{"nodes": [], "edges": []}')
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "graph_path": str(output / "graph.json"),
                    "source": "prebuilt",
                }
            ),
        )

    monkeypatch.setattr(setup_module.subprocess, "run", prepare)
    graph = setup_module.setup_graphify({"repo_path": str(consumer)})
    context = setup_module.setup_context_discipline({"repo_path": str(consumer)})
    status = setup_module.verify_setup({"repo_path": str(consumer)})

    assert Path(graph["graph_path"]).is_file()
    assert Path(context["local_store"]).is_dir()
    assert not Path(graph["graph_path"]).is_relative_to(consumer)
    assert not Path(context["local_store"]).is_relative_to(consumer)
    assert status["graph_exists"] and status["context_store_exists"]
    assert status["graph_path"] == graph["graph_path"]
    assert status["local_store"] == context["local_store"]
    assert sorted(consumer.iterdir()) == before
    assert (consumer / ".gitignore").read_text() == "existing-rule\n"


def test_setup_delegates_explicit_local_refresh(
    setup_module: ModuleType, consumer: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def installed(executable: str) -> str:
        return "/bin/graphify-codegraph"

    def prepare(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert command[-1] == "--force-local"
        return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}')

    monkeypatch.setattr(setup_module.shutil, "which", installed)
    monkeypatch.setattr(setup_module.subprocess, "run", prepare)
    assert setup_module.setup_graphify(
        {"repo_path": str(consumer), "force_local": True}
    )["ok"]


def test_missing_graphify_does_not_create_outputs(
    setup_module: ModuleType, consumer: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing_graphify(executable: str) -> None:
        return None

    monkeypatch.setattr(setup_module.shutil, "which", missing_graphify)
    result = setup_module.setup_graphify({"repo_path": str(consumer)})
    assert not result["ok"]
    assert not Path(result["graph_path"]).parent.exists()


def test_verify_missing_graph_reports_user_cache(
    setup_module: ModuleType, consumer: Path
) -> None:
    status = setup_module.verify_setup({"repo_path": str(consumer)})
    assert not status["graph_exists"]
    expected_graph = setup_module.graph_cache(consumer) / "graph.json"
    assert status["graph_path"] == str(expected_graph)


def test_setup_paths_match_runtime_defaults(
    setup_module: ModuleType, consumer: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    monkeypatch.setattr(
        sys,
        "path",
        [
            str(repo_root / "packages/context-discipline/src"),
            str(repo_root / "packages/graphify-codegraph/src"),
            *sys.path,
        ],
    )
    from context_sessions import resolve_local_store
    from graph_cache import cache_dir

    assert setup_module.context_store(consumer) == resolve_local_store(consumer)
    assert setup_module.graph_cache(consumer) == cache_dir(consumer)
