# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Project Sphinx-Needs requirements into a local graph artefact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

REQUIREMENT_NEED_TYPES = frozenset(
    {"comp_req", "aou_req", "feat_req", "stkh_req", "comp", "testcase"}
)
_REQUIREMENT_TYPE_ORDER = (
    "aou_req",
    "comp",
    "comp_req",
    "feat_req",
    "stkh_req",
    "testcase",
)
_VERSION_SUFFIX = re.compile(r"\[version==[^]]+\]$")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_SAFE_NODE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MAX_NODES = 20000
_MAX_EDGES = 60000
_MAX_TITLE_CHARS = 200
_MAX_ATTRIBUTE_CHARS = 500


@dataclass(frozen=True)
class AdapterReport:
    nodes: int
    edges: int
    skipped_needs: int
    ignored_types: int
    skipped_links: int
    type_counts: dict[str, int]


@dataclass(frozen=True)
class RequirementNode:
    id: str
    type: str
    title: str
    attributes: dict[str, str]


@dataclass(frozen=True)
class RequirementEdge:
    source: str
    target: str
    relation: str


def strip_version(value: Any) -> str:
    """Remove a version suffix from a Sphinx-Needs identifier."""
    if not isinstance(value, str):
        raise ValueError("link identifier must be a string")
    return _VERSION_SUFFIX.sub("", value)


def is_safe_node_id(value: str) -> bool:
    """Return whether a projected node identifier is safe to use."""
    return _SAFE_NODE_ID.fullmatch(value) is not None


def _load_input(path: Path) -> tuple[Mapping[str, Any], str]:
    raw = path.read_bytes()
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("needs JSON top-level must be an object")
    document = cast(dict[str, Any], document)
    versions = document.get("versions")
    if not isinstance(versions, dict):
        raise ValueError("needs JSON field 'versions' must be an object")
    versions = cast(dict[str, Any], versions)
    if len(versions) != 1:
        raise ValueError("needs JSON field 'versions' must contain exactly one version")
    version = next(iter(versions.values()))
    if not isinstance(version, dict):
        raise ValueError("selected needs JSON version must be an object")
    version = cast(dict[str, Any], version)
    needs = version.get("needs")
    if not isinstance(needs, dict):
        raise ValueError("selected needs JSON version field 'needs' must be an object")
    needs = cast(dict[str, Any], needs)
    return document, hashlib.sha256(raw).hexdigest()


def _title(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        raise ValueError("need title must be a string")
    title = _CONTROL_CHARS.sub(" ", value)[:limit]
    if not title:
        raise ValueError("need title must not be empty")
    return title


def _attributes(need: Mapping[str, Any], limit: int) -> dict[str, str]:
    attributes: dict[str, str] = {}
    for name in ("status", "safety", "security", "reqtype", "docname"):
        value = need.get(name)
        if isinstance(value, str):
            attributes[name] = _CONTROL_CHARS.sub(" ", value)[:limit]

    if "version" in need and need["version"] is not None:
        attributes["version"] = _CONTROL_CHARS.sub(" ", str(need["version"]))[:limit]

    content = need.get("content")
    if isinstance(content, str):
        normalized = _CONTROL_CHARS.sub(" ", content)
        attributes["content"] = normalized[:limit]
        if len(normalized) > limit:
            attributes["content_truncated"] = "true"
    return attributes


_LINKS: dict[str, dict[str, tuple[str, frozenset[str]]]] = {
    "comp_req": {
        "derived_from": ("derived_from", frozenset({"feat_req"})),
        "satisfied_by": ("satisfied_by", frozenset({"comp"})),
        "covers": ("covers", frozenset({"aou_req"})),
    },
    "feat_req": {
        "derived_from": ("derived_from", frozenset({"stkh_req"})),
    },
    "testcase": {
        "partially_verifies": ("partially_verifies", frozenset({"comp_req"})),
        "fully_verifies": ("fully_verifies", frozenset({"comp_req"})),
    },
}


def build_requirements(
    needs_json_path: Path,
) -> tuple[
    tuple[RequirementNode, ...], tuple[RequirementEdge, ...], AdapterReport, str
]:
    """Build a deterministic requirements projection from needs JSON."""
    document, digest = _load_input(needs_json_path)
    versions = document["versions"]
    version = next(iter(versions.values()))
    needs = version["needs"]

    skipped_needs = 0
    ignored_types = 0
    node_data: dict[str, tuple[RequirementNode, str]] = {}
    need_data: dict[str, Mapping[str, Any]] = {}
    for key in sorted(needs):
        need = needs[key]
        if not isinstance(need, dict):
            skipped_needs += 1
            continue
        need = cast(dict[str, Any], need)
        raw_id = need.get("id")
        need_type = need.get("type")
        if not isinstance(raw_id, str) or not isinstance(need_type, str):
            skipped_needs += 1
            continue
        node_id = strip_version(raw_id)
        if need_type not in REQUIREMENT_NEED_TYPES:
            ignored_types += 1
            continue
        if not _SAFE_NODE_ID.fullmatch(node_id):
            skipped_needs += 1
            continue
        try:
            node = RequirementNode(
                node_id,
                need_type,
                _title(need.get("title"), _MAX_TITLE_CHARS),
                _attributes(need, _MAX_ATTRIBUTE_CHARS),
            )
        except ValueError:
            skipped_needs += 1
            continue
        if node_id in node_data:
            skipped_needs += 1
            continue
        node_data[node_id] = (node, need_type)
        need_data[node_id] = need
        if len(node_data) > _MAX_NODES:
            raise ValueError(
                f"requirements node count exceeds policy limit {_MAX_NODES}"
            )

    skipped_links = 0
    edges: list[RequirementEdge] = []
    edge_keys: set[tuple[str, str, str]] = set()
    for source_id in sorted(node_data):
        _, source_type = node_data[source_id]
        need = need_data[source_id]
        for field, (relation, target_types) in _LINKS.get(source_type, {}).items():
            values = need.get(field, [])
            if not isinstance(values, list):
                skipped_links += 1
                continue
            values = cast(list[Any], values)
            for value in values:
                if not isinstance(value, str):
                    skipped_links += 1
                    continue
                target_id = strip_version(value)
                target = node_data.get(target_id)
                if target is None or target[1] not in target_types:
                    skipped_links += 1
                    continue
                edge_key = (source_id, relation, target_id)
                if edge_key in edge_keys:
                    continue
                edge_keys.add(edge_key)
                edges.append(RequirementEdge(source_id, target_id, relation))
                if len(edges) > _MAX_EDGES:
                    raise ValueError(
                        f"requirements edge count exceeds policy limit {_MAX_EDGES}"
                    )

    nodes = tuple(
        node for node, _ in sorted(node_data.values(), key=lambda item: item[0].id)
    )
    edges_tuple = tuple(
        sorted(edges, key=lambda edge: (edge.source, edge.relation, edge.target))
    )
    type_counts = {
        need_type: sum(node.type == need_type for node in nodes)
        for need_type in _REQUIREMENT_TYPE_ORDER
    }
    return (
        nodes,
        edges_tuple,
        AdapterReport(
            nodes=len(nodes),
            edges=len(edges_tuple),
            skipped_needs=skipped_needs,
            ignored_types=ignored_types,
            skipped_links=skipped_links,
            type_counts=type_counts,
        ),
        digest,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--needs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--observed-at", default=datetime.now(UTC).isoformat())
    args = parser.parse_args(argv)
    try:
        nodes, edges, report, digest = build_requirements(args.needs)
        payload = {
            "schema_version": 1,
            "source": {
                "repo": args.repo,
                "commit": args.source_ref,
                "digest": f"sha256:{digest}",
                "generated_at": args.observed_at,
            },
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type,
                    "title": node.title,
                    "attributes": node.attributes,
                }
                for node in nodes
            ],
            "edges": [
                {
                    "source": edge.source,
                    "relation": edge.relation,
                    "target": edge.target,
                }
                for edge in edges
            ],
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    counts = " ".join(
        f"{need_type}={report.type_counts[need_type]}"
        for need_type in _REQUIREMENT_TYPE_ORDER
    )
    print(
        f"nodes={report.nodes} edges={report.edges} "
        f"skipped_needs={report.skipped_needs} "
        f"ignored_types={report.ignored_types} "
        f"skipped_links={report.skipped_links} {counts}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
