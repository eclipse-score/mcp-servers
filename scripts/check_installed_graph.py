#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Check the metamodel and process graphs shipped in an APM consumer install.

Runs the installed context-discipline loader from the consumer directory, so the
check covers what an agent would actually read: the process graph discovered
under apm_modules, and the metamodel data committed next to it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _first(consumer: Path, pattern: str, name: str) -> Path:
    matches = sorted((consumer / "apm_modules").glob(pattern))
    if not matches:
        raise RuntimeError(f"{name} is not installed under apm_modules")
    return matches[0]


def check(consumer: Path) -> list[str]:
    consumer = consumer.resolve()
    src = _first(
        consumer, "**/context-discipline/src/context_sources.py", "context-discipline"
    ).parent
    model = _first(
        consumer, "**/metamodel-flow/model/process_graph.json", "metamodel-flow"
    ).parent
    failures: list[str] = []

    data = json.loads((model / "metamodel-data.json").read_text(encoding="utf-8"))
    if not COMMIT_RE.fullmatch(str(data.get("source", {}).get("commit", ""))):
        failures.append("metamodel-data.json does not record a full source commit")
    if not data.get("need_types"):
        failures.append("metamodel-data.json has no need types")

    sys.path.insert(0, str(src))
    from context_policy import load_policy
    from context_sources import load_process_graph

    graph = load_process_graph(consumer, load_policy(consumer))
    workflows = [node for node in graph.nodes.values() if node.type == "workflow"]
    if not graph.nodes:
        failures.append("installed process graph loaded no nodes")
    if not workflows:
        failures.append("installed process graph has no workflow nodes")
    if not graph.edges:
        failures.append("installed process graph has no edges")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("consumer", type=Path)
    args = parser.parse_args(argv)
    try:
        failures = check(args.consumer)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"check_installed_graph: {error}", file=sys.stderr)
        return 2
    for failure in failures:
        print(f"check_installed_graph: {failure}", file=sys.stderr)
    if failures:
        return 1
    print("installed metamodel and process graphs load")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
