# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Tests for the process-description overlay adapter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import process_overlay_adapter as adapter
import pytest
from process_overlay_adapter import build_overlay, strip_version

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
    assert all(
        node.provenance.repo == source_repo
        and str(tmp_path) not in node.provenance.repo
        for node in nodes
    )
    assert all(
        edge.provenance.repo == source_repo
        and str(tmp_path) not in edge.provenance.repo
        for edge in edges
    )
    assert all(
        node.provenance.sha == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        for node in nodes
    )
    assert all(
        edge.provenance.sha == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        for edge in edges
    )


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
