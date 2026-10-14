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
GRAPHIFY_RE = re.compile(r"(?<![\w.-])graphifyy(\[[\w,]+\])?(==[\w.]+)?(?![\w-])")
INSTALL_CONTEXT_RE = re.compile(r"\b(pip|pipx|uv|uvx)\b|--from\b|--with\b")
SCANNED_SUFFIXES = {".md", ".py", ".toml", ".yml", ".yaml", ""}
EXCLUDED_DIRS = {".git", ".venv", "node_modules", "graphify-out"}
EXCLUDED_FILES = {Path(__file__).resolve(), ROOT / "tests" / "test_check_pins.py"}


def graphify_pin(root: Path = ROOT) -> str:
    pyproject = root / "packages/graphify-codegraph/pyproject.toml"
    match = GRAPHIFY_PIN_RE.search(pyproject.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"No graphifyy[mcp]==<version> dependency in {pyproject}")
    return match.group(1)


def check_mcp_sources(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.glob("packages/*/*.yml")):
        text = path.read_text(encoding="utf-8")
        version = VERSION_RE.search(text)
        for match in MCP_SOURCE_RE.finditer(text):
            expected = f"@v{version.group(1)}" if version else None
            if match.group(1) != expected:
                errors.append(
                    f"{path.relative_to(root)}: MCP source must be pinned to "
                    f"{expected or 'a release tag'}, found {match.group(1) or 'no ref'}"
                )
    return errors


def scanned_files(root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts) or not path.is_file():
            continue
        if path.suffix in SCANNED_SUFFIXES and path not in EXCLUDED_FILES:
            files.append(path)
    return sorted(files)


def is_install_spec(line: str, match: re.Match[str]) -> bool:
    quoted = match.start() > 0 and line[match.start() - 1] in "\"'"
    return quoted or INSTALL_CONTEXT_RE.search(line) is not None


def check_graphify_installs(pin: str, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for path in scanned_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            for match in GRAPHIFY_RE.finditer(line):
                if is_install_spec(line, match) and match.group(2) != f"=={pin}":
                    errors.append(
                        f"{path.relative_to(root)}:{number}: graphifyy must be "
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
