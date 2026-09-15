# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

from __future__ import annotations

import json
from pathlib import Path

import pytest
from context_merge import MergedGraph
from context_policy import OverlayPolicy, Policy, RequirementsPolicy
from context_sources import DEFAULT_SOURCES, RequirementsSource


def _artifact(
    path: Path,
    *,
    schema_version: int = 1,
    commit: str = "abc",
    nodes: list[dict[str, object]] | None = None,
    edges: list[dict[str, str]] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "source": {
                    "repo": "eclipse-score/baselibs",
                    "commit": commit,
                    "digest": "sha256:def",
                    "generated_at": "2026-01-01T00:00:00Z",
                },
                "nodes": nodes
                or [
                    {
                        "id": "comp_req__one",
                        "type": "comp_req",
                        "title": "Requirement",
                        "attributes": {"version": "2", "content": "Body"},
                    }
                ],
                "edges": edges or [],
            }
        ),
        encoding="utf-8",
    )


def test_requirements_source_missing_and_disabled_are_unloaded(
    tmp_path: Path,
) -> None:
    source = RequirementsSource()
    assert not source.load(tmp_path, Policy()).loaded
    disabled = Policy(requirements=RequirementsPolicy(enabled=False))
    assert not source.load(tmp_path, disabled).loaded


def test_requirements_source_rejects_schema_and_limits(tmp_path: Path) -> None:
    path = tmp_path / "requirements.json"
    _artifact(path, schema_version=2)
    assert (
        not RequirementsSource()
        .load(tmp_path, Policy(requirements=RequirementsPolicy(path=str(path))))
        .loaded
    )

    _artifact(
        path,
        nodes=[
            {
                "id": "comp_req__one",
                "type": "comp_req",
                "title": "One",
                "attributes": {},
            },
            {
                "id": "comp_req__two",
                "type": "comp_req",
                "title": "Two",
                "attributes": {},
            },
        ],
    )
    limited = Policy(
        overlay=OverlayPolicy(max_nodes=1),
        requirements=RequirementsPolicy(path=str(path)),
    )
    assert not RequirementsSource().load(tmp_path, limited).loaded


def test_requirements_source_loads_provenance_attributes_and_drops_dangling_edge(
    tmp_path: Path,
) -> None:
    path = tmp_path / "requirements.json"
    _artifact(
        path,
        nodes=[
            {
                "id": "comp_req__one",
                "type": "comp_req",
                "title": "Requirement",
                "attributes": {"version": "2"},
            },
            {
                "id": "feat_req__one",
                "type": "feat_req",
                "title": "Feature",
                "attributes": {},
            },
        ],
        edges=[
            {
                "source": "comp_req__one",
                "relation": "derived_from",
                "target": "feat_req__one",
            },
            {
                "source": "comp_req__one",
                "relation": "covers",
                "target": "missing",
            },
        ],
    )
    policy = Policy(requirements=RequirementsPolicy(path=str(path)))

    source = RequirementsSource().load(tmp_path, policy)

    assert source.loaded
    assert source.freshness is not None
    assert source.freshness.source_ref == "abc"
    assert source.freshness.current_ref == ""
    assert source.freshness.stale is False
    node = source.nodes[0]
    assert node.layer == "requirements"
    assert dict(node.attributes)["version"] == "2"
    assert node.provenance is not None
    assert node.provenance.adapter == "requirements_projection"
    assert len(source.edges) == 1
    assert source.edges[0].provenance is not None
    assert source.edges[0].provenance.adapter == "requirements_projection"


def test_requirements_source_honors_environment_and_policy_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / "env.json"
    policy_path = tmp_path / "policy.json"
    _artifact(env_path)
    _artifact(policy_path)
    monkeypatch.setenv("SCORE_REQUIREMENTS_GRAPH", "env.json")
    env_source = RequirementsSource().load(tmp_path, Policy())
    assert env_source.loaded

    monkeypatch.delenv("SCORE_REQUIREMENTS_GRAPH")
    policy = Policy(requirements=RequirementsPolicy(path="policy.json"))
    policy_source = RequirementsSource().load(tmp_path, policy)
    assert policy_source.loaded


@pytest.mark.parametrize(
    ("source_ref", "current_ref", "stale"),
    [("abc", "abc", False), ("abc", "def", True)],
)
def test_requirements_source_freshness(
    tmp_path: Path,
    source_ref: str,
    current_ref: str,
    stale: bool,
) -> None:
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "refs" / "heads" / "main").write_text(current_ref + "\n", encoding="utf-8")
    path = tmp_path / "requirements.json"
    _artifact(path, commit=source_ref)

    source = RequirementsSource().load(
        tmp_path,
        Policy(requirements=RequirementsPolicy(path=str(path))),
    )

    assert source.loaded
    assert source.freshness is not None
    assert source.freshness.current_ref == current_ref
    assert source.freshness.stale is stale


def test_requirements_source_is_in_default_merge_with_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / ".score-local" / "requirements_graph.json"
    _artifact(
        path,
        nodes=[
            {
                "id": "comp_req__one",
                "type": "comp_req",
                "title": "Requirement",
                "attributes": {},
            },
            {
                "id": "feat_req__one",
                "type": "feat_req",
                "title": "Feature",
                "attributes": {},
            },
        ],
        edges=[
            {
                "source": "comp_req__one",
                "relation": "derived_from",
                "target": "feat_req__one",
            }
        ],
    )
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(tmp_path / "missing.json"))

    graph = MergedGraph.build(tmp_path)

    assert [source.layer for source in DEFAULT_SOURCES][-1] == "requirements"
    assert "requirements" in graph.loaded_layers
    node = graph.nodes["comp_req__one"]
    assert node.provenance is not None
    assert node.provenance.adapter == "requirements_projection"
    edge = graph.edges[("comp_req__one", "feat_req__one", "derived_from")]
    assert edge.provenance is not None
    assert edge.provenance.adapter == "requirements_projection"
