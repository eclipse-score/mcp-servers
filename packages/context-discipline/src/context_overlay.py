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

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, cast

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

_SAFE_NODE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SAFE_NODE_ID_MESSAGE = (
    "overlay node id must match "
    "[A-Za-z0-9][A-Za-z0-9._-]{0,127} (ASCII letters, digits, dot, underscore, hyphen)"
)


def _empty_attributes() -> dict[str, str]:
    return {}


def _edge_digest(source: str, relation: str, target: str) -> str:
    identity = f"{source}\0{relation}\0{target}".encode()
    return hashlib.sha256(identity).hexdigest()[:16]


def _has_control_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 0x7F for character in value)


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
        if type(self.id) is not str or not _SAFE_NODE_ID.fullmatch(self.id):
            raise ValueError(_SAFE_NODE_ID_MESSAGE)
        if type(self.type) is not str or self.type not in OVERLAY_NODE_TYPES:
            raise ValueError(f"unknown overlay node type: {self.type}")
        if type(self.title) is not str or not self.title:
            raise ValueError("overlay node title must not be empty")


@dataclass(frozen=True)
class OverlayEdge:
    source: str
    target: str
    relation: str
    provenance: Provenance
    attributes: dict[str, str] = field(default_factory=_empty_attributes)

    def __post_init__(self) -> None:
        if type(self.source) is not str or not self.source:
            raise ValueError("overlay edge source must not be empty")
        if type(self.target) is not str or not self.target:
            raise ValueError("overlay edge target must not be empty")
        if _has_control_character(self.source):
            raise ValueError("overlay edge source must not contain control characters")
        if _has_control_character(self.target):
            raise ValueError("overlay edge target must not contain control characters")
        if type(self.relation) is not str or self.relation not in OVERLAY_RELATIONS:
            raise ValueError(f"unknown overlay relation: {self.relation}")


class OverlayStore:
    """Read and write the durable repository-local context overlay."""

    def __init__(self, repo_path: str | Path, overlay_dir: str = "score-context"):
        self.repo_path = Path(repo_path).expanduser().resolve()
        self.root = self.repo_path / overlay_dir
        self.nodes_dir = self.root / "nodes"
        self.edges_dir = self.root / "edges"
        self.meta_path = self.root / "meta.json"
        self.legacy_path = self.root / "overlay.json"
        self._nodes: dict[str, OverlayNode] = {}
        self._edges: dict[tuple[str, str, str], OverlayEdge] = {}

    def _inside_root(self, path: Path) -> Path:
        root = self.root.resolve()
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"overlay path escapes root: {path}") from exc
        return resolved

    def _node_path(self, node_id: str) -> Path:
        return self._inside_root(self.nodes_dir / f"{node_id}.json")

    def _edge_path(self, edge: OverlayEdge) -> Path:
        return self._inside_root(
            self.edges_dir
            / f"{_edge_digest(edge.source, edge.relation, edge.target)}.json"
        )

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f"{path.name}.tmp")
        temporary.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            value: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"malformed overlay shard {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"malformed overlay shard {path}: expected an object")
        return cast(dict[str, Any], value)

    @staticmethod
    def _node_from_dict(data: dict[str, Any], path: Path) -> OverlayNode:
        try:
            attributes = cast(dict[str, str], data.get("attributes", {}))
            return OverlayNode(
                id=data["id"],
                type=data["type"],
                title=data["title"],
                provenance=Provenance(**data["provenance"]),
                attributes=dict(attributes),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"malformed overlay shard {path}: {exc}") from exc

    @staticmethod
    def _edge_from_dict(data: dict[str, Any], path: Path) -> OverlayEdge:
        try:
            attributes = cast(dict[str, str], data.get("attributes", {}))
            return OverlayEdge(
                source=data["source"],
                target=data["target"],
                relation=data["relation"],
                provenance=Provenance(**data["provenance"]),
                attributes=dict(attributes),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"malformed overlay shard {path}: {exc}") from exc

    def load(self) -> None:
        """Load legacy data first, then sharded data as authoritative overrides."""
        self._nodes.clear()
        self._edges.clear()
        if self.legacy_path.exists():
            data = self._read_json(self.legacy_path)
            version = data.get("version")
            if (
                isinstance(version, bool)
                or not isinstance(version, int)
                or version != SCORE_OVERLAY_VERSION
            ):
                raise ValueError(f"unknown overlay version: {data.get('version')!r}")
            for raw_node in data.get("nodes", []):
                self.upsert_node(self._node_from_dict(raw_node, self.legacy_path))
            for raw_edge in data.get("edges", []):
                self.upsert_edge(self._edge_from_dict(raw_edge, self.legacy_path))
        if not self.meta_path.exists():
            return
        meta = self._read_json(self.meta_path)
        version = meta.get("version")
        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or version != SCORE_OVERLAY_VERSION
        ):
            raise ValueError(f"unknown overlay version: {meta.get('version')!r}")
        if self.nodes_dir.exists():
            for path in sorted(self.nodes_dir.glob("*.json")):
                self._inside_root(path)
                self.upsert_node(self._node_from_dict(self._read_json(path), path))
        if self.edges_dir.exists():
            for path in sorted(self.edges_dir.glob("*.json")):
                self._inside_root(path)
                self.upsert_edge(self._edge_from_dict(self._read_json(path), path))

    def upsert_node(self, node: OverlayNode) -> None:
        self._nodes[node.id] = node

    def upsert_edge(self, edge: OverlayEdge) -> None:
        self._edges[(edge.source, edge.target, edge.relation)] = edge

    def save(self) -> None:
        """Atomically persist shards and remove legacy overlay after migration."""
        self._write_json(self.meta_path, {"version": SCORE_OVERLAY_VERSION})
        expected_nodes = {f"{node_id}.json" for node_id in self._nodes}
        for node in self._nodes.values():
            self._write_json(self._node_path(node.id), asdict(node))
        expected_edges = {
            f"{_edge_digest(edge.source, edge.relation, edge.target)}.json"
            for edge in self._edges.values()
        }
        for edge in self._edges.values():
            self._write_json(self._edge_path(edge), asdict(edge))
        for directory, expected in (
            (self.nodes_dir, expected_nodes),
            (self.edges_dir, expected_edges),
        ):
            if directory.exists():
                for path in directory.iterdir():
                    if (
                        path.is_file()
                        and path.suffix == ".json"
                        and path.name not in expected
                    ):
                        path.unlink()
        if self.legacy_path.exists():
            self.legacy_path.unlink()

    @property
    def nodes(self) -> tuple[OverlayNode, ...]:
        return tuple(self._nodes[node_id] for node_id in sorted(self._nodes))

    @property
    def edges(self) -> tuple[OverlayEdge, ...]:
        return tuple(self._edges[key] for key in sorted(self._edges))
