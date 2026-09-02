#!/usr/bin/env python3
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

"""Validate the committed context overlay and its change-size budget."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parents[1] / "packages/context-discipline/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from context_overlay import (  # noqa: E402
    SCORE_OVERLAY_VERSION,
    OverlayEdge,
    OverlayNode,
    Provenance,
    _edge_digest,
)
from context_policy import Policy, load_policy  # noqa: E402

SECRET_PATTERNS = (
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github-token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    (
        "private-key-header",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ),
    ("secret-key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    (
        "secret-assignment",
        re.compile(
            r"\b(password|passwd|secret|api[_-]?key|token)\b\s*[:=]\s*\S{8,}",
            re.IGNORECASE,
        ),
    ),
    (
        "email-address",
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    ),
)


def _display_path(repo: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def _node_from_data(data: dict[str, Any]) -> OverlayNode:
    attributes = data.get("attributes", {})
    if not isinstance(attributes, dict):
        raise ValueError("attributes must be an object")
    if not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in attributes.items()
    ):
        raise ValueError("attribute keys and values must be strings")
    return OverlayNode(
        id=data["id"],
        type=data["type"],
        title=data["title"],
        provenance=Provenance(**data["provenance"]),
        attributes=dict(attributes),
    )


def _edge_from_data(data: dict[str, Any]) -> OverlayEdge:
    attributes = data.get("attributes", {})
    if not isinstance(attributes, dict):
        raise ValueError("attributes must be an object")
    if not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in attributes.items()
    ):
        raise ValueError("attribute keys and values must be strings")
    return OverlayEdge(
        source=data["source"],
        target=data["target"],
        relation=data["relation"],
        provenance=Provenance(**data["provenance"]),
        attributes=dict(attributes),
    )


def _inside_root(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _scan_text(
    text: str, path: Path, repo: Path, failures: list[tuple[str, str]]
) -> None:
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            failures.append(
                (
                    _display_path(repo, path),
                    f"secret or PII pattern {name!r} matched",
                )
            )


def _load_graph_ids(repo: Path) -> set[str]:
    graph_path = repo / "graphify-out" / "graph.json"
    if not graph_path.exists():
        return set()
    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        return {
            str(node["id"])
            for node in data.get("nodes", [])
            if isinstance(node, dict) and "id" in node
        }
    except (AttributeError, OSError, json.JSONDecodeError, TypeError):
        return set()


def _policy(repo: Path, failures: list[tuple[str, str]]) -> Policy:
    try:
        return load_policy(repo)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        failures.append(("score-context/policy.toml", f"invalid policy: {exc}"))
        return Policy()


def _validate_delta(
    repo: Path,
    base: str,
    policy: Policy,
    failures: list[tuple[str, str]],
    warnings: list[tuple[str, str]],
) -> None:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", f"{base}...HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )
    except OSError as exc:
        warnings.append(("git", f"could not inspect overlay delta: {exc}"))
        return
    if result.returncode != 0:
        warnings.append(("git", "could not inspect overlay delta; check skipped"))
        return
    added_nodes = 0
    added_edges = 0
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) < 2 or fields[0] != "A":
            continue
        changed = fields[1]
        if changed.startswith("score-context/nodes/") and changed.endswith(".json"):
            added_nodes += 1
        elif changed.startswith("score-context/edges/") and changed.endswith(".json"):
            added_edges += 1
    if added_nodes > policy.overlay.max_added_nodes_per_change:
        failures.append(
            (
                "git diff",
                f"added node shards {added_nodes} exceed "
                "max_added_nodes_per_change "
                f"{policy.overlay.max_added_nodes_per_change}",
            )
        )
    if added_edges > policy.overlay.max_added_edges_per_change:
        failures.append(
            (
                "git diff",
                f"added edge shards {added_edges} exceed "
                "max_added_edges_per_change "
                f"{policy.overlay.max_added_edges_per_change}",
            )
        )


def validate(
    repo: Path, base: str | None = None
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], bool]:
    failures: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []
    root = repo / "score-context"
    nodes_dir = root / "nodes"
    edges_dir = root / "edges"
    node_paths = sorted(nodes_dir.glob("*.json")) if nodes_dir.exists() else []
    edge_paths = sorted(edges_dir.glob("*.json")) if edges_dir.exists() else []
    has_data = (
        (root / "meta.json").exists()
        or (root / "overlay.json").exists()
        or bool(node_paths)
        or bool(edge_paths)
    )
    if not has_data:
        return failures, warnings, False

    policy = _policy(repo, failures)
    meta_path = root / "meta.json"
    if not meta_path.exists() and not (root / "overlay.json").exists():
        failures.append(("score-context/meta.json", "missing overlay metadata"))
    elif meta_path.exists():
        display = _display_path(repo, meta_path)
        try:
            metadata = _read_object(meta_path)
            version = metadata.get("version")
            if (
                isinstance(version, bool)
                or not isinstance(version, int)
                or version != SCORE_OVERLAY_VERSION
            ):
                failures.append((display, f"unknown overlay version: {version!r}"))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            failures.append((display, str(exc)))
    nodes: dict[str, OverlayNode] = {}
    edges: list[tuple[Path, OverlayEdge]] = []
    for path in node_paths:
        display = _display_path(repo, path)
        if not _inside_root(root, path):
            failures.append((display, "shard path escapes overlay root"))
            continue
        try:
            node = _node_from_data(_read_object(path))
        except (
            KeyError,
            TypeError,
            UnicodeError,
            ValueError,
            json.JSONDecodeError,
            OSError,
        ) as exc:
            failures.append((display, str(exc)))
            continue
        if path.name != f"{node.id}.json":
            failures.append((display, f"filename does not match node id {node.id!r}"))
        nodes[node.id] = node
        if len(node.title) > policy.overlay.max_title_chars:
            failures.append((display, "title exceeds max_title_chars"))
        if len(node.attributes) > policy.overlay.max_attributes:
            failures.append((display, "attribute count exceeds max_attributes"))
        for key, value in node.attributes.items():
            if len(key) + len(value) > policy.overlay.max_attribute_chars:
                failures.append(
                    (display, "attribute key/value exceeds max_attribute_chars")
                )
            _scan_text(key, path, repo, failures)
            _scan_text(value, path, repo, failures)
        _scan_text(node.title, path, repo, failures)
    for path in edge_paths:
        display = _display_path(repo, path)
        if not _inside_root(root, path):
            failures.append((display, "shard path escapes overlay root"))
            continue
        try:
            edge = _edge_from_data(_read_object(path))
        except (
            KeyError,
            TypeError,
            UnicodeError,
            ValueError,
            json.JSONDecodeError,
            OSError,
        ) as exc:
            failures.append((display, str(exc)))
            continue
        expected = f"{_edge_digest(edge.source, edge.relation, edge.target)}.json"
        if path.name != expected:
            failures.append((display, "filename does not match edge digest"))
        edges.append((path, edge))
        if len(edge.attributes) > policy.overlay.max_attributes:
            failures.append((display, "attribute count exceeds max_attributes"))
        for key, value in edge.attributes.items():
            if len(key) + len(value) > policy.overlay.max_attribute_chars:
                failures.append(
                    (display, "attribute key/value exceeds max_attribute_chars")
                )
            _scan_text(key, path, repo, failures)
            _scan_text(value, path, repo, failures)
    if len(nodes) > policy.overlay.max_nodes:
        failures.append(("score-context/nodes", "node count exceeds max_nodes"))
    if len(edges) > policy.overlay.max_edges:
        failures.append(("score-context/edges", "edge count exceeds max_edges"))
    graph_ids = _load_graph_ids(repo)
    known_ids = set(nodes) | graph_ids
    for path, edge in edges:
        missing = sorted(
            endpoint
            for endpoint in (edge.source, edge.target)
            if endpoint not in known_ids
        )
        if missing:
            warnings.append(
                (
                    _display_path(repo, path),
                    f"dangling endpoint(s): {', '.join(missing)}",
                )
            )
    if base is not None:
        _validate_delta(repo, base, policy, failures, warnings)
    return failures, warnings, True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--base")
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    failures, warnings, has_data = validate(repo, args.base)
    if not has_data:
        print("overlay: no overlay data")
        return 0
    for path, message in failures:
        print(f"overlay: {path}: {message}")
    for path, message in warnings:
        print(f"overlay: {path}: warning: {message}")
    if failures:
        return 1
    root = repo / "score-context"
    node_dir = root / "nodes"
    edge_dir = root / "edges"
    node_count = len(list(node_dir.glob("*.json"))) if node_dir.exists() else 0
    edge_count = len(list(edge_dir.glob("*.json"))) if edge_dir.exists() else 0
    print(f"overlay: valid ({node_count} nodes, {edge_count} edges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
