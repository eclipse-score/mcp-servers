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

"""Human-facing command line interface for context scoring and learning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from score_context.context import ContextEngine
from score_context.graph import compose_fragments
from score_context.harness.base import TaskSpec
from score_context.harness.candidate import ContextHarness
from score_context.harness.experience import ExperiencePersistence
from score_context.harness.gate import lane_a_gate
from score_context.policy import load_policy


def _path(root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else root / candidate


def _load_task(path: Path) -> TaskSpec:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("task must be a JSON object")
    return cast(TaskSpec, raw)


def _root() -> Path:
    return Path.cwd()


def _run(args: argparse.Namespace, root: Path) -> int:
    task = _load_task(_path(root, args.task))
    graph_path = _path(root, args.graph or "harness/spec/graph_fragment.json")
    policy = load_policy(root / "harness/policy.yml")
    persistence = ExperiencePersistence(_path(root, args.artifacts))
    candidate = ContextHarness(
        compose_fragments([graph_path]),
        repo="mcp-servers",
        role="developer",
        track_route=True,
    )
    context = candidate.get_context(task, persistence.load_weights(), policy)
    selection = candidate.last_selection
    if selection is None:
        raise ValueError("candidate did not produce a selection")
    gate = lane_a_gate(context, task, selection.route)
    experience = candidate.record_experience(gate, task)
    persistence.append_experience(experience)
    selected = [node.id for node in selection.selected]
    print(f"verdict: {gate.verdict}")
    print(f"selected: {', '.join(selected)}")
    print(f"appended: {persistence.experiences_path}")
    return 0 if gate.verdict == "pass" else 1


def _aggregate(args: argparse.Namespace, root: Path) -> int:
    policy = load_policy(root / "harness/policy.yml")
    path = ExperiencePersistence(_path(root, args.artifacts)).aggregate(policy)
    print(f"wrote: {path}")
    return 0


def _demo(root: Path) -> int:
    graph = compose_fragments([root / "harness/demo/graph.json"])
    task = _load_task(root / "harness/demo/task.json")
    policy = load_policy(root / "harness/policy.yml")
    persistence = ExperiencePersistence(root / "harness/demo")
    weights = persistence.load_weights()
    engine = ContextEngine(graph)
    baseline = engine.get_context(task, "mcp-servers", "developer", 2, policy=policy)
    learned = engine.get_context(
        task,
        "mcp-servers",
        "developer",
        2,
        experience_weights=weights,
        policy=policy,
    )
    baseline_gate = lane_a_gate(baseline.rendered, task)
    learned_gate = lane_a_gate(learned.rendered, task)
    baseline_ids = [node.id for node in baseline.selected]
    learned_ids = [node.id for node in learned.selected]
    moved = [node_id for node_id in learned_ids if node_id not in baseline_ids]
    print("score-ctx demo")
    print("without learned weights:")
    print(f"  selected: {', '.join(baseline_ids)}")
    print(f"  lane_a_gate: {baseline_gate.verdict}")
    print("with learned weights:")
    print(f"  selected: {', '.join(learned_ids)}")
    print(f"  lane_a_gate: {learned_gate.verdict}")
    print(f"moved into selection: {', '.join(moved)}")
    print(f"gate flip: {baseline_gate.verdict} -> {learned_gate.verdict}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run one score-ctx subcommand."""
    parser = argparse.ArgumentParser(prog="score-ctx")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run")
    run.add_argument("--task", required=True)
    run.add_argument("--graph")
    run.add_argument("--artifacts", default="harness/artifacts")

    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--artifacts", default="harness/artifacts")

    subparsers.add_parser("demo")
    args = parser.parse_args(argv)
    root = _root()
    if args.command == "run":
        return _run(args, root)
    if args.command == "aggregate":
        return _aggregate(args, root)
    return _demo(root)


if __name__ == "__main__":
    raise SystemExit(main())
