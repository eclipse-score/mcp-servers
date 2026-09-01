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

from context_merge import MergedGraph, link_reasoning
from context_overlay import OverlayNode, OverlayStore, Provenance
from context_sessions import (
    ReasoningRecord,
    RetrievalRecord,
    SessionLog,
    SessionRecord,
    TaskRecord,
)


def test_three_layer_merge_and_dangling_edges(tmp_path: Path) -> None:
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "code__one", "label": "Code one", "file_type": "code"},
                    {"id": "collision", "label": "Code", "file_type": "code"},
                ],
                "links": [
                    {
                        "source": "code__one",
                        "target": "missing",
                        "relation": "contains",
                    },
                    {
                        "source": "code__one",
                        "target": "missing",
                        "relation": "contains",
                    },
                    {"source": "code__one", "target": "code__one"},
                ],
            }
        ),
        encoding="utf-8",
    )
    overlay = OverlayStore(tmp_path)
    overlay.upsert_node(
        OverlayNode(
            "domain__one",
            "dec_rec",
            "Decision",
            Provenance("repo", "test", 1.0, "2026-01-01T00:00:00Z"),
        )
    )
    overlay.upsert_node(
        OverlayNode(
            "collision",
            "contract",
            "Domain collision",
            Provenance("repo", "test", 1.0, "2026-01-01T00:00:00Z"),
        )
    )
    overlay.save()

    log = SessionLog(tmp_path)
    session = SessionRecord(
        id="session__one",
        agent="agent",
        goal="Goal",
        timestamp="2026-01-01T00:00:00Z",
    )
    task = TaskRecord(
        id="task__one",
        session_id=session.id,
        text="Task",
        timestamp="2026-01-01T00:00:01Z",
    )
    reasoning = ReasoningRecord(
        id="reasoning__one",
        session_id=session.id,
        task_id=task.id,
        text="Reasoning",
        grounded_nodes=["domain__one", "missing"],
        timestamp="2026-01-01T00:00:02Z",
    )
    retrieval = RetrievalRecord(
        id="retrieval__one",
        session_id=session.id,
        task_id=task.id,
        query="query",
        returned_nodes=["code__one"],
    )
    for record in (session, task, reasoning, retrieval):
        log.append(record)

    merged = MergedGraph.build(tmp_path)
    assert merged.nodes["code__one"].layer == "code"
    assert merged.nodes["domain__one"].layer == "domain"
    assert merged.nodes[reasoning.id].layer == "collaboration"
    assert merged.nodes["collision"].label == "Code"
    assert "collision" in merged.conflicts
    assert merged.edge_conflicts == (("code__one", "missing", "contains"),)
    assert merged.edges[(session.id, task.id, "contains")].relation == "contains"
    assert merged.edges[(reasoning.id, task.id, "belongs_to")].relation == "belongs_to"
    assert merged.edges[(reasoning.id, "domain__one", "supported_by")]
    assert merged.edges[(retrieval.id, "code__one", "covers")]
    assert any(edge.target == "missing" for edge in merged.dangling_edges)


def test_link_reasoning_pairs_prior_cross_session_records() -> None:
    records = [
        ReasoningRecord(
            id="reasoning__later",
            session_id="session__two",
            task_id="task__two",
            text="Later",
            grounded_nodes=["node__one"],
            timestamp="2026-01-02T00:00:00Z",
        ),
        ReasoningRecord(
            id="reasoning__earlier",
            session_id="session__one",
            task_id="task__one",
            text="Earlier",
            grounded_nodes=["node__one", "node__two"],
            timestamp="2026-01-01T00:00:00Z",
        ),
    ]
    assert link_reasoning(records) == (("reasoning__later", "reasoning__earlier"),)
