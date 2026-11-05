# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

import json
from pathlib import Path

import pytest
from context_merge import MergedGraph
from context_policy import Policy
from context_sources import (
    DEFAULT_SOURCES,
    CodeGraphSource,
    OverlaySource,
    ProcessSource,
    SessionSource,
)


def _process_graph(path: Path, *, schema_version: int = 1) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "source": {
                    "repo": "eclipse-score/process_description",
                    "commit": "abc",
                    "digest": "sha256:def",
                    "generated_at": "2026-01-01T00:00:00Z",
                },
                "nodes": [
                    {
                        "id": "gd_req__one",
                        "type": "gd_req",
                        "title": "Requirement",
                        "attributes": {},
                    }
                ],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )


def test_default_sources_are_ordered_and_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(tmp_path / "missing-process.json"))
    assert [source.layer for source in DEFAULT_SOURCES] == [
        "code",
        "domain",
        "process",
        "collaboration",
        "requirements",
    ]
    policy = Policy()
    code = CodeGraphSource().load(tmp_path, policy)
    overlay = OverlaySource().load(tmp_path, policy)
    process = ProcessSource().load(tmp_path, policy)
    session = SessionSource().load(tmp_path, policy)
    assert code.nodes == () and not code.loaded
    assert overlay.nodes == () and not overlay.loaded
    assert process.nodes == () and not process.loaded
    assert session.nodes == () and not session.loaded


def test_process_source_loads_provenance_and_layer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "process.json"
    _process_graph(path)
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(path))

    source = ProcessSource().load(tmp_path, Policy())
    graph = MergedGraph.build(tmp_path)

    assert source.freshness is not None
    assert source.freshness.source_ref == "abc"
    assert source.freshness.current_ref == ""
    assert source.freshness.stale is False
    node = graph.nodes["gd_req__one"]
    assert node.layer == "process"
    assert node.provenance is not None
    assert node.provenance.repo == "eclipse-score/process_description"
    assert node.provenance.adapter == "process_description"
    assert node.provenance.sha == "sha256:def"
    assert node.provenance.observed_at == "2026-01-01T00:00:00Z"
    assert dict(node.attributes) == {}
    assert "process" in graph.loaded_layers


def test_malformed_process_source_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "process.json"
    _process_graph(path, schema_version=2)
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(path))

    graph = MergedGraph.build(tmp_path)

    assert "gd_req__one" not in graph.nodes
    assert "process" not in graph.loaded_layers


def test_unknown_process_edge_target_is_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "process.json"
    _process_graph(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["edges"] = [
        {"source": "gd_req__one", "target": "missing", "relation": "satisfies"}
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(path))

    source = ProcessSource().load(tmp_path, Policy())

    assert source.edges == ()
    assert source.nodes


def test_source_file_index_preserves_relative_and_absolute_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    absolute = tmp_path / "src" / "b.py"
    (graph_dir / "graph.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "code__relative",
                        "label": "relative",
                        "file_type": "code",
                        "source_file": "./src/a.py",
                    },
                    {
                        "id": "code__absolute",
                        "label": "absolute",
                        "file_type": "code",
                        "source_file": str(absolute),
                    },
                ],
                "links": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(tmp_path / "missing.json"))

    graph = MergedGraph.build(tmp_path)

    assert graph.source_file_index["./src/a.py"] == "code__relative"
    assert graph.source_file_index["src/a.py"] == "code__relative"
    assert graph.source_file_index[str(absolute)] == "code__absolute"
    assert graph.source_file_index["src/b.py"] == "code__absolute"


def test_process_policy_disables_environment_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy_dir = tmp_path / "score-context"
    policy_dir.mkdir()
    policy_dir.joinpath("policy.toml").write_text(
        "version = 1\n[process]\nenabled = false\n",
        encoding="utf-8",
    )
    process_path = tmp_path / "process.json"
    _process_graph(process_path)
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(process_path))

    graph = MergedGraph.build(tmp_path)

    assert "process" not in graph.loaded_layers
    assert "gd_req__one" not in graph.nodes


def test_relative_environment_process_path_is_repository_relative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _process_graph(tmp_path / "process.json")
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", "process.json")

    graph = MergedGraph.build(tmp_path)

    assert "process" in graph.loaded_layers
    assert "gd_req__one" in graph.nodes


def test_consumer_apm_module_process_graph_precedes_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = (
        tmp_path
        / "apm_modules"
        / "_local"
        / "deadbeef"
        / "metamodel-flow"
        / "model"
        / "process_graph.json"
    )
    path.parent.mkdir(parents=True)
    _process_graph(path)

    monkeypatch.delenv("SCORE_PROCESS_GRAPH", raising=False)
    graph = MergedGraph.build(tmp_path)

    assert "process" in graph.loaded_layers
    assert "gd_req__one" in graph.nodes


def test_consumer_apm_module_process_graph_selection_is_sorted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = (
        tmp_path
        / "apm_modules"
        / "_local"
        / "aaaa"
        / "metamodel-flow"
        / "model"
        / "process_graph.json"
    )
    second = (
        tmp_path
        / "apm_modules"
        / "_local"
        / "zzzz"
        / "metamodel-flow"
        / "model"
        / "process_graph.json"
    )
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    _process_graph(first)
    _process_graph(second)
    second_payload = json.loads(second.read_text(encoding="utf-8"))
    second_payload["nodes"][0]["id"] = "gd_req__second"
    second.write_text(json.dumps(second_payload), encoding="utf-8")

    monkeypatch.delenv("SCORE_PROCESS_GRAPH", raising=False)
    graph = MergedGraph.build(tmp_path)

    assert "gd_req__one" in graph.nodes
    assert "gd_req__second" not in graph.nodes


def test_graph_build_loads_policy_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import context_policy

    calls = 0
    original = context_policy.load_policy

    def counted_load_policy(repo: Path):
        nonlocal calls
        calls += 1
        return original(repo)

    monkeypatch.setattr(context_policy, "load_policy", counted_load_policy)
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(tmp_path / "missing.json"))

    MergedGraph.build(tmp_path)

    assert calls == 1
