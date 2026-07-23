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

"""First-cut deterministic attention selection over a context graph."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast

from pydantic import BaseModel, ConfigDict, Field

from score_context.graph import ContextGraph
from score_context.schema.edges import EdgeRelation
from score_context.schema.nodes import Node, NodeType

RELATION_WEIGHTS: dict[EdgeRelation, float] = {
    EdgeRelation.AFFECTS: 3.0,
    EdgeRelation.BLOCKS: 3.0,
    EdgeRelation.DISCUSSED_IN: 2.5,
    EdgeRelation.IMPLEMENTS: 2.0,
    EdgeRelation.DEPENDS_ON: 2.0,
}


class ContextSelection(BaseModel):
    """Structured and renderable result of one deterministic query."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    repo: str
    role: str
    selected: list[Node]
    decisions: list[Node]
    contracts: list[Node]
    repositories: list[Node]
    blocking_tasks: list[Node]
    rendered: str = Field(min_length=1)


class ContextEngine:
    """MCP-free context engine bound to one composed graph."""

    def __init__(self, graph: ContextGraph) -> None:
        self.graph = graph

    def get_context(
        self,
        task: Mapping[str, object],
        repo: str,
        role: str,
        top_n: int,
    ) -> ContextSelection:
        """Return structured and rendered context for one task."""

        return get_context(self.graph, task, repo, role, top_n)


def _freshness(node: Node, latest: datetime) -> float:
    age_days = max(0.0, (latest - node.provenance.observed_at).total_seconds() / 86400)
    return 1.0 / (1.0 + age_days / 365.0)


def get_context(
    graph: ContextGraph,
    task_spec: Mapping[str, object],
    repo: str,
    role: str,
    top_n: int,
) -> ContextSelection:
    """Select stable top-N context using seeds, relation weights, and freshness.

    This deliberately simple scorer is a Phase 1 placeholder for personalized
    PageRank. The seam and output shape are stable; ranking math is not.
    """

    task_id = str(task_spec["id"])
    raw_seeds = task_spec.get("seed_node_ids", [])
    if not isinstance(raw_seeds, list):
        raise ValueError("task_spec.seed_node_ids must be a list of strings")
    seeds = cast(list[str], raw_seeds)
    if top_n < 1:
        raise ValueError("top_n must be positive")
    if not seeds:
        raise ValueError("task_spec has no known seed nodes")
    latest = max(node.provenance.observed_at for node in graph.nodes.values())
    scores: dict[str, float] = {seed: 100.0 for seed in seeds}
    for seed in seeds:
        for neighbor, edge in graph.neighbors(seed):
            relation_score = RELATION_WEIGHTS.get(edge.relation, 1.0)
            degree_score = len(graph.neighbors(neighbor.id)) * 0.1
            scores[neighbor.id] = max(
                scores.get(neighbor.id, 0.0),
                relation_score + degree_score + _freshness(neighbor, latest),
            )
    ranked_ids = sorted(
        scores,
        key=lambda node_id: (-scores[node_id], node_id),
    )[:top_n]
    selected = [graph.nodes[node_id] for node_id in ranked_ids]
    decisions = [node for node in selected if node.type == NodeType.DEC_REC]
    contracts = [node for node in selected if node.type == NodeType.CONTRACT]
    repositories = [node for node in selected if node.type == NodeType.REPO]
    blocking_tasks = [
        node
        for node in selected
        if node.type in {NodeType.ISSUE, NodeType.PULL_REQUEST}
        and any(
            edge.relation == EdgeRelation.BLOCKS for edge in graph.outgoing[node.id]
        )
    ]
    rendered_lines = [
        f"Context selection for {task_id} ({repo}, {role})",
        "Selected nodes:",
    ]
    rendered_lines.extend(
        f"- {node.id} [{node.type.value}] {node.title}" for node in selected
    )
    rendered = "\n".join(rendered_lines)
    return ContextSelection(
        task_id=task_id,
        repo=repo,
        role=role,
        selected=selected,
        decisions=decisions,
        contracts=contracts,
        repositories=repositories,
        blocking_tasks=blocking_tasks,
        rendered=rendered,
    )
