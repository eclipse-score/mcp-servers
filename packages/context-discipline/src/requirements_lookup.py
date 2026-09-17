# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Resolve requirement identifiers against a projected local graph."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from requirements_projection import is_safe_node_id, strip_version

REQUIREMENTS_GRAPH_ENV = "SCORE_REQUIREMENTS_GRAPH"
DEFAULT_REQUIREMENTS_GRAPH = ".score-local/requirements_graph.json"
MAX_REQUEST_IDS = 100

_UNAVAILABLE_NEXT = (
    "Generate the requirements graph: python -m requirements_projection "
    "--needs bazel-bin/needs.json --out .score-local/requirements_graph.json "
    "--repo <repo> --source-ref <commit>"
)


@dataclass(frozen=True)
class RequirementEntry:
    id: str
    type: str
    title: str
    attributes: dict[str, str]


@dataclass(frozen=True)
class RequirementsIndex:
    path: Path
    loaded: bool
    source: dict[str, str]
    nodes: dict[str, RequirementEntry]
    outgoing: dict[str, tuple[tuple[str, str], ...]]
    incoming: dict[str, tuple[tuple[str, str], ...]]

    @classmethod
    def load(cls, repo_path: Path, path_override: str = "") -> RequirementsIndex:
        repo = repo_path.expanduser().resolve()
        configured_path = path_override or os.environ.get(REQUIREMENTS_GRAPH_ENV, "")
        candidate = Path(configured_path or DEFAULT_REQUIREMENTS_GRAPH).expanduser()
        path = candidate if candidate.is_absolute() else repo / candidate
        path = path.resolve()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError, UnicodeError):
            return cls._empty(path)
        if not isinstance(payload, dict):
            return cls._empty(path)
        payload = cast(dict[str, object], payload)
        if payload.get("schema_version") != 1:
            return cls._empty(path)

        source_value = payload.get("source")
        nodes_value = payload.get("nodes")
        edges_value = payload.get("edges")
        if (
            not isinstance(source_value, dict)
            or not isinstance(nodes_value, list)
            or not isinstance(edges_value, list)
        ):
            return cls._empty(path)
        source = cast(dict[object, object], source_value)
        typed_source: dict[str, str] = {}
        for key, value in source.items():
            if isinstance(key, str) and isinstance(value, str):
                typed_source[key] = value

        nodes: dict[str, RequirementEntry] = {}
        typed_nodes = cast(list[object], nodes_value)
        for node_value in typed_nodes:
            if not isinstance(node_value, dict):
                continue
            node = cast(dict[str, object], node_value)
            raw_id = node.get("id")
            node_type = node.get("type")
            title = node.get("title")
            if (
                not isinstance(raw_id, str)
                or not isinstance(node_type, str)
                or not isinstance(title, str)
            ):
                continue
            try:
                node_id = strip_version(raw_id)
            except ValueError:
                continue
            if not node_id or not is_safe_node_id(node_id) or node_id in nodes:
                continue
            attributes_value = node.get("attributes", {})
            attributes: dict[str, str] = {}
            if isinstance(attributes_value, dict):
                attributes = {
                    key: value
                    for key, value in cast(
                        dict[object, object], attributes_value
                    ).items()
                    if isinstance(key, str) and isinstance(value, str)
                }
            nodes[node_id] = RequirementEntry(
                id=node_id,
                type=node_type,
                title=title,
                attributes=attributes,
            )

        outgoing_sets: dict[str, set[tuple[str, str]]] = {
            node_id: set() for node_id in nodes
        }
        incoming_sets: dict[str, set[tuple[str, str]]] = {
            node_id: set() for node_id in nodes
        }
        typed_edges = cast(list[object], edges_value)
        for edge_value in typed_edges:
            if not isinstance(edge_value, dict):
                continue
            edge = cast(dict[str, object], edge_value)
            raw_source = edge.get("source")
            raw_target = edge.get("target")
            relation = edge.get("relation")
            if (
                not isinstance(raw_source, str)
                or not isinstance(raw_target, str)
                or not isinstance(relation, str)
            ):
                continue
            try:
                source_id = strip_version(raw_source)
                target_id = strip_version(raw_target)
            except ValueError:
                continue
            if source_id not in nodes or target_id not in nodes:
                continue
            outgoing_sets[source_id].add((relation, target_id))
            incoming_sets[target_id].add((relation, source_id))

        outgoing = {
            node_id: tuple(sorted(links)) for node_id, links in outgoing_sets.items()
        }
        incoming = {
            node_id: tuple(sorted(links)) for node_id, links in incoming_sets.items()
        }
        return cls(
            path=path,
            loaded=True,
            source=typed_source,
            nodes=nodes,
            outgoing=outgoing,
            incoming=incoming,
        )

    @classmethod
    def _empty(cls, path: Path) -> RequirementsIndex:
        return cls(
            path=path,
            loaded=False,
            source={},
            nodes={},
            outgoing={},
            incoming={},
        )


def _request_pairs(
    requirement_ids: Sequence[str],
) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for requested in requirement_ids:
        try:
            normalized = strip_version(requested)
        except ValueError:
            normalized = ""
        if normalized in seen:
            continue
        seen.add(normalized)
        pairs.append((normalized, requested))
    return tuple(pairs)


def _result_requested(result: dict[str, Any], requested: str) -> None:
    if requested != result["id"]:
        result["requested"] = requested


def _link_entries(
    links: tuple[tuple[str, str], ...],
    nodes: dict[str, RequirementEntry],
    endpoint_key: str,
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for relation, endpoint in links:
        entry = nodes[endpoint]
        result.append(
            {
                "relation": relation,
                endpoint_key: endpoint,
                "type": entry.type,
                "title": entry.title,
            }
        )
    return result


def resolve_requirements(
    index: RequirementsIndex,
    requirement_ids: Sequence[str],
    include_links: bool = True,
) -> dict[str, Any]:
    """Resolve requirement IDs against one freshly loaded requirements index."""
    if len(requirement_ids) > MAX_REQUEST_IDS:
        raise ValueError(f"at most {MAX_REQUEST_IDS} requirement IDs may be requested")

    pairs = _request_pairs(requirement_ids)
    results: list[dict[str, Any]] = []
    unknown: list[str] = []
    for normalized, requested in pairs:
        result: dict[str, Any] = {"id": normalized}
        _result_requested(result, requested)
        if not index.loaded:
            result.update(
                known=False,
                reason="requirements_graph_unavailable",
            )
            unknown.append(normalized)
            results.append(result)
            continue
        if not normalized or not is_safe_node_id(normalized):
            result.update(known=False, reason="invalid_id")
            unknown.append(normalized)
            results.append(result)
            continue
        entry = index.nodes.get(normalized)
        if entry is None:
            result.update(known=False, reason="not_found")
            unknown.append(normalized)
            results.append(result)
            continue

        result.update(
            known=True,
            type=entry.type,
            title=entry.title,
            attributes=dict(entry.attributes),
        )
        if include_links:
            result["links"] = {
                "outgoing": _link_entries(
                    index.outgoing.get(normalized, ()),
                    index.nodes,
                    "target",
                ),
                "incoming": _link_entries(
                    index.incoming.get(normalized, ()),
                    index.nodes,
                    "source",
                ),
            }
        results.append(result)

    response: dict[str, Any] = {
        "loaded": index.loaded,
        "graph_path": str(index.path),
        "source": dict(index.source),
        "results": results,
        "unknown": unknown,
    }
    if not index.loaded:
        response["next"] = _UNAVAILABLE_NEXT
    return response
