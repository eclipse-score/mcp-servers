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

"""Read-time union of code, durable domain, and collaboration context."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from context_overlay import OverlayStore
from context_sessions import (
    ReasoningRecord,
    Record,
    RetrievalRecord,
    SessionLog,
    SessionRecord,
    TaskRecord,
)


@dataclass(frozen=True)
class MergedNode:
    id: str
    label: str
    type: str
    layer: str


@dataclass(frozen=True)
class MergedEdge:
    source: str
    target: str
    relation: str
    layer: str


def link_reasoning(records: Iterable[Record]) -> tuple[tuple[str, str], ...]:
    reasoning = [record for record in records if isinstance(record, ReasoningRecord)]
    pairs: list[tuple[str, str]] = []
    for r2 in reasoning:
        for r1 in reasoning:
            if r1.id == r2.id or r1.session_id == r2.session_id:
                continue
            if r1.timestamp < r2.timestamp and set(r1.grounded_nodes) & set(
                r2.grounded_nodes
            ):
                pairs.append((r2.id, r1.id))
    return tuple(sorted(set(pairs)))


def _session_edges(records: tuple[Record, ...]) -> tuple[MergedEdge, ...]:
    edges: list[MergedEdge] = []
    sessions = [record for record in records if isinstance(record, SessionRecord)]
    tasks = [record for record in records if isinstance(record, TaskRecord)]
    reasonings = [record for record in records if isinstance(record, ReasoningRecord)]
    retrievals = [record for record in records if isinstance(record, RetrievalRecord)]
    for session in sessions:
        for task in tasks:
            if task.session_id == session.id:
                edges.append(
                    MergedEdge(session.id, task.id, "contains", "collaboration")
                )
    for task in tasks:
        if task.parent_id:
            edges.append(
                MergedEdge(task.parent_id, task.id, "contains", "collaboration")
            )
    for reasoning in reasonings:
        if reasoning.task_id:
            edges.append(
                MergedEdge(
                    reasoning.id, reasoning.task_id, "belongs_to", "collaboration"
                )
            )
        edges.extend(
            MergedEdge(reasoning.id, node_id, "supported_by", "collaboration")
            for node_id in reasoning.grounded_nodes
        )
    edges.extend(
        MergedEdge(r2, r1, "derived_from", "collaboration")
        for r2, r1 in link_reasoning(records)
    )
    for retrieval in retrievals:
        edges.extend(
            MergedEdge(retrieval.id, node_id, "covers", "collaboration")
            for node_id in retrieval.returned_nodes
        )
    return tuple(edges)


@dataclass
class MergedGraph:
    nodes: dict[str, MergedNode]
    edges: dict[tuple[str, str, str], MergedEdge]
    conflicts: tuple[str, ...] = ()
    edge_conflicts: tuple[tuple[str, str, str], ...] = ()

    @classmethod
    def build(cls, repo_path: str | Path) -> MergedGraph:
        repo = Path(repo_path).expanduser().resolve()
        nodes: dict[str, MergedNode] = {}
        edges: dict[tuple[str, str, str], MergedEdge] = {}
        conflicts: set[str] = set()
        edge_conflicts: set[tuple[str, str, str]] = set()

        graph_path = repo / "graphify-out" / "graph.json"
        if graph_path.exists():
            data = json.loads(graph_path.read_text(encoding="utf-8"))
            for raw in data.get("nodes", []):
                node = MergedNode(
                    id=str(raw["id"]),
                    label=str(raw.get("label", raw["id"])),
                    type=str(raw.get("type") or raw.get("file_type", "")),
                    layer="code",
                )
                if node.id in nodes:
                    conflicts.add(node.id)
                else:
                    nodes[node.id] = node
            raw_edges = data.get("links", data.get("edges", []))
            for raw in raw_edges:
                edge = MergedEdge(
                    source=str(raw["source"]),
                    target=str(raw["target"]),
                    relation=str(raw.get("relation", "")),
                    layer="code",
                )
                key = (edge.source, edge.target, edge.relation)
                if key in edges:
                    edge_conflicts.add(key)
                else:
                    edges[key] = edge

        overlay = OverlayStore(repo)
        overlay.load()
        for raw in overlay.nodes:
            node = MergedNode(raw.id, raw.title, raw.type, "domain")
            if node.id in nodes:
                conflicts.add(node.id)
            else:
                nodes[node.id] = node
        for raw in overlay.edges:
            edge = MergedEdge(raw.source, raw.target, raw.relation, "domain")
            key = (edge.source, edge.target, edge.relation)
            if key in edges:
                edge_conflicts.add(key)
            else:
                edges[key] = edge

        log = SessionLog(repo)
        records = log.read_all()
        for record in records:
            if isinstance(record, SessionRecord):
                label = record.goal
                record_type = "session"
            elif isinstance(record, TaskRecord):
                label = record.text
                record_type = "task"
            elif isinstance(record, ReasoningRecord):
                label = record.text
                record_type = "reasoning"
            elif isinstance(record, RetrievalRecord):
                label = record.query
                record_type = "retrieval"
            else:
                label = record.verdict
                record_type = "outcome"
            node = MergedNode(record.id, label, record_type, "collaboration")
            if node.id in nodes:
                conflicts.add(node.id)
            else:
                nodes[node.id] = node
        for edge in _session_edges(records):
            key = (edge.source, edge.target, edge.relation)
            if key in edges:
                edge_conflicts.add(key)
            else:
                edges[key] = edge
        return cls(
            nodes,
            edges,
            tuple(sorted(conflicts)),
            tuple(sorted(edge_conflicts)),
        )

    def neighbors(self, node_id: str) -> tuple[MergedNode, ...]:
        neighbor_ids = {
            edge.target for edge in self.edges.values() if edge.source == node_id
        } | {edge.source for edge in self.edges.values() if edge.target == node_id}
        return tuple(
            self.nodes[neighbor_id]
            for neighbor_id in sorted(neighbor_ids)
            if neighbor_id in self.nodes
        )

    def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes

    @property
    def dangling_edges(self) -> tuple[MergedEdge, ...]:
        return tuple(
            edge
            for edge in self.edges.values()
            if edge.source not in self.nodes or edge.target not in self.nodes
        )
