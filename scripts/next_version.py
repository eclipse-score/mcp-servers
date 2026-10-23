#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
"""Derive the next release version from conventional commits since the last tag.

``feat`` bumps the minor, ``fix``/``perf`` bump the patch version, a ``!`` after
the type or a ``BREAKING CHANGE:`` footer bumps the major version (the minor
version while still on 0.x). Other types do not trigger a release.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG_RE = re.compile(r"v(\d+)\.(\d+)\.(\d+)")
HEADER_RE = re.compile(r"(?P<type>[a-z]+)(?:\([^)]*\))?(?P<breaking>!)?: \S")
BREAKING_FOOTER_RE = re.compile(r"^BREAKING[ -]CHANGE: ", re.MULTILINE)
LEVELS = ("patch", "minor", "major")


def bump_level(message: str) -> str | None:
    match = HEADER_RE.match(message.strip())
    if match is None:
        return None
    if match.group("breaking") or BREAKING_FOOTER_RE.search(message):
        return "major"
    if match.group("type") == "feat":
        return "minor"
    if match.group("type") in ("fix", "perf"):
        return "patch"
    return None


def next_version(current: str, messages: list[str]) -> str | None:
    match = TAG_RE.fullmatch(f"v{current}")
    if match is None:
        raise ValueError(f"not a MAJOR.MINOR.PATCH version: {current!r}")
    levels = [level for level in map(bump_level, messages) if level is not None]
    if not levels:
        return None
    level = max(levels, key=LEVELS.index)
    major, minor, patch = (int(part) for part in match.groups())
    if level == "major" and major == 0:
        level = "minor"
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def git(*args: str, root: Path = ROOT) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout


def last_tag(root: Path = ROOT) -> str:
    for tag in git("tag", "--list", "v*", "--sort=-v:refname", root=root).split():
        if TAG_RE.fullmatch(tag):
            return tag
    raise SystemExit("no vX.Y.Z tag found")


def commit_messages(since: str, ref: str, root: Path = ROOT) -> list[str]:
    log = git("log", "--format=%B%x00", f"{since}..{ref}", root=root)
    return [message.strip() for message in log.split("\0") if message.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD", help="commit to release")
    args = parser.parse_args()
    tag = last_tag()
    version = next_version(tag[1:], commit_messages(tag, args.ref))
    if version is None:
        print(f"no feat, fix or breaking commits since {tag}", file=sys.stderr)
        return 1
    print(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
