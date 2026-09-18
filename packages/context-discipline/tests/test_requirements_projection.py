# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

from __future__ import annotations

import json
from pathlib import Path

import requirements_projection as adapter
from requirements_projection import build_requirements, strip_version

OBSERVED_AT = "2026-07-22T00:00:00+00:00"


def _needs() -> dict[str, object]:
    long_title = "Requirement " + ("x" * 250)
    long_content = "Normative content " + ("y" * 600)
    return {
        "comp": {
            "id": "comp__one",
            "type": "comp",
            "title": "Context component",
        },
        "comp_req": {
            "id": "comp_req__one",
            "type": "comp_req",
            "title": long_title,
            "content": long_content,
            "status": "valid",
            "version": 2,
            "safety": "QM",
            "security": "NO",
            "reqtype": "Functional",
            "docname": "requirements/index",
            "derived_from": [
                "feat_req__one[version==1]",
                "feat_req__one[version==1]",
                "feat_req__missing",
            ],
            "satisfied_by": ["comp__one[version==1]"],
            "covers": ["aou_req__one[version==1]"],
        },
        "feat": {
            "id": "feat_req__one",
            "type": "feat_req",
            "title": "Feature requirement",
            "content": "Short feature content",
            "derived_from": ["stkh_req__one[version==1]"],
        },
        "stkh": {
            "id": "stkh_req__one",
            "type": "stkh_req",
            "title": "Stakeholder requirement",
        },
        "aou": {
            "id": "aou_req__one",
            "type": "aou_req",
            "title": "Consumer assumption",
        },
        "testcase": {
            "id": "testcase__one",
            "type": "testcase",
            "title": "Requirement test",
            "partially_verifies": ["comp_req__one[version==2]"],
        },
        "duplicate_first": {
            "id": "comp_req__duplicate",
            "type": "comp_req",
            "title": "Duplicate",
        },
        "duplicate_second": {
            "id": "comp_req__duplicate",
            "type": "comp_req",
            "title": "Duplicate again",
        },
        "ignored": {
            "id": "issue__one",
            "type": "issue",
            "title": "Ignored issue",
        },
        "not_a_need": "skip",
    }


def _write_needs(path: Path) -> None:
    path.write_text(
        json.dumps({"versions": {"1": {"needs": _needs()}}}),
        encoding="utf-8",
    )


def test_build_requirements_is_deterministic_and_preserves_requirement_metadata(
    tmp_path: Path,
) -> None:
    path = tmp_path / "needs.json"
    _write_needs(path)

    first = build_requirements(
        path,
    )
    second = build_requirements(
        path,
    )
    nodes, edges, report, digest = first

    assert first == second
    assert digest
    assert report.nodes == 7
    assert report.edges == 5
    assert report.skipped_needs == 2
    assert report.ignored_types == 1
    assert report.skipped_links == 1
    assert report.type_counts == {
        "aou_req": 1,
        "comp": 1,
        "comp_req": 2,
        "feat_req": 1,
        "stkh_req": 1,
        "testcase": 1,
    }
    assert [node.id for node in nodes] == sorted(node.id for node in nodes)
    assert [(edge.source, edge.relation, edge.target) for edge in edges] == sorted(
        (edge.source, edge.relation, edge.target) for edge in edges
    )
    assert len(edges) == len(
        {(edge.source, edge.relation, edge.target) for edge in edges}
    )
    requirement = next(node for node in nodes if node.id == "comp_req__one")
    assert len(requirement.title) == 200
    assert requirement.attributes["version"] == "2"
    assert requirement.attributes["content_truncated"] == "true"
    assert len(requirement.attributes["content"]) == 500
    feature = next(node for node in nodes if node.id == "feat_req__one")
    assert feature.attributes["content"] == "Short feature content"
    assert "content_truncated" not in feature.attributes
    assert "feat_req__missing" not in {edge.target for edge in edges}
    assert ("comp_req__one", "derived_from", "feat_req__one") in {
        (edge.source, edge.relation, edge.target) for edge in edges
    }
    assert ("testcase__one", "partially_verifies", "comp_req__one") in {
        (edge.source, edge.relation, edge.target) for edge in edges
    }
    assert strip_version("comp_req__one[version==2]") == "comp_req__one"


def test_main_writes_deterministic_requirements_artifact(tmp_path: Path) -> None:
    path = tmp_path / "needs.json"
    _write_needs(path)
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    arguments = [
        "--needs",
        str(path),
        "--out",
        str(first_path),
        "--repo",
        "eclipse-score/baselibs",
        "--source-ref",
        "abc123",
        "--observed-at",
        OBSERVED_AT,
    ]

    assert adapter.main(arguments) == 0
    assert adapter.main([*arguments[:3], str(second_path), *arguments[4:]]) == 0
    assert first_path.read_bytes() == second_path.read_bytes()
    document = json.loads(first_path.read_bytes())
    assert document["source"]["repo"] == "eclipse-score/baselibs"
    assert document["source"]["commit"] == "abc123"
    assert document["schema_version"] == 1
    assert document["nodes"][0]["id"] == "aou_req__one"
