# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Project process-description needs into the durable context overlay."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_CONTEXT_SRC = Path(__file__).resolve().parents[2] / "context-discipline" / "src"
if str(_CONTEXT_SRC) not in sys.path:
    sys.path.insert(0, str(_CONTEXT_SRC))

from context_overlay import (  # noqa: E402, I001
    OverlayEdge,
    OverlayNode,
    OverlayStore,
    Provenance,
)


PROCESS_NEED_TYPES = frozenset(
    {
        "workflow",
        "role",
        "workproduct",
        "gd_req",
        "gd_temp",
        "gd_guidl",
        "gd_chklst",
        "std_req",
        "std_wp",
    }
)

_VERSION_SUFFIX = re.compile(r"\[version==[^]]+\]$")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_DEFAULT_POLICY_LIMITS = (20000, 60000, 200, 500)


@dataclass(frozen=True)
class AdapterReport:
    nodes: int
    edges: int
    skipped_needs: int
    ignored_types: int
    skipped_links: int


def strip_version(value: str) -> str:
    """Remove the process-description version suffix from an identifier."""
    if not isinstance(value, str):
        raise ValueError("link identifier must be a string")
    return _VERSION_SUFFIX.sub("", value)


def _load_input(path: Path) -> tuple[Mapping[str, Any], str]:
    raw = path.read_bytes()
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("top-level process description must be an object")
    versions = document.get("versions")
    if not isinstance(versions, dict):
        raise ValueError("process description field 'versions' must be an object")
    if len(versions) != 1:
        raise ValueError(
            "process description field 'versions' must contain exactly one version"
        )
    version = next(iter(versions.values()))
    if not isinstance(version, dict):
        raise ValueError("selected process description version must be an object")
    needs = version.get("needs")
    if not isinstance(needs, dict):
        raise ValueError(
            "selected process description version field 'needs' must be an object"
        )
    return document, hashlib.sha256(raw).hexdigest()


def _policy_limits(repo: str) -> tuple[tuple[int, int, int, int], bool]:
    try:
        from context_policy import load_policy
    except (ImportError, ModuleNotFoundError):
        return _DEFAULT_POLICY_LIMITS, True
    overlay = load_policy(repo).overlay
    return (
        (
            overlay.max_nodes,
            overlay.max_edges,
            overlay.max_title_chars,
            overlay.max_attribute_chars,
        ),
        False,
    )


def _title(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        raise ValueError("need title must be a string")
    return _CONTROL_CHARS.sub(" ", value)[:limit]


def _attributes(need: Mapping[str, Any], limit: int) -> dict[str, str]:
    attributes: dict[str, str] = {}
    status = need.get("status")
    if isinstance(status, str):
        attributes["status"] = status[:limit]
    tags = need.get("tags")
    if isinstance(tags, list):
        attributes["tags"] = ",".join(tag for tag in tags if isinstance(tag, str))[
            :limit
        ]
    return attributes


_LINKS: dict[str, dict[str, tuple[str, frozenset[str]]]] = {
    "workflow": {
        "responsible": ("responsible", frozenset({"role"})),
        "approved_by": ("approved_by", frozenset({"role"})),
        "supported_by": ("supported_by", frozenset({"role"})),
        "input": ("input", frozenset({"workproduct"})),
        "output": ("output", frozenset({"workproduct"})),
        "contains": (
            "contains",
            frozenset({"gd_req", "gd_temp", "gd_guidl", "gd_chklst"}),
        ),
    },
    "gd_req": {
        "satisfies": ("satisfies", frozenset({"workflow"})),
        "complies": ("complies", frozenset({"std_req", "std_wp"})),
    },
    "workproduct": {
        "complies": ("complies", frozenset({"std_req", "std_wp"})),
    },
    "gd_temp": {
        "complies": ("complies", frozenset({"std_req", "std_wp"})),
    },
    "gd_guidl": {
        "complies": ("complies", frozenset({"std_req", "std_wp"})),
    },
    "gd_chklst": {
        "complies": ("complies", frozenset({"std_req", "std_wp"})),
    },
    "role": {
        "contains": ("contains", frozenset({"role"})),
    },
}


def build_overlay(
    needs_json_path: Path,
    *,
    repo: str,
    observed_at: str,
    policy_repo: str | None = None,
) -> tuple[tuple[OverlayNode, ...], tuple[OverlayEdge, ...], AdapterReport]:
    """Build a deterministic overlay projection from a needs JSON file."""
    document, digest = _load_input(needs_json_path)
    versions = document["versions"]
    version = next(iter(versions.values()))
    needs = version["needs"]
    (max_nodes, max_edges, title_limit, attribute_limit), _ = _policy_limits(
        policy_repo or repo
    )

    skipped_needs = 0
    ignored_types = 0
    node_data: dict[str, tuple[OverlayNode, str]] = {}
    need_data: dict[str, Mapping[str, Any]] = {}
    for key in sorted(needs):
        need = needs[key]
        if not isinstance(need, dict):
            skipped_needs += 1
            continue
        raw_id = need.get("id")
        need_type = need.get("type")
        if not isinstance(raw_id, str) or not isinstance(need_type, str):
            skipped_needs += 1
            continue
        node_id = strip_version(raw_id)
        if need_type not in PROCESS_NEED_TYPES:
            ignored_types += 1
            continue
        try:
            node = OverlayNode(
                node_id,
                need_type,
                _title(need.get("title"), title_limit),
                Provenance(
                    repo=repo,
                    adapter="process_description",
                    confidence=1.0,
                    observed_at=observed_at,
                    sha=digest,
                ),
                _attributes(need, attribute_limit),
            )
        except ValueError:
            skipped_needs += 1
            continue
        if node_id in node_data:
            skipped_needs += 1
            continue
        node_data[node_id] = (node, need_type)
        need_data[node_id] = need
        if len(node_data) > max_nodes:
            raise ValueError(f"overlay node count exceeds policy limit {max_nodes}")

    provenance = Provenance(
        repo=repo,
        adapter="process_description",
        confidence=1.0,
        observed_at=observed_at,
        sha=digest,
    )
    skipped_links = 0
    edges: list[OverlayEdge] = []
    for source_id in sorted(node_data):
        _, source_type = node_data[source_id]
        need = need_data[source_id]
        for field, (relation, target_types) in _LINKS.get(source_type, {}).items():
            values = need.get(field, [])
            if not isinstance(values, list):
                skipped_links += 1
                continue
            for value in values:
                if not isinstance(value, str):
                    skipped_links += 1
                    continue
                target_id = strip_version(value)
                target = node_data.get(target_id)
                if target is None or target[1] not in target_types:
                    skipped_links += 1
                    continue
                edges.append(OverlayEdge(source_id, target_id, relation, provenance))
                if len(edges) > max_edges:
                    raise ValueError(
                        f"overlay edge count exceeds policy limit {max_edges}"
                    )

    nodes = tuple(
        node for node, _ in sorted(node_data.values(), key=lambda item: item[0].id)
    )
    edges_tuple = tuple(
        sorted(edges, key=lambda edge: (edge.source, edge.relation, edge.target))
    )
    return (
        nodes,
        edges_tuple,
        AdapterReport(
            nodes=len(nodes),
            edges=len(edges_tuple),
            skipped_needs=skipped_needs,
            ignored_types=ignored_types,
            skipped_links=skipped_links,
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--needs", type=Path, required=True)
    parser.add_argument("--repo-path", type=Path, required=True)
    parser.add_argument("--source-repo", default="eclipse-score/process_description")
    parser.add_argument("--observed-at", default=datetime.now(UTC).isoformat())
    args = parser.parse_args(argv)
    try:
        _, used_policy_fallback = _policy_limits(str(args.repo_path))
        nodes, edges, report = build_overlay(
            args.needs,
            repo=args.source_repo,
            observed_at=args.observed_at,
            policy_repo=str(args.repo_path),
        )
        store = OverlayStore(args.repo_path)
        store.load()
        for node in nodes:
            store.upsert_node(node)
        for edge in edges:
            store.upsert_edge(edge)
        store.save()
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(
        f"nodes={report.nodes} edges={report.edges} "
        f"skipped_needs={report.skipped_needs} "
        f"ignored_types={report.ignored_types} "
        f"skipped_links={report.skipped_links}"
    )
    if used_policy_fallback:
        print("policy_limits=module defaults (context_policy unavailable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
