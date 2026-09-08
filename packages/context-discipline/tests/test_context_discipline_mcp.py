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

import json
from pathlib import Path

from context_discipline_mcp import (
    ContextDisciplineMCP,
    ReasoningRecord,
    SessionRecord,
    call_tool,
)


def _write_graph(tmp_path: Path) -> Path:
    graph_path = tmp_path / "graphify-out" / "graph.json"
    graph_path.parent.mkdir()
    graph_path.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "include_score_result_error_domain",
                        "label": "error_domain.h",
                        "source_file": "include/score/result/error_domain.h",
                    },
                    {
                        "id": "include_score_result_error_domain_errordomain",
                        "label": "ErrorDomain",
                        "source_file": "include/score/result/error_domain.h",
                    },
                    {
                        "id": "long_source_symbol",
                        "label": "source.py",
                        "source_file": "src/source.py",
                    },
                    {
                        "id": "a",
                        "label": "Source",
                        "source_file": "src/source.py",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return graph_path


def test_initialize_session_writes_one_session_record(tmp_path: Path) -> None:
    manager = ContextDisciplineMCP(str(tmp_path))
    result = manager.initialize_session("Goal", ["Subgoal"], agent="alice")
    session_id = result["session_id"]

    records = manager.session_log.read_all()
    raw_log = manager.session_log.path.read_text(encoding="utf-8")
    sessions = [record for record in records if isinstance(record, SessionRecord)]
    assert session_id == manager.session_id
    assert len(sessions) == 1
    assert sessions[0].goal == "Goal"
    assert "alice" not in raw_log
    assert manager.local_store.joinpath("agent-salt").stat().st_mode & 0o777 == 0o600


def test_initialize_session_resets_state_and_assigns_fresh_id(
    tmp_path: Path,
) -> None:
    manager = ContextDisciplineMCP(str(tmp_path))

    first = manager.initialize_session("First goal", [])
    manager.record_decision("First decision", ["first reason"])
    first_memory = manager.get_working_memory()

    second = manager.initialize_session("Second goal", [])

    assert second["session_id"] != first["session_id"]
    assert manager.session_id == second["session_id"]
    assert manager.goal_task_id is not None
    assert len(manager.get_working_memory()) < len(first_memory)
    assert manager.get_working_memory()[0]["content"] == "Second goal"


def test_prior_context_is_available_after_reinitializing_manager(
    tmp_path: Path,
) -> None:
    _write_graph(tmp_path)
    manager = ContextDisciplineMCP(str(tmp_path))
    manager.initialize_session("Inspect error domain", [])
    manager.record_decision(
        "The error domain is shared by result construction.",
        ["The file owns the domain mapping."],
        grounded_nodes=["include/score/result/error_domain.h"],
    )

    manager.initialize_session("Inspect error domain", [])
    result = manager.get_prior_context(
        "The error domain is shared by result construction.",
        ["include/score/result/error_domain.h"],
    )

    assert result["items"]
    assert result["items"][0]["grounded_nodes"] == (
        "include_score_result_error_domain",
    )
    assert result["items"][0]["score"] > 0.0


def test_record_decision_resolves_nodes_and_reports_unknown_values(
    tmp_path: Path,
) -> None:
    _write_graph(tmp_path)
    manager = ContextDisciplineMCP(str(tmp_path))
    manager.initialize_session("Inspect graph", [])

    result = manager.record_decision(
        "Use the error domain file.",
        ["It is the file-level graph node."],
        grounded_nodes=[
            "include/score/result/error_domain.h",
            "include_score_result_error_domain",
            "unknown/path.h",
        ],
    )

    assert result == {"unresolved_nodes": ["unknown/path.h"]}
    reasoning = [
        record
        for record in manager.session_log.read_all()
        if isinstance(record, ReasoningRecord)
    ][0]
    assert reasoning.grounded_nodes == [
        "include_score_result_error_domain",
        "include_score_result_error_domain",
        "unknown/path.h",
    ]


def test_record_decision_resolves_absolute_paths(tmp_path: Path) -> None:
    _write_graph(tmp_path)
    manager = ContextDisciplineMCP(str(tmp_path))
    manager.initialize_session("Inspect graph", [])

    result = manager.record_decision(
        "Use the error domain file.",
        ["It is the file-level graph node."],
        grounded_nodes=[str(tmp_path / "include/score/result/error_domain.h")],
    )

    assert result == {"unresolved_nodes": []}


def test_graph_source_file_index_picks_shortest_id(tmp_path: Path) -> None:
    _write_graph(tmp_path)

    from context_merge import MergedGraph

    graph = MergedGraph.build(tmp_path)

    assert (
        graph.source_file_index["include/score/result/error_domain.h"]
        == "include_score_result_error_domain"
    )
    assert graph.source_file_index["src/source.py"] == "a"


def test_initialize_session_reports_missing_graph_setup(tmp_path: Path) -> None:
    manager = ContextDisciplineMCP(str(tmp_path))

    result = manager.initialize_session("Goal", [])

    assert result["setup"] == {
        "ok": False,
        "graph_path": str(tmp_path / "graphify-out" / "graph.json"),
        "next": "Call setup_graphify with install_graphify=true.",
    }


def test_initialize_session_reports_existing_graph_setup(tmp_path: Path) -> None:
    graph_path = tmp_path / "graphify-out" / "graph.json"
    graph_path.parent.mkdir()
    graph_path.write_text("{}", encoding="utf-8")
    manager = ContextDisciplineMCP(str(tmp_path))

    result = manager.initialize_session("Goal", [])

    assert result["setup"] == {
        "ok": True,
        "graph_path": str(graph_path),
    }


def test_query_graph_reports_missing_graph_setup(tmp_path: Path) -> None:
    manager = ContextDisciplineMCP(str(tmp_path))

    result = manager.query_graph("Show me the repository")

    assert result == {
        "query": "Show me the repository",
        "matches": [],
        "setup": {
            "ok": False,
            "graph_path": str(tmp_path / "graphify-out" / "graph.json"),
            "next": "Call setup_graphify with install_graphify=true.",
        },
    }


def test_get_prior_context_returns_items_and_untrusted_rendered_block(
    tmp_path: Path,
) -> None:
    manager = ContextDisciplineMCP(str(tmp_path))
    manager.initialize_session("Goal", [])

    result = manager.get_prior_context("Goal", [])

    assert result == {"items": [], "rendered": ""}


def test_add_overlay_node_uses_repo_slug_and_wire_names(tmp_path: Path) -> None:
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text(
        json.dumps({"nodes": [{"id": "code__one", "label": "Code"}]}),
        encoding="utf-8",
    )
    manager = ContextDisciplineMCP(str(tmp_path))

    result = call_tool(
        manager,
        "add_overlay_node",
        {
            "id": "dec__one",
            "type": "dec_rec",
            "title": "Decision",
            "relation": "affects",
            "target": "code__one",
            "confidence": 0.9,
        },
    )

    assert result["node"]["id"] == "dec__one"
    assert result["node"]["provenance"]["repo"] == tmp_path.name
    assert result["edge"]["source"] == "dec__one"
