#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
"""Check that MCP server sources and graphify installs use pinned versions.

MCP sources must pin a commit SHA followed by a ``# v<version>`` comment.
With ``--release`` the script also checks that the pinned commit only differs
from HEAD in release metadata, so the tagged release runs the pinned code.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MCP_SOURCE_RE = re.compile(
    r"git\+https://github\.com/eclipse-score/mcp-servers(?:@([^#\s]*))?"
    r"#subdirectory=[^\s'\"]+(?:[ \t]+#[ \t]*(\S+))?"
)
SHA_RE = re.compile(r"[0-9a-f]{40}")
VERSION_RE = re.compile(r"^version:\s*['\"]?([^'\"\s]+)", re.MULTILINE)
MARKETPLACE_VERSION_RE = re.compile(r"^\s+version:\s*['\"]?([^'\"\s]+)", re.MULTILINE)
PYPROJECT_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)
RELEASE_FILE_RE = re.compile(
    r"apm\.yml|uv\.lock|packages/[^/]+/(?:apm\.yml|mcp\.yml|pyproject\.toml)"
    r"|features/src/[^/]+/(?:install\.sh|devcontainer-feature\.json)"
)
FEATURE_VERSION_RE = re.compile(r'^\s*"version":\s*"([^"]+)"', re.MULTILINE)
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


def release_version(root: Path = ROOT) -> str | None:
    manifest = root / "apm.yml"
    match = (
        VERSION_RE.search(manifest.read_text(encoding="utf-8"))
        if manifest.exists()
        else None
    )
    return match.group(1) if match else None


def pinned_files(root: Path = ROOT) -> list[Path]:
    return sorted(root.glob("packages/*/*.yml")) + sorted(
        root.glob("features/src/*/install.sh")
    )


def check_mcp_sources(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    release = release_version(root)
    for path in pinned_files(root):
        text = path.read_text(encoding="utf-8")
        match = VERSION_RE.search(text)
        version = release if path.name == "install.sh" else match and match.group(1)
        expected = f"v{version}" if version else "v<version>"
        for match in MCP_SOURCE_RE.finditer(text):
            ref, comment = match.group(1), match.group(2)
            where = path.relative_to(root)
            if ref is None or not SHA_RE.fullmatch(ref):
                errors.append(
                    f"{where}: MCP source must be pinned to a full commit SHA, "
                    f"found {ref or 'no ref'}"
                )
            if comment != expected:
                errors.append(
                    f"{where}: MCP source needs the comment '# {expected}', "
                    f"found {'# ' + comment if comment else 'none'}"
                )
    return errors


def package_dirs(root: Path = ROOT) -> list[Path]:
    return [
        path
        for path in sorted((root / "packages").iterdir())
        if path.is_dir() and not path.name.startswith("_")
    ]


def check_versions(root: Path = ROOT) -> list[str]:
    """All packages share the release version declared in the root apm.yml."""
    manifest = (root / "apm.yml").read_text(encoding="utf-8")
    release = VERSION_RE.search(manifest)
    if release is None:
        return ["apm.yml: no version"]
    found = [
        ("apm.yml marketplace", v) for v in MARKETPLACE_VERSION_RE.findall(manifest)
    ]
    for package in package_dirs(root):
        for name, pattern in (
            ("apm.yml", VERSION_RE),
            ("mcp.yml", VERSION_RE),
            ("pyproject.toml", PYPROJECT_VERSION_RE),
        ):
            path = package / name
            if path.exists():
                match = pattern.search(path.read_text(encoding="utf-8"))
                found.append(
                    (str(path.relative_to(root)), match.group(1) if match else "none")
                )
    for path in sorted(root.glob("features/src/*/devcontainer-feature.json")):
        match = FEATURE_VERSION_RE.search(path.read_text(encoding="utf-8"))
        found.append((str(path.relative_to(root)), match.group(1) if match else "none"))
    return [
        f"{where}: version {version} differs from release version {release.group(1)}"
        for where, version in found
        if version != release.group(1)
    ]


def pinned_commits(root: Path = ROOT) -> set[str]:
    return {
        match.group(1) or ""
        for path in pinned_files(root)
        for match in MCP_SOURCE_RE.finditer(path.read_text(encoding="utf-8"))
    }


def check_release(root: Path = ROOT) -> list[str]:
    """The pinned commit may only differ from HEAD in release metadata."""
    commits = pinned_commits(root)
    if len(commits) != 1:
        return [f"MCP sources must pin one common commit, found {sorted(commits)}"]
    commit = commits.pop()
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", commit, "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return [f"pinned commit {commit} is not in the local history"]
    return [
        f"{name}: changed since pinned commit {commit[:12]}, "
        "only release metadata may differ"
        for name in result.stdout.splitlines()
        if not RELEASE_FILE_RE.fullmatch(name)
    ]


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release",
        action="store_true",
        help="also check that the pinned commit matches HEAD apart from metadata",
    )
    args = parser.parse_args()
    errors = (
        check_mcp_sources() + check_versions() + check_graphify_installs(graphify_pin())
    )
    if args.release:
        errors += check_release()
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
