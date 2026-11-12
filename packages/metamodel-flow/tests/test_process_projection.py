# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Tests for the process-description projection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import process_projection as adapter
import pytest
from process_projection import build_overlay, strip_version, write_artifact

FIXTURE = Path(__file__).parent / "data" / "process_needs_min.json"
OBSERVED_AT = "2026-07-22T00:00:00+00:00"


def test_strip_version() -> None:
    assert strip_version("wf__x[version==1]") == "wf__x"
    assert strip_version("wf__x") == "wf__x"


def test_build_overlay_is_deterministic_and_small(tmp_path: Path) -> None:
    source_repo = "eclipse-score/process_description"
    first = build_overlay(FIXTURE, repo=source_repo, observed_at=OBSERVED_AT)
    second = build_overlay(FIXTURE, repo=source_repo, observed_at=OBSERVED_AT)
    nodes, edges, report = first

    assert first == second
    assert report.nodes == 8
    assert report.edges == 10
    assert report.skipped_needs == 1
    assert report.ignored_types == 1
    assert report.skipped_links == 2
    assert [node.id for node in nodes] == sorted(node.id for node in nodes)
    assert [(edge.source, edge.relation, edge.target) for edge in edges] == sorted(
        (edge.source, edge.relation, edge.target) for edge in edges
    )

    workflow = next(node for node in nodes if node.id == "wf__one")
    assert len(workflow.title) == 200
    assert "\n" not in workflow.title
    assert "\t" not in workflow.title
    assert all(set(node.attributes) <= {"status", "tags"} for node in nodes)


def test_main_writes_deterministic_golden_projection(tmp_path: Path) -> None:
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    arguments = [
        "--needs",
        str(FIXTURE),
        "--out",
        str(first_path),
        "--source-commit",
        "abc123",
        "--observed-at",
        OBSERVED_AT,
    ]

    assert adapter.main(arguments) == 0
    assert adapter.main([*arguments[0:3], str(second_path), *arguments[4:]]) == 0

    first = first_path.read_bytes()
    assert first == second_path.read_bytes()
    document = json.loads(first)
    assert list(document) == ["schema_version", "source", "nodes", "edges"]
    assert document["schema_version"] == 1
    assert list(document["source"]) == [
        "repo",
        "commit",
        "digest",
        "generated_at",
    ]
    assert document["source"] == {
        "repo": "eclipse-score/process_description",
        "commit": "abc123",
        "digest": f"sha256:{hashlib.sha256(FIXTURE.read_bytes()).hexdigest()}",
        "generated_at": OBSERVED_AT,
    }
    assert [node["id"] for node in document["nodes"]] == sorted(
        node["id"] for node in document["nodes"]
    )
    assert [
        (edge["source"], edge["relation"], edge["target"]) for edge in document["edges"]
    ] == sorted(
        (edge["source"], edge["relation"], edge["target"]) for edge in document["edges"]
    )
    assert document["nodes"][0] == {
        "id": "gd_req__one",
        "type": "gd_req",
        "title": "A development requirement",
        "attributes": {"status": "approved", "tags": "process,requirement"},
    }


def test_write_artifact_returns_projection_report(tmp_path: Path) -> None:
    output = tmp_path / "process_graph.json"

    report = write_artifact(FIXTURE, output, "abc123", OBSERVED_AT)

    assert report.nodes == 8
    assert report.edges == 10
    assert output.exists()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "top-level"),
        ({"versions": {}}, "exactly one"),
        ({"versions": {"0.1": []}}, "version"),
        ({"versions": {"0.1": {"needs": []}}}, "needs"),
    ],
)
def test_malformed_process_input_is_rejected(
    tmp_path: Path, payload: object, message: str
) -> None:
    path = tmp_path / "needs.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        build_overlay(path, repo=str(tmp_path), observed_at=OBSERVED_AT)


def test_non_list_link_field_is_skipped(tmp_path: Path) -> None:
    path = tmp_path / "needs.json"
    path.write_text(
        '{"versions":{"0.1":{"needs":{"wf":{"id":"wf","type":"workflow",'
        '"title":"Workflow","responsible":"rl"}}}}}',
        encoding="utf-8",
    )

    _, edges, report = build_overlay(
        path, repo="eclipse-score/process_description", observed_at=OBSERVED_AT
    )

    assert not edges
    assert report.skipped_links == 1


@pytest.mark.parametrize(
    ("limits", "message"),
    [
        ((1, 60000, 200, 500), "node count"),
        ((20000, 1, 200, 500), "edge count"),
    ],
)
def test_policy_count_limits_are_enforced(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    limits: tuple[int, int, int, int],
    message: str,
) -> None:
    monkeypatch.setattr(adapter, "_policy_limits", lambda _: (limits, False))

    with pytest.raises(ValueError, match=message):
        build_overlay(
            FIXTURE,
            repo="eclipse-score/process_description",
            observed_at=OBSERVED_AT,
        )
