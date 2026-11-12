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

"""Deterministic task-class detection from the process workflow graph."""

from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt

from context_attention import tokenize
from context_merge import MergedGraph, MergedNode
from context_policy import Policy

PROCESS_FACT_RELATIONS = (
    "responsible",
    "approved_by",
    "supported_by",
    "input",
    "output",
    "contains",
)


@dataclass(frozen=True)
class WorkflowCandidate:
    id: str
    title: str
    score: float


@dataclass(frozen=True)
class Detection:
    status: str
    task_class: str
    title: str
    gap: float
    candidates: tuple[WorkflowCandidate, ...]


class WorkflowIndex:
    def __init__(self, graph: MergedGraph) -> None:
        workflows = tuple(
            node
            for node in graph.nodes.values()
            if node.layer == "process" and node.type == "workflow"
        )
        self.workflows = tuple(sorted(workflows, key=lambda node: node.id))
        self.tokens = {
            workflow.id: tokenize(workflow.label) for workflow in self.workflows
        }
        document_frequency: dict[str, int] = {}
        for workflow_tokens in self.tokens.values():
            for token in workflow_tokens:
                document_frequency[token] = document_frequency.get(token, 0) + 1
        count = len(self.workflows)
        self.idf = (
            {
                token: log(count / frequency)
                for token, frequency in document_frequency.items()
            }
            if count
            else {}
        )
        self.graph = graph

    def score(self, task: str, workflow: MergedNode) -> float:
        workflow_tokens = self.tokens[workflow.id]
        if not workflow_tokens:
            return 0.0
        overlap = tokenize(task) & workflow_tokens
        if not overlap:
            return 0.0
        return sum(self.idf[token] for token in overlap) / sqrt(len(workflow_tokens))

    def candidates(self, task: str) -> tuple[WorkflowCandidate, ...]:
        ranked = sorted(
            (
                WorkflowCandidate(
                    workflow.id,
                    workflow.label,
                    self.score(task, workflow),
                )
                for workflow in self.workflows
            ),
            key=lambda candidate: (-candidate.score, candidate.id),
        )
        return tuple(ranked)

    def signatures(self) -> dict[str, frozenset[tuple[str, str]]]:
        return {
            workflow.id: frozenset(
                (edge.relation, edge.target)
                for edge in self.graph.edges.values()
                if edge.layer == "process" and edge.source == workflow.id
            )
            for workflow in self.workflows
        }


def build_workflow_index(graph: MergedGraph) -> WorkflowIndex:
    return WorkflowIndex(graph)


def detect_task_class(
    task: str,
    graph: MergedGraph,
    policy: Policy,
) -> Detection:
    index = build_workflow_index(graph)
    ranked = index.candidates(task)
    top = ranked[:3]
    if not ranked or ranked[0].score == 0.0:
        return Detection(
            status="unknown",
            task_class="",
            title=ranked[0].title if ranked else "",
            gap=0.0,
            candidates=top,
        )

    best = ranked[0]
    second = ranked[1].score if len(ranked) > 1 else 0.0
    gap = (best.score - second) / best.score
    if len(ranked) == 1 or gap >= policy.process.gap_min:
        return Detection(
            status="confident",
            task_class=best.id,
            title=best.title,
            gap=gap,
            candidates=top,
        )

    tie_floor = best.score * (1.0 - policy.process.gap_min)
    tied = [candidate for candidate in ranked if candidate.score >= tie_floor]
    signatures = index.signatures()
    tied_signatures = {signatures[candidate.id] for candidate in tied}
    if len(tied_signatures) == 1:
        selected = min(tied, key=lambda candidate: candidate.id)
        return Detection(
            status="confident",
            task_class=selected.id,
            title=selected.title,
            gap=gap,
            candidates=top,
        )
    return Detection(
        status="ambiguous",
        task_class="",
        title=best.title,
        gap=gap,
        candidates=top,
    )


def process_facts(graph: MergedGraph, workflow_id: str) -> dict[str, list[str]]:
    facts: dict[str, list[str]] = {relation: [] for relation in PROCESS_FACT_RELATIONS}
    facts["satisfied_by"] = []
    for edge in graph.edges.values():
        if edge.layer != "process":
            continue
        if edge.source == workflow_id and edge.relation in PROCESS_FACT_RELATIONS:
            facts[edge.relation].append(edge.target)
        elif edge.target == workflow_id and edge.relation == "satisfies":
            facts["satisfied_by"].append(edge.source)
    return {key: sorted(values) for key, values in facts.items()}
