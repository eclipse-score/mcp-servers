#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
"""Build a GitHub Actions matrix of eclipse-score modules to graph.

Only the module list is read from known_good.json; the graphs are built from
each module's default branch HEAD.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_RE = re.compile(
    r"^https://github\.com/eclipse-score/([A-Za-z0-9_.-]+?)(?:\.git)?$"
)


def targets(modules: dict[str, Any], groups: list[str]) -> list[dict[str, str]]:
    """Select the eclipse-score repositories listed in the given groups."""
    result: list[dict[str, str]] = []
    for group in groups:
        for module, entry in modules.get("modules", {}).get(group, {}).items():
            repo = REPO_RE.match(str(entry.get("repo", "")))
            if repo is None:
                print(f"skipping {module}: no eclipse-score repo", file=sys.stderr)
                continue
            if {"name": repo.group(1)} not in result:
                result.append({"name": repo.group(1)})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modules", type=Path)
    parser.add_argument("--group", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    data = json.loads(args.modules.read_text(encoding="utf-8"))
    selected = targets(data, args.group or ["target_sw"])
    if args.limit > 0:
        selected = selected[: args.limit]
    print(json.dumps({"include": selected}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
