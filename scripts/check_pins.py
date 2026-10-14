#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
"""Check that MCP server sources and graphify installs use pinned versions."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MCP_SOURCE_RE = re.compile(
    r"git\+https://github\.com/eclipse-score/mcp-servers(@[^#\s]*)?#"
)
VERSION_RE = re.compile(r"^version:\s*['\"]?([^'\"\s]+)", re.MULTILINE)
GRAPHIFY_PIN_RE = re.compile(r'"graphifyy\[mcp\]==([^"]+)"')
GRAPHIFY_RE = re.compile(r"graphifyy(\[mcp\])?(==[\w.]+)?")
SCANNED_SUFFIXES = {".md", ".py", ".toml", ".yml", ".yaml", ""}
EXCLUDED_DIRS = {".git", ".venv", "node_modules", "graphify-out"}


def graphify_pin() -> str:
    pyproject = ROOT / "packages/graphify-codegraph/pyproject.toml"
    match = GRAPHIFY_PIN_RE.search(pyproject.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"No graphifyy[mcp]==<version> dependency in {pyproject}")
    return match.group(1)


def check_mcp_sources() -> list[str]:
    errors: list[str] = []
    for path in sorted(ROOT.glob("packages/*/*.yml")):
        text = path.read_text(encoding="utf-8")
        version = VERSION_RE.search(text)
        for match in MCP_SOURCE_RE.finditer(text):
            expected = f"@v{version.group(1)}" if version else None
            if match.group(1) != expected:
                errors.append(
                    f"{path.relative_to(ROOT)}: MCP source must be pinned to "
                    f"{expected or 'a release tag'}, found {match.group(1) or 'no ref'}"
                )
    return errors


def scanned_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in path.parts) or not path.is_file():
            continue
        if path.suffix in SCANNED_SUFFIXES and path != Path(__file__).resolve():
            files.append(path)
    return sorted(files)


def check_graphify_installs(pin: str) -> list[str]:
    errors: list[str] = []
    for path in scanned_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            for match in GRAPHIFY_RE.finditer(line):
                if match.group(2) != f"=={pin}":
                    errors.append(
                        f"{path.relative_to(ROOT)}:{number}: graphifyy must be "
                        f"pinned to =={pin}"
                    )
    return errors


def main() -> int:
    errors = check_mcp_sources() + check_graphify_installs(graphify_pin())
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
