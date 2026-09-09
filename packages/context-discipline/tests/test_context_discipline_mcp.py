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
    AttentionRecord,
    ContextDisciplineMCP,
    OutcomeRecord,
    ReasoningRecord,
    SessionRecord,
    call_tool,
    expand_focus,
)
from context_merge import MergedGraph
from context_policy import Policy


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
                        "id": "include_score_other_error_domain",
                        "label": "ErrorDomain",
                        "source_file": "include/score/other/error_domain.h",
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
    assert result["selection"] == "rank"
    assert result["items"][0]["grounded_nodes"] == (
        "include_score_result_error_domain",
    )
    assert result["items"][0]["score"] > 0.0
    assert (
        "The error domain is shared by result construction."
        in result["items"][0]["text"]
    )
    assert "The error domain is shared by result construction." in result["rendered"]


def test_prior_context_resolves_legacy_grounded_nodes(
    tmp_path: Path,
) -> None:
    _write_graph(tmp_path)
    manager = ContextDisciplineMCP(str(tmp_path))
    manager.initialize_session("Inspect error domain", [])
    manager.session_log.append(
        ReasoningRecord(
            id="reasoning__legacy",
            session_id="session__legacy",
            text="The error domain is shared by result construction.",
            grounded_nodes=["include/score/result/error_domain.h"],
        )
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

    assert result == {
        "items": [],
        "rejected": [],
        "threshold": 0.037,
        "selection": "rank",
        "unresolved_nodes": [],
        "rendered": "",
    }


def test_get_prior_context_logs_attention_factors_and_unresolved_nodes(
    tmp_path: Path,
) -> None:
    _write_graph(tmp_path)
    manager = ContextDisciplineMCP(str(tmp_path))
    manager.initialize_session("Current task", [])
    manager.session_log.append(
        ReasoningRecord(
            id="reasoning__rejected",
            session_id="session__prior",
            text="different finding",
            grounded_nodes=["include_score_result_error_domain"],
        )
    )

    result = manager.get_prior_context("unrelated query", ["unknown/node.h"])

    assert result["items"] == []
    assert result["unresolved_nodes"] == ["unknown/node.h"]
    attention_records = [
        record
        for record in manager.session_log.read_all()
        if isinstance(record, AttentionRecord)
    ]
    assert len(attention_records) == 1
    attention = attention_records[0]
    assert attention.current_nodes == ["unknown/node.h"]
    assert attention.rejected[0]["score"] == 0.0
    assert attention.rejected[0]["structural"] == 0.0
    assert attention.rejected[0]["live_ratio"] == 1.0
    assert attention.selection == "rank"
    assert attention.threshold == 0.037
    assert attention.focus_size == 0
    assert attention.focus_expansion_counts == {"unknown/node.h": 0}
    assert attention.focus_hop_skipped is False
    assert result["selection"] == "rank"
    assert result["threshold"] == 0.037


def test_expand_focus_resolves_nodes_directories_and_skips_hop_at_cap(
    tmp_path: Path,
) -> None:
    _write_graph(tmp_path)
    graph = MergedGraph.build(tmp_path)

    focus, unresolved, counts = expand_focus(
        [
            "include_score_result_error_domain",
            "include/score/result",
            "ErrorDomain",
            "unknown/path",
        ],
        graph,
        tmp_path,
        Policy(),
    )

    assert "include_score_result_error_domain" in focus
    assert counts["include_score_result_error_domain"] == 1
    assert counts["include/score/result"] == 2
    assert unresolved == ["ErrorDomain", "unknown/path"]
    assert focus

    policy_path = tmp_path / "score-context" / "policy.toml"
    policy_path.parent.mkdir()
    policy_path.write_text(
        "version = 1\n[attention]\nmax_focus_nodes = 1\n",
        encoding="utf-8",
    )
    capped_manager = ContextDisciplineMCP(str(tmp_path))
    capped_manager.initialize_session("Current task", [])
    capped_manager.get_prior_context("matching", ["include/score/result"])
    attention = next(
        record
        for record in capped_manager.session_log.read_all()
        if isinstance(record, AttentionRecord)
    )
    assert attention.focus_hop_skipped is True


def test_structural_focus_orders_module_and_neighbor_records(tmp_path: Path) -> None:
    graph_path = tmp_path / "graphify-out" / "graph.json"
    graph_path.parent.mkdir()
    graph_path.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "os_a", "label": "os_a", "source_file": "score/os/a.cpp"},
                    {"id": "os_b", "label": "os_b", "source_file": "score/os/b.cpp"},
                    {
                        "id": "result_a",
                        "label": "result_a",
                        "source_file": "score/result/a.cpp",
                    },
                    {
                        "id": "result_b",
                        "label": "result_b",
                        "source_file": "score/result/b.cpp",
                    },
                    {
                        "id": "fs_a",
                        "label": "fs_a",
                        "source_file": "score/filesystem/a.cpp",
                    },
                    {
                        "id": "fs_b",
                        "label": "fs_b",
                        "source_file": "score/filesystem/b.cpp",
                    },
                    {
                        "id": "fs_c",
                        "label": "fs_c",
                        "source_file": "score/filesystem/c.cpp",
                    },
                    *[
                        {
                            "id": f"fs_{suffix}",
                            "label": f"fs_{suffix}",
                            "source_file": f"score/filesystem/{suffix}.cpp",
                        }
                        for suffix in "defgh"
                    ],
                    {
                        "id": "tooling",
                        "label": "tooling",
                        "source_file": "tools/coverage/check.py",
                    },
                ],
                "edges": [
                    {"source": "os_a", "target": "fs_a"},
                    {"source": "os_a", "target": "fs_b"},
                    {"source": "os_b", "target": "fs_c"},
                ],
            }
        ),
        encoding="utf-8",
    )
    manager = ContextDisciplineMCP(str(tmp_path))
    manager.initialize_session("Current task", [])
    records = [
        ReasoningRecord(
            id="reasoning__os",
            session_id="session__os",
            text="matching finding",
            grounded_nodes=["os_a", "os_b"],
            timestamp="2026-01-01T00:00:00+00:00",
        ),
        ReasoningRecord(
            id="reasoning__result",
            session_id="session__result",
            text="matching finding",
            grounded_nodes=["os_a", "result_a"],
            timestamp="2026-01-01T00:00:00+00:00",
        ),
        ReasoningRecord(
            id="reasoning__result_b",
            session_id="session__result_b",
            text="matching finding",
            grounded_nodes=["os_a", "result_b"],
            timestamp="2026-01-01T00:00:00+00:00",
        ),
        ReasoningRecord(
            id="reasoning__filesystem",
            session_id="session__filesystem",
            text="matching finding",
            grounded_nodes=[
                "fs_a",
                "fs_b",
                "fs_c",
                "fs_d",
                "fs_e",
                "fs_f",
                "fs_g",
                "fs_h",
            ],
            timestamp="2026-01-01T00:00:00+00:00",
        ),
        ReasoningRecord(
            id="reasoning__tooling",
            session_id="session__tooling",
            text="matching finding",
            grounded_nodes=["tooling"],
            timestamp="2026-01-01T00:00:00+00:00",
        ),
    ]
    for record in records:
        manager.session_log.append(record)

    result = manager.get_prior_context("matching finding", ["score/os"])
    ordered = [item["reasoning_id"] for item in (*result["items"], *result["rejected"])]
    factors = {
        item["reasoning_id"]: item["factors"]["structural"]
        for item in (*result["items"], *result["rejected"])
    }
    attention = next(
        record
        for record in manager.session_log.read_all()
        if isinstance(record, AttentionRecord)
    )

    assert ordered == [
        "reasoning__os",
        "reasoning__result",
        "reasoning__result_b",
        "reasoning__filesystem",
        "reasoning__tooling",
    ]
    assert factors == {
        "reasoning__os": 1.0,
        "reasoning__result": 0.5,
        "reasoning__result_b": 0.5,
        "reasoning__filesystem": 0.375,
        "reasoning__tooling": 0.0,
    }
    assert attention.focus_expansion_counts == {"score/os": 2}
    assert attention.focus_size >= 2
    assert attention.focus_hop_skipped is False


def test_record_outcome_requires_clean_verdict_and_stores_rationale(
    tmp_path: Path,
) -> None:
    manager = ContextDisciplineMCP(str(tmp_path))
    manager.initialize_session("Goal", [])

    for verdict in ("PASS: prose", "Pass", ""):
        try:
            manager.record_outcome("Goal", verdict, 1.0, [], [])
        except ValueError:
            pass
        else:
            raise AssertionError(f"{verdict!r} should be rejected")
    try:
        manager.record_outcome("Goal", 1, 1.0, [], [])  # type: ignore[arg-type]
    except ValueError:
        pass
    else:
        raise AssertionError("non-string verdict should be rejected")

    manager.record_outcome(
        "Goal",
        "pass",
        1.0,
        [],
        [],
        rationale="RATIONALE MARKER\x00",
    )
    outcome = next(
        record
        for record in manager.session_log.read_all()
        if isinstance(record, OutcomeRecord)
    )
    assert outcome.verdict == "pass"
    assert outcome.rationale == "RATIONALE MARKER"

    result = manager.get_prior_context("unrelated", [])
    assert "RATIONALE MARKER" not in json.dumps(result)


def test_outcome_record_round_trips_with_and_without_rationale(
    tmp_path: Path,
) -> None:
    manager = ContextDisciplineMCP(str(tmp_path))
    manager.session_log.append(
        OutcomeRecord(
            id="outcome__new",
            verdict="pass",
            rationale="documented",
        )
    )
    manager.session_log.path.write_text(
        manager.session_log.path.read_text(encoding="utf-8")
        + json.dumps(
            {
                "id": "outcome__legacy",
                "record_type": "outcome",
                "session_id": "",
                "task_id": "",
                "verdict": "fail",
                "coverage": 0.2,
                "timestamp": "2026-01-01T00:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    outcomes = [
        record
        for record in manager.session_log.read_all()
        if isinstance(record, OutcomeRecord)
    ]
    assert [(record.id, record.rationale) for record in outcomes] == [
        ("outcome__new", "documented"),
        ("outcome__legacy", ""),
    ]


def test_record_decision_resolves_labels_and_rejects_ambiguous_labels(
    tmp_path: Path,
) -> None:
    graph_path = tmp_path / "graphify-out" / "graph.json"
    graph_path.parent.mkdir()
    graph_path.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "error_domain", "label": "ErrorDomain"},
                    {"id": "make_error", "label": "MakeError"},
                    {"id": "duplicate_one", "label": "Duplicate"},
                    {"id": "duplicate_two", "label": "Duplicate"},
                ]
            }
        ),
        encoding="utf-8",
    )
    manager = ContextDisciplineMCP(str(tmp_path))
    manager.initialize_session("Goal", [])
    result = manager.record_decision(
        "Use graph labels.",
        [],
        grounded_nodes=["ErrorDomain", "errordomain", "score::detail::MakeError()"],
    )
    assert result == {"unresolved_nodes": []}
    reasoning = next(
        record
        for record in manager.session_log.read_all()
        if isinstance(record, ReasoningRecord)
    )
    assert reasoning.grounded_nodes == ["error_domain", "make_error"]

    unresolved = manager.record_decision(
        "Reject ambiguity.",
        [],
        grounded_nodes=["Duplicate", "unknown"],
    )
    assert unresolved == {"unresolved_nodes": ["Duplicate", "unknown"]}


def test_rejected_prior_context_omits_foreign_reasoning_text(
    tmp_path: Path,
) -> None:
    _write_graph(tmp_path)
    manager = ContextDisciplineMCP(str(tmp_path))
    manager.initialize_session("Current task", [])
    manager.session_log.append(
        ReasoningRecord(
            id="reasoning__hostile",
            session_id="session__prior",
            text="FOREIGN REASONING MUST NOT ESCAPE",
            grounded_nodes=["include_score_result_error_domain"],
        )
    )

    result = manager.get_prior_context("unrelated query", [])

    assert result["items"] == []
    assert "FOREIGN REASONING MUST NOT ESCAPE" not in json.dumps(result)


def test_attention_record_round_trips_with_and_without_selection(
    tmp_path: Path,
) -> None:
    manager = ContextDisciplineMCP(str(tmp_path))
    manager.session_log.append(
        AttentionRecord(
            id="attention__rank",
            threshold=0.2,
            selection="rank",
        )
    )
    manager.session_log.path.write_text(
        manager.session_log.path.read_text(encoding="utf-8")
        + json.dumps(
            {
                "id": "attention__legacy",
                "record_type": "attention",
                "session_id": "",
                "task_id": "",
                "query": "",
                "current_nodes": [],
                "surfaced": [],
                "rejected": [],
                "threshold": 0.15,
                "timestamp": "2026-01-01T00:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    records = [
        record
        for record in manager.session_log.read_all()
        if isinstance(record, AttentionRecord)
    ]

    assert [(record.id, record.selection, record.threshold) for record in records] == [
        ("attention__rank", "rank", 0.2),
        ("attention__legacy", "", 0.15),
    ]


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
