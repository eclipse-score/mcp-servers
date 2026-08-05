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

"""Deterministic graph-fragment loading and composition for Phase 1."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from score_context.schema.edges import Edge
from score_context.schema.nodes import Node


class GraphFragment(BaseModel):
    """The git-committed JSON shape emitted by future adapters."""

    model_config = ConfigDict(extra="forbid")

    fragment_version: str | None = Field(
        default=None, description="Schema version (v1)"
    )
    adapter: dict | None = Field(
        default=None, description="Adapter metadata {name, version, sha256}"
    )
    nodes: list[Node]
    edges: list[Edge]


class ContextGraph:
    """Small adjacency graph; a heavier graph library is deferred."""

    def __init__(self, nodes: dict[str, Node], edges: list[Edge]) -> None:
        self.nodes = nodes
        self.edges = edges
        self.outgoing: dict[str, list[Edge]] = {node_id: [] for node_id in nodes}
        self.incoming: dict[str, list[Edge]] = {node_id: [] for node_id in nodes}
        for edge in edges:
            self.outgoing.setdefault(edge.source, []).append(edge)
            self.incoming.setdefault(edge.target, []).append(edge)

    def neighbors(self, node_id: str) -> list[tuple[Node, Edge]]:
        """Return outgoing and incoming neighbors in stable edge order."""

        relationships: list[tuple[Node, Edge]] = []
        for edge in self.outgoing.get(node_id, []):
            if edge.target in self.nodes:
                relationships.append((self.nodes[edge.target], edge))
        for edge in self.incoming.get(node_id, []):
            if edge.source in self.nodes:
                relationships.append((self.nodes[edge.source], edge))
        return relationships


def load_fragment(path: Path) -> GraphFragment:
    """Load and validate one graph fragment using the Phase 0 models."""

    return GraphFragment.model_validate_json(path.read_text(encoding="utf-8"))


def compose_fragments(paths: list[Path]) -> ContextGraph:
    """Compose fragments, rejecting conflicting natural-key definitions."""

    nodes: dict[str, Node] = {}
    edges: list[Edge] = []
    for path in paths:
        fragment = load_fragment(path)
        for node in fragment.nodes:
            existing = nodes.get(node.id)
            if existing is not None and existing != node:
                raise ValueError(f"conflicting node definition: {node.id}")
            nodes[node.id] = node
        for edge in fragment.edges:
            if edge not in edges:
                edges.append(edge)
    return ContextGraph(nodes, edges)
