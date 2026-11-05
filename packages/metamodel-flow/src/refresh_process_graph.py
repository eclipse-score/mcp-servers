# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Refresh the committed process graph from an upstream needs artefact."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from process_projection import (
    AdapterReport,
    build_artifact,
    write_artifact_payload,
)

_SOURCE_REPO_URL = "https://github.com/eclipse-score/process_description.git"
# REUSE-IgnoreStart
_SOURCE_FILE_HEADER = (
    "# SPDX-License-Identifier: Apache-2.0\n"
    "# Copyright (c) 2026 Contributors to the Eclipse Foundation\n"
)
# REUSE-IgnoreEnd


@dataclass(frozen=True)
class ArtifactStats:
    commit: str
    node_counts: dict[str, int]
    nodes: int
    edges: int


def type_deltas(
    old: Mapping[str, int], new: Mapping[str, int]
) -> tuple[tuple[str, int], ...]:
    """Return changed node-type counts in deterministic order."""
    return tuple(
        (node_type, new.get(node_type, 0) - old.get(node_type, 0))
        for node_type in sorted(set(old) | set(new))
        if new.get(node_type, 0) != old.get(node_type, 0)
    )


def _empty_stats() -> ArtifactStats:
    return ArtifactStats(commit="", node_counts={}, nodes=0, edges=0)


def _stats_from_payload(payload: object) -> ArtifactStats | None:
    if not isinstance(payload, dict):
        return None
    typed_payload = cast(dict[str, object], payload)
    source = typed_payload.get("source")
    nodes = typed_payload.get("nodes")
    edges = typed_payload.get("edges")
    if (
        not isinstance(source, dict)
        or not isinstance(nodes, list)
        or not isinstance(edges, list)
    ):
        return None
    typed_source = cast(dict[str, object], source)
    typed_nodes = cast(list[object], nodes)
    typed_edges = cast(list[object], edges)
    commit = typed_source.get("commit")
    if not isinstance(commit, str):
        return None
    node_counts: dict[str, int] = {}
    for node_value in typed_nodes:
        if not isinstance(node_value, dict):
            return None
        node = cast(dict[str, object], node_value)
        node_type = node.get("type")
        if not isinstance(node_type, str):
            return None
        node_counts[node_type] = node_counts.get(node_type, 0) + 1
    return ArtifactStats(
        commit=commit,
        node_counts=node_counts,
        nodes=len(typed_nodes),
        edges=len(typed_edges),
    )


def _read_artifact(
    path: Path,
) -> tuple[dict[str, object], ArtifactStats] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None
    stats = _stats_from_payload(payload)
    if not isinstance(payload, dict) or stats is None:
        return None
    return cast(dict[str, object], payload), stats


def _without_generated_at(payload: Mapping[str, object]) -> dict[str, object]:
    normalized = dict(payload)
    source = payload.get("source")
    if isinstance(source, dict):
        typed_source = cast(dict[str, object], source)
        normalized["source"] = {
            key: value for key, value in typed_source.items() if key != "generated_at"
        }
    return normalized


def _source_text(source_commit: str) -> str:
    return (
        _SOURCE_FILE_HEADER
        + "\n"
        + f"source_repo_url={_SOURCE_REPO_URL}\n"
        + f"source_commit={source_commit}\n"
        + "generator_command="
        + "python packages/metamodel-flow/src/refresh_process_graph.py "
        + "--needs <needs.json from 'bazel build //:needs_json' in "
        + f"process_description> --source-commit {source_commit}\n"
    )


def _summary(
    old: ArtifactStats,
    new: ArtifactStats,
    report: AdapterReport,
    source_commit: str,
    current: bool,
) -> str:
    deltas = type_deltas(old.node_counts, new.node_counts)
    lines = [
        "# Process graph refresh",
        "",
        f"- Source commit: `{old.commit}` → `{source_commit}`",
        f"- Total nodes: {old.nodes} → {new.nodes}",
        f"- Total edges: {old.edges} → {new.edges}",
        "- Per-type node deltas:",
    ]
    if deltas:
        lines.extend(
            f"  - {'+' if delta > 0 else ''}{delta} {node_type}"
            for node_type, delta in deltas
        )
    else:
        lines.append("  - none")
    lines.extend(
        [
            "- Projection counters: "
            f"skipped_needs={report.skipped_needs}, "
            f"ignored_types={report.ignored_types}, "
            f"skipped_links={report.skipped_links}",
            "- The artefact is generated and reviewed via this summary, "
            "not by reading the JSON.",
            (
                "- The artefact is already current; both model files were "
                "left untouched."
                if current
                else "- The artefact was refreshed from the upstream projection."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def refresh(
    *,
    needs: Path,
    source_commit: str,
    repo_root: Path,
    observed_at: str,
    summary_out: Path | None = None,
) -> str:
    """Refresh the process graph and return its review summary."""
    model_dir = repo_root / "packages" / "metamodel-flow" / "model"
    artifact_path = model_dir / "process_graph.json"
    source_path = model_dir / "process_source.txt"
    existing = _read_artifact(artifact_path)
    old = existing[1] if existing is not None else _empty_stats()
    existing_payload = existing[0] if existing is not None else None
    payload, report = build_artifact(needs, source_commit, observed_at)
    new = _stats_from_payload(payload)
    if new is None:
        raise ValueError("generated process graph artefact could not be parsed")
    current = existing_payload is not None and _without_generated_at(
        existing_payload
    ) == _without_generated_at(payload)
    if not current:
        write_artifact_payload(payload, artifact_path)
        source_path.write_text(_source_text(source_commit), encoding="utf-8")
    summary = _summary(old, new, report, source_commit, current)
    if summary_out is not None:
        summary_out.parent.mkdir(parents=True, exist_ok=True)
        summary_out.write_text(summary, encoding="utf-8")
    print(summary, end="")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--needs", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--observed-at", default=datetime.now(UTC).isoformat())
    parser.add_argument("--summary-out", type=Path)
    args = parser.parse_args(argv)
    try:
        refresh(
            needs=args.needs,
            source_commit=args.source_commit,
            repo_root=args.repo_root,
            observed_at=args.observed_at,
            summary_out=args.summary_out,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
