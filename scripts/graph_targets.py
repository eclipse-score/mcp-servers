#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
"""Build a GitHub Actions matrix of graph targets from known_good.json."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_RE = re.compile(
    r"^https://github\.com/eclipse-score/([A-Za-z0-9_.-]+?)(?:\.git)?$"
)
HASH_RE = re.compile(r"^[0-9a-f]{40}$")


def targets(
    known_good: dict[str, Any], groups: list[str], pinned: bool = False
) -> list[dict[str, str]]:
    """Select modules; ref is the known-good hash if pinned, else the default branch."""
    result: list[dict[str, str]] = []
    for group in groups:
        for module, entry in known_good.get("modules", {}).get(group, {}).items():
            repo = REPO_RE.match(str(entry.get("repo", "")))
            ref = str(entry.get("hash", ""))
            if repo is None or (pinned and not HASH_RE.match(ref)):
                print(
                    f"skipping {module}: no eclipse-score repo or pinned hash",
                    file=sys.stderr,
                )
                continue
            result.append({"name": repo.group(1), "ref": ref if pinned else ""})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("known_good", type=Path)
    parser.add_argument("--group", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--known-good", dest="pinned", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.known_good.read_text(encoding="utf-8"))
    selected = targets(data, args.group or ["target_sw"], args.pinned)
    if args.limit > 0:
        selected = selected[: args.limit]
    print(json.dumps({"include": selected}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
