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

"""Read-time union of ordered context graph sources."""

from __future__ import annotations

import posixpath
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from context_overlay import Provenance
from context_sessions import ReasoningRecord, Record


def _empty_attributes() -> dict[str, str]:
    return {}


@dataclass(frozen=True)
class MergedNode:
    id: str
    label: str
    type: str
    layer: str
    source_file: str = ""
    provenance: Provenance | None = None
    source_file_keys: tuple[str, ...] = ()
    attributes: dict[str, str] = field(default_factory=_empty_attributes)


@dataclass(frozen=True)
class MergedEdge:
    source: str
    target: str
    relation: str
    layer: str
    provenance: Provenance | None = None


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


@dataclass
class MergedGraph:
    nodes: dict[str, MergedNode]
    edges: dict[tuple[str, str, str], MergedEdge]
    conflicts: tuple[str, ...] = ()
    edge_conflicts: tuple[tuple[str, str, str], ...] = ()
    source_file_index: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    label_index: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    label_casefold_index: dict[str, str] = field(
        default_factory=lambda: dict[str, str]()
    )
    label_tail_index: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    loaded_layers: frozenset[str] = frozenset()

    @classmethod
    def build(cls, repo_path: str | Path) -> MergedGraph:
        from context_policy import load_policy
        from context_sources import DEFAULT_SOURCES

        repo = Path(repo_path).expanduser().resolve()
        policy = load_policy(repo)
        return merge_sources(repo, policy, DEFAULT_SOURCES)

    def nodes_under(self, prefix: str) -> frozenset[str]:
        """Return node IDs whose source files are at or below a path prefix."""
        normalized = posixpath.normpath(prefix.replace("\\", "/")).removeprefix("./")
        subtree = f"{normalized.rstrip('/')}/"
        return frozenset(
            node_id
            for node_id, node in self.nodes.items()
            if node.source_file == normalized or node.source_file.startswith(subtree)
        )

    def neighbors(self, node_ids: set[str]) -> frozenset[str]:
        """Return the input node IDs and all nodes adjacent in either direction."""
        neighbors = set(node_ids)
        for edge in self.edges.values():
            if edge.source in node_ids:
                neighbors.add(edge.target)
            if edge.target in node_ids:
                neighbors.add(edge.source)
        return frozenset(neighbors)

    def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes

    @property
    def dangling_edges(self) -> tuple[MergedEdge, ...]:
        return tuple(
            edge
            for edge in self.edges.values()
            if edge.source not in self.nodes or edge.target not in self.nodes
        )


def label_tail(value: str) -> str:
    """Normalize a label tail by stripping ``()`` and template arguments."""
    segment = value.rsplit("::", 1)[-1].strip()
    if segment.endswith("()"):
        segment = segment[:-2].rstrip()
    while segment.endswith(">"):
        depth = 0
        start = -1
        for index in range(len(segment) - 1, -1, -1):
            character = segment[index]
            if character == ">":
                depth += 1
            elif character == "<":
                depth -= 1
                if depth == 0:
                    start = index
                    break
        if start < 0:
            break
        segment = segment[:start].rstrip()
    return segment.casefold()


def _unique_index(candidates: dict[str, set[str]]) -> dict[str, str]:
    return {
        key: next(iter(node_ids))
        for key, node_ids in candidates.items()
        if len(node_ids) == 1
    }


def merge_sources(
    repo: Path,
    policy: Any,
    sources: Iterable[Any],
) -> MergedGraph:
    nodes: dict[str, MergedNode] = {}
    edges: dict[tuple[str, str, str], MergedEdge] = {}
    source_file_candidates: dict[str, set[str]] = {}
    label_candidates: dict[str, set[str]] = {}
    label_casefold_candidates: dict[str, set[str]] = {}
    label_tail_candidates: dict[str, set[str]] = {}
    conflicts: set[str] = set()
    edge_conflicts: set[tuple[str, str, str]] = set()
    loaded_layers: set[str] = set()

    for source in sources:
        source_graph = source.load(repo, policy)
        if source_graph.loaded:
            loaded_layers.add(source.layer)

        for node in source_graph.nodes:
            if node.id in nodes:
                conflicts.add(node.id)
            else:
                nodes[node.id] = node
            label_candidates.setdefault(node.label, set()).add(node.id)
            label_casefold_candidates.setdefault(node.label.casefold(), set()).add(
                node.id
            )
            label_tail_candidates.setdefault(label_tail(node.label), set()).add(node.id)
            for source_file in node.source_file_keys:
                source_file_candidates.setdefault(source_file, set()).add(node.id)
        for edge in source_graph.edges:
            key = (edge.source, edge.target, edge.relation)
            if key in edges:
                edge_conflicts.add(key)
            else:
                edges[key] = edge

    return MergedGraph(
        nodes,
        edges,
        tuple(sorted(conflicts)),
        tuple(sorted(edge_conflicts)),
        {
            key: min(node_ids, key=lambda node_id: (len(node_id), node_id))
            for key, node_ids in source_file_candidates.items()
        },
        _unique_index(label_candidates),
        _unique_index(label_casefold_candidates),
        _unique_index(label_tail_candidates),
        frozenset(loaded_layers),
    )
