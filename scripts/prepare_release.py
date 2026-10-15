#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
"""Set the release version and pin all MCP sources to a commit.

Run on an up-to-date main. The pins point at the current HEAD, the release
commit itself only changes version metadata (checked by check_pins --release).
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER_RE = re.compile(r"\d+\.\d+\.\d+")
SHA_RE = re.compile(r"[0-9a-f]{40}")
SOURCE_RE = re.compile(
    r"(git\+https://github\.com/eclipse-score/mcp-servers)(?:@[^#\s]*)?"
    r"(#subdirectory=[^\s'\"]+)(?:[ \t]+#[ \t]*\S+)?"
)
TOP_VERSION_RE = re.compile(r"^(version:\s*)\S+", re.MULTILINE)
MARKETPLACE_VERSION_RE = re.compile(r"^(\s+version:\s*)\S+", re.MULTILINE)
FEATURE_VERSION_RE = re.compile(r'^(\s*"version":\s*)"[^"]*"', re.MULTILINE)
PYPROJECT_VERSION_RE = re.compile(r'^(version\s*=\s*)"[^"]*"', re.MULTILINE)


def current_version(root: Path = ROOT) -> str:
    match = TOP_VERSION_RE.search((root / "apm.yml").read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit("apm.yml: no version")
    return match.group(0).split(":", 1)[1].strip().strip("'\"")


def package_dirs(root: Path) -> list[Path]:
    return [
        path
        for path in sorted((root / "packages").iterdir())
        if path.is_dir() and not path.name.startswith("_")
    ]


def update(path: Path, version: str, commit: str) -> bool:
    text = path.read_text(encoding="utf-8")
    new = text
    if path.name == "pyproject.toml":
        new = PYPROJECT_VERSION_RE.sub(rf'\g<1>"{version}"', new, count=1)
    elif path.name == "devcontainer-feature.json":
        new = FEATURE_VERSION_RE.sub(rf'\g<1>"{version}"', new, count=1)
    elif path.name == "install.sh":
        new = SOURCE_RE.sub(rf"\g<1>@{commit}\g<2> # v{version}", new)
    else:
        new = TOP_VERSION_RE.sub(rf"\g<1>{version}", new, count=1)
        new = SOURCE_RE.sub(rf"\g<1>@{commit}\g<2> # v{version}", new)
        if path.parent.name != "packages" and path.parent.parent.name != "packages":
            new = MARKETPLACE_VERSION_RE.sub(rf'\g<1>"{version}"', new)
    if new != text:
        path.write_text(new, encoding="utf-8")
    return new != text


def prepare(version: str, commit: str, root: Path = ROOT) -> list[Path]:
    if not SEMVER_RE.fullmatch(version):
        raise SystemExit(f"version must be MAJOR.MINOR.PATCH, got {version!r}")
    if not SHA_RE.fullmatch(commit):
        raise SystemExit(f"commit must be a full SHA, got {commit!r}")
    files = [root / "apm.yml"] + [
        package / name
        for package in package_dirs(root)
        for name in ("apm.yml", "mcp.yml", "pyproject.toml")
        if (package / name).exists()
    ]
    files += [
        *sorted(root.glob("features/src/*/install.sh")),
        *sorted(root.glob("features/src/*/devcontainer-feature.json")),
    ]
    return [path for path in files if update(path, version, commit)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="release version, e.g. 0.2.0")
    parser.add_argument("--ref", default="HEAD", help="commit to pin (default HEAD)")
    parser.add_argument(
        "--current", action="store_true", help="print the current version and exit"
    )
    args = parser.parse_args()
    if args.current:
        print(current_version())
        return 0
    if args.version is None:
        parser.error("version is required")
    commit = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--verify", f"{args.ref}^{{commit}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    for path in prepare(args.version, commit):
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
