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
    ]
    assert CodeGraphSource().load(tmp_path).nodes == ()
    assert OverlaySource().load(tmp_path).nodes == ()
    assert ProcessSource().load(tmp_path).nodes == ()
    assert SessionSource().load(tmp_path).nodes == ()


def test_process_source_loads_provenance_and_layer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "process.json"
    _process_graph(path)
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(path))

    graph = MergedGraph.build(tmp_path)

    node = graph.nodes["gd_req__one"]
    assert node.layer == "process"
    assert node.provenance is not None
    assert node.provenance.repo == "eclipse-score/process_description"
    assert node.provenance.adapter == "process_description"
    assert node.provenance.sha == "sha256:def"
    assert node.provenance.observed_at == "2026-01-01T00:00:00Z"
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

    source = ProcessSource().load(tmp_path)

    assert source.edges == ()
    assert source.nodes
