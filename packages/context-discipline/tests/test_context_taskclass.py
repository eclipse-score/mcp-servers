# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

from pathlib import Path

import pytest
from context_discipline_mcp import ContextDisciplineMCP
from context_merge import MergedEdge, MergedGraph, MergedNode
from context_policy import Policy
from context_sessions import TaskClassRecord, TaskRecord
from context_taskclass import build_workflow_index, detect_task_class, process_facts

PROCESS_GRAPH = (
    Path(__file__).parents[2] / "metamodel-flow" / "model" / "process_graph.json"
)


def _real_graph(monkeypatch: pytest.MonkeyPatch) -> MergedGraph:
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(PROCESS_GRAPH))
    return MergedGraph.build(Path.cwd())


def test_real_process_workflow_measurement_and_probes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = _real_graph(monkeypatch)
    index = build_workflow_index(graph)
    assert len(index.workflows) == 79
    signatures = index.signatures()
    assert len(set(signatures.values())) == 76
    assert {
        frozenset(
            {
                "wf__problem_analyze_pr",
                "wf__problem_create_pr",
                "wf__problem_initiate_monitor_pr",
            }
        ),
        frozenset({"wf__change_close_cr", "wf__change_implement_monitor_cr"}),
    } == {
        frozenset(
            workflow_id
            for workflow_id in signatures
            if signatures[workflow_id] == signature
        )
        for signature in set(signatures.values())
        if sum(value == signature for value in signatures.values()) > 1
    }

    probes = (
        (
            "Build unit tests for the mw/log error domain",
            "confident",
            "wf__verification_unit_test",
        ),
        (
            "Add a unit test for score::os::Fcntl",
            "confident",
            "wf__verification_unit_test",
        ),
        (
            "Write the module release note for the 0.7 release",
            None,
            "wf__rel_mod_rel_note",
        ),
        ("Fix bug 1234 in lib score/result", "unknown", "wf__analyse_comparch"),
        ("Refactor the CMake build files", "unknown", "wf__analyse_comparch"),
        (
            "Perform a code review on pull request 42",
            "ambiguous",
            "wf__change_analyze_cr",
        ),
        (
            "Review the component architecture of score/mw/log",
            "ambiguous",
            "wf__analyse_comparch",
        ),
    )
    for text, status, top_id in probes:
        detection = detect_task_class(text, graph, Policy())
        assert detection.candidates[0].id == top_id
        if status is not None:
            assert detection.status == status
        if status in {"unknown", "ambiguous"}:
            assert detection.task_class == ""


def test_same_signature_tie_selects_lexicographically_smallest_workflow() -> None:
    nodes = {
        node.id: node
        for node in (
            MergedNode("wf__b", "Review Beta", "workflow", "process"),
            MergedNode("wf__a", "Review Alpha", "workflow", "process"),
            MergedNode("wf__c", "Unique", "workflow", "process"),
            MergedNode("rl__reviewer", "Reviewer", "role", "process"),
        )
    }
    edges = {
        (workflow_id, "rl__reviewer", "responsible"): MergedEdge(
            workflow_id, "rl__reviewer", "responsible", "process"
        )
        for workflow_id in ("wf__a", "wf__b")
    }
    graph = MergedGraph(nodes, edges)

    detection = detect_task_class("Review", graph, Policy())

    assert detection.status == "confident"
    assert detection.task_class == "wf__a"


def test_process_facts_do_not_expand_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = _real_graph(monkeypatch)

    facts = process_facts(graph, "wf__verification_unit_test")

    assert facts["responsible"] == ["rl__contributor"]
    assert facts["approved_by"] == ["rl__committer"]
    assert "rl__committer" not in facts["satisfied_by"]


def test_initialize_detection_and_set_task_class(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(PROCESS_GRAPH))
    manager = ContextDisciplineMCP(str(tmp_path))
    result = manager.initialize_session(
        "Build unit tests for the mw/log error domain",
        ["Run them"],
    )

    assert result["detection"]["status"] == "confident"
    assert result["detection"]["announcement"].startswith("Repository ")
    assert "question" not in result["detection"]
    tasks = [
        record
        for record in manager.session_log.read_all()
        if isinstance(record, TaskRecord)
    ]
    assert tasks[0].task_class == "wf__verification_unit_test"
    assert tasks[1].task_class == "wf__verification_unit_test"

    rejected = manager.set_task_class("wf__does_not_exist")
    assert "error" in rejected
    accepted = manager.set_task_class("none")
    assert accepted["task_class"] == ""
    records = [
        record
        for record in manager.session_log.read_all()
        if isinstance(record, TaskClassRecord)
    ]
    assert records[-1].source == "user"


def test_missing_process_layer_omits_detection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(tmp_path / "missing.json"))
    manager = ContextDisciplineMCP(str(tmp_path))

    result = manager.initialize_session("Goal", [])

    assert "detection" not in result


def test_ambiguous_and_unknown_detections_ask_before_continuing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SCORE_PROCESS_GRAPH", str(PROCESS_GRAPH))
    manager = ContextDisciplineMCP(str(tmp_path))

    ambiguous = manager.initialize_session(
        "Perform a code review on pull request 42",
        [],
    )
    assert ambiguous["detection"]["status"] == "ambiguous"
    assert ambiguous["detection"]["announcement"].endswith("task class ambiguous")
    assert {
        option["id"] for option in ambiguous["detection"]["question"]["options"]
    }.__contains__("none")

    unknown = manager.initialize_session("Fix bug 1234 in lib score/result", [])
    assert unknown["detection"]["status"] == "unknown"
    assert {
        option["id"] for option in unknown["detection"]["question"]["options"]
    }.__contains__("none")
    assert unknown["task_class"] == ""
