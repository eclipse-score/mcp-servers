# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from requirements_lookup import MAX_REQUEST_IDS, RequirementsIndex, resolve_requirements


def _payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "source": {
            "repo": "eclipse-score/example",
            "commit": "abc123",
            "digest": "sha256:digest",
            "generated_at": "2026-01-01T00:00:00+00:00",
        },
        "nodes": [
            {
                "id": "comp_req__x",
                "type": "comp_req",
                "title": "Requirement X",
                "attributes": {"status": "valid", "version": "1"},
            },
            {
                "id": "comp__a",
                "type": "comp",
                "title": "Component A",
                "attributes": {},
            },
            {
                "id": "comp__z",
                "type": "comp",
                "title": "Component Z",
                "attributes": {},
            },
            {
                "id": "testcase__a",
                "type": "testcase",
                "title": "Test A",
                "attributes": {},
            },
            {
                "id": "testcase__z",
                "type": "testcase",
                "title": "Test Z",
                "attributes": {},
            },
        ],
        "edges": [
            {"source": "comp_req__x", "relation": "zeta", "target": "comp__z"},
            {"source": "comp_req__x", "relation": "alpha", "target": "comp__a"},
            {"source": "comp_req__x", "relation": "zeta", "target": "comp__z"},
            {"source": "testcase__z", "relation": "zeta", "target": "comp_req__x"},
            {"source": "testcase__a", "relation": "alpha", "target": "comp_req__x"},
            {"source": "missing", "relation": "ignored", "target": "comp_req__x"},
            {"source": "comp_req__x", "relation": "ignored", "target": "missing"},
            {"source": "comp_req__x", "relation": 7, "target": "comp__a"},
            "malformed",
        ],
    }


def _write_graph(path: Path, payload: object | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_payload() if payload is None else payload),
        encoding="utf-8",
    )


def test_missing_graph_is_unavailable_and_explains_next_step(
    tmp_path: Path,
) -> None:
    index = RequirementsIndex.load(tmp_path)

    result = resolve_requirements(index, ["comp_req__x"])

    assert result["loaded"] is False
    assert result["source"] == {}
    assert result["results"] == [
        {
            "id": "comp_req__x",
            "known": False,
            "reason": "requirements_graph_unavailable",
        }
    ]
    assert result["unknown"] == ["comp_req__x"]
    assert "next" in result


@pytest.mark.parametrize(
    "payload",
    [
        "{not json",
        json.dumps({"schema_version": 2}),
        json.dumps([]),
        json.dumps({"schema_version": 1, "source": {}, "nodes": {}, "edges": []}),
        json.dumps({"schema_version": 1, "source": {}, "nodes": [], "edges": {}}),
    ],
)
def test_invalid_graph_documents_fail_open(tmp_path: Path, payload: str) -> None:
    path = tmp_path / "requirements.json"
    path.write_text(payload, encoding="utf-8")

    index = RequirementsIndex.load(tmp_path, str(path))
    result = resolve_requirements(index, ["comp_req__x"])

    assert index.loaded is False
    assert index.nodes == {}
    assert result["results"][0]["reason"] == "requirements_graph_unavailable"


def test_malformed_nodes_and_edges_are_skipped(tmp_path: Path) -> None:
    payload = _payload()
    nodes = cast(list[object], payload["nodes"])
    payload["nodes"] = [
        *nodes,
        {"id": "missing_type", "title": "No type"},
        {"id": "../unsafe", "type": "comp", "title": "Unsafe"},
        {"id": "comp__a", "type": "comp", "title": "Duplicate"},
        {"id": "empty_attrs", "type": "comp", "title": "Empty", "attributes": 3},
    ]
    path = tmp_path / "requirements.json"
    _write_graph(path, payload)

    index = RequirementsIndex.load(tmp_path, str(path))

    assert index.loaded is True
    assert set(index.nodes) == {
        "comp_req__x",
        "comp__a",
        "comp__z",
        "testcase__a",
        "testcase__z",
        "empty_attrs",
    }
    assert index.nodes["empty_attrs"].attributes == {}
    assert index.outgoing["comp_req__x"] == (
        ("alpha", "comp__a"),
        ("zeta", "comp__z"),
    )
    assert index.incoming["comp_req__x"] == (
        ("alpha", "testcase__a"),
        ("zeta", "testcase__z"),
    )


def test_known_id_returns_sorted_typed_links(tmp_path: Path) -> None:
    path = tmp_path / "requirements.json"
    _write_graph(path)

    result = resolve_requirements(
        RequirementsIndex.load(tmp_path, str(path)),
        ["comp_req__x"],
    )

    assert result["source"]["commit"] == "abc123"
    assert result["results"] == [
        {
            "id": "comp_req__x",
            "known": True,
            "type": "comp_req",
            "title": "Requirement X",
            "attributes": {"status": "valid", "version": "1"},
            "links": {
                "outgoing": [
                    {
                        "relation": "alpha",
                        "target": "comp__a",
                        "type": "comp",
                        "title": "Component A",
                    },
                    {
                        "relation": "zeta",
                        "target": "comp__z",
                        "type": "comp",
                        "title": "Component Z",
                    },
                ],
                "incoming": [
                    {
                        "relation": "alpha",
                        "source": "testcase__a",
                        "type": "testcase",
                        "title": "Test A",
                    },
                    {
                        "relation": "zeta",
                        "source": "testcase__z",
                        "type": "testcase",
                        "title": "Test Z",
                    },
                ],
            },
        }
    ]


def test_version_pins_and_duplicates_keep_first_request(tmp_path: Path) -> None:
    path = tmp_path / "requirements.json"
    _write_graph(path)

    result = resolve_requirements(
        RequirementsIndex.load(tmp_path, str(path)),
        ["comp_req__x[version==3]", "comp_req__x", "unknown__id"],
    )

    assert [entry["id"] for entry in result["results"]] == [
        "comp_req__x",
        "unknown__id",
    ]
    assert result["results"][0]["requested"] == "comp_req__x[version==3]"
    assert result["results"][1] == {
        "id": "unknown__id",
        "known": False,
        "reason": "not_found",
    }
    assert result["unknown"] == ["unknown__id"]


def test_invalid_ids_are_reported_without_raising(tmp_path: Path) -> None:
    path = tmp_path / "requirements.json"
    _write_graph(path)

    result = resolve_requirements(
        RequirementsIndex.load(tmp_path, str(path)),
        ["../etc/passwd", ""],
    )

    assert [entry["reason"] for entry in result["results"]] == [
        "invalid_id",
        "invalid_id",
    ]
    assert result["unknown"] == ["../etc/passwd", ""]


def test_links_can_be_omitted_and_empty_requests_are_normal(
    tmp_path: Path,
) -> None:
    path = tmp_path / "requirements.json"
    _write_graph(path)
    index = RequirementsIndex.load(tmp_path, str(path))

    without_links = resolve_requirements(index, ["comp_req__x"], False)
    empty = resolve_requirements(index, [])

    assert "links" not in without_links["results"][0]
    assert empty["results"] == []
    assert empty["unknown"] == []


def test_request_limit_is_enforced(tmp_path: Path) -> None:
    path = tmp_path / "requirements.json"
    _write_graph(path)

    with pytest.raises(ValueError, match=str(MAX_REQUEST_IDS)):
        resolve_requirements(
            RequirementsIndex.load(tmp_path, str(path)),
            ["comp_req__x"] * (MAX_REQUEST_IDS + 1),
        )


def test_environment_override_and_relative_path_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative_path = tmp_path / "relative" / "requirements.json"
    absolute_path = tmp_path / "absolute" / "requirements.json"
    _write_graph(relative_path)
    _write_graph(absolute_path)
    monkeypatch.setenv("SCORE_REQUIREMENTS_GRAPH", "relative/requirements.json")

    from_environment = RequirementsIndex.load(tmp_path)
    from_argument = RequirementsIndex.load(tmp_path, str(absolute_path))

    assert from_environment.path == relative_path.resolve()
    assert from_argument.path == absolute_path.resolve()
    assert from_environment.loaded is True
    assert from_argument.loaded is True
