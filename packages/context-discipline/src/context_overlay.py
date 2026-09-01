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

"""Durable S-CORE domain nodes and edges stored beside the code graph."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import cast

SCORE_OVERLAY_VERSION = 1

OVERLAY_NODE_TYPES = frozenset(
    {
        "dec_rec",
        "stkh_req",
        "feat_req",
        "comp_req",
        "aou_req",
        "contract",
        "testcase",
        "workproduct",
        "issue",
        "pull_request",
    }
)

OVERLAY_RELATIONS = frozenset(
    {
        "affects",
        "depends_on",
        "discussed_in",
        "blocks",
        "supersedes",
        "conflicts_with",
        "implements",
        "satisfies",
        "satisfied_by",
        "derived_from",
        "covers",
        "contains",
        "belongs_to",
        "supported_by",
        "fully_verifies",
        "partially_verifies",
    }
)


def _empty_attributes() -> dict[str, str]:
    return {}


@dataclass(frozen=True)
class Provenance:
    repo: str
    adapter: str
    confidence: float
    observed_at: str
    sha: str | None = None

    def __post_init__(self) -> None:
        if not self.repo:
            raise ValueError("provenance repo must not be empty")
        if not self.adapter:
            raise ValueError("provenance adapter must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("provenance confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class OverlayNode:
    id: str
    type: str
    title: str
    provenance: Provenance
    attributes: dict[str, str] = field(default_factory=_empty_attributes)

    def __post_init__(self) -> None:
        if self.type not in OVERLAY_NODE_TYPES:
            raise ValueError(f"unknown overlay node type: {self.type}")
        if not self.id:
            raise ValueError("overlay node id must not be empty")
        if not self.title:
            raise ValueError("overlay node title must not be empty")


@dataclass(frozen=True)
class OverlayEdge:
    source: str
    target: str
    relation: str
    provenance: Provenance
    attributes: dict[str, str] = field(default_factory=_empty_attributes)

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("overlay edge source must not be empty")
        if not self.target:
            raise ValueError("overlay edge target must not be empty")
        if self.relation not in OVERLAY_RELATIONS:
            raise ValueError(f"unknown overlay relation: {self.relation}")


class OverlayStore:
    """Read and write the durable repository-local context overlay."""

    def __init__(self, repo_path: str | Path, overlay_dir: str = "score-context"):
        self.repo_path = Path(repo_path).expanduser().resolve()
        self.path = self.repo_path / overlay_dir / "overlay.json"
        self._nodes: dict[str, OverlayNode] = {}
        self._edges: dict[tuple[str, str, str], OverlayEdge] = {}

    def load(self) -> None:
        """Load the overlay, treating a missing file as an empty overlay."""
        self._nodes.clear()
        self._edges.clear()
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("version") != SCORE_OVERLAY_VERSION:
            raise ValueError(f"unknown overlay version: {data.get('version')!r}")
        for raw_node in data.get("nodes", []):
            attributes = cast(dict[str, str], raw_node.get("attributes", {}))
            node = OverlayNode(
                id=raw_node["id"],
                type=raw_node["type"],
                title=raw_node["title"],
                provenance=Provenance(**raw_node["provenance"]),
                attributes=dict(attributes),
            )
            self.upsert_node(node)
        for raw_edge in data.get("edges", []):
            attributes = cast(dict[str, str], raw_edge.get("attributes", {}))
            edge = OverlayEdge(
                source=raw_edge["source"],
                target=raw_edge["target"],
                relation=raw_edge["relation"],
                provenance=Provenance(**raw_edge["provenance"]),
                attributes=dict(attributes),
            )
            self.upsert_edge(edge)

    def upsert_node(self, node: OverlayNode) -> None:
        self._nodes[node.id] = node

    def upsert_edge(self, edge: OverlayEdge) -> None:
        self._edges[(edge.source, edge.target, edge.relation)] = edge

    def save(self) -> None:
        """Persist a deterministic, reviewable overlay document."""
        data = {
            "version": SCORE_OVERLAY_VERSION,
            "nodes": [asdict(self._nodes[node_id]) for node_id in sorted(self._nodes)],
            "edges": [asdict(self._edges[key]) for key in sorted(self._edges)],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @property
    def nodes(self) -> tuple[OverlayNode, ...]:
        return tuple(self._nodes[node_id] for node_id in sorted(self._nodes))

    @property
    def edges(self) -> tuple[OverlayEdge, ...]:
        return tuple(self._edges[key] for key in sorted(self._edges))
