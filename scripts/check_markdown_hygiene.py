#!/usr/bin/env python3
"""Lightweight markdown hygiene checks for repository-scale governance docs.

Checks:
- Duplicate markdown files by content hash
- Broken local markdown links (relative repo paths)

Exit codes:
- 0: no issues
- 1: one or more issues found
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
DEFAULT_EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", ".mypy_cache", ".pytest_cache"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check markdown hygiene in a repository")
    parser.add_argument("--root", default=".", help="Repository root path")
    parser.add_argument(
        "--include",
        action="append",
        default=[".github", "README.md", "profile"],
        help="Path (file/dir) under root to include; repeatable",
    )
    return parser.parse_args()


def to_repo_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def gather_markdown_files(root: Path, include_paths: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for include in include_paths:
        candidate = (root / include).resolve()
        if not candidate.exists():
            continue
        if candidate.is_file() and candidate.suffix.lower() == ".md":
            files.append(candidate)
            continue
        if candidate.is_dir():
            for path in candidate.rglob("*.md"):
                if any(part in DEFAULT_EXCLUDED_DIRS for part in path.parts):
                    continue
                files.append(path.resolve())
    unique = sorted(set(files))
    return unique


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def find_duplicate_markdown(files: list[Path]) -> list[list[Path]]:
    by_hash: dict[str, list[Path]] = {}
    for path in files:
        file_hash = sha256_of(path)
        by_hash.setdefault(file_hash, []).append(path)
    return [group for group in by_hash.values() if len(group) > 1]


def strip_anchor_and_query(target: str) -> str:
    no_anchor = target.split("#", 1)[0]
    no_query = no_anchor.split("?", 1)[0]
    return no_query


def is_external_link(target: str) -> bool:
    lowered = target.lower()
    return lowered.startswith(("http://", "https://", "mailto:", "tel:"))


def find_broken_local_links(files: list[Path], root: Path) -> list[tuple[Path, str, str]]:
    issues: list[tuple[Path, str, str]] = []
    for markdown_file in files:
        text = markdown_file.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = raw_target.strip()
            if not target or target.startswith("#") or is_external_link(target):
                continue

            # Template placeholders are examples, not resolvable links.
            if "{" in target or "}" in target:
                continue

            normalized = strip_anchor_and_query(target)
            if not normalized:
                continue

            # Absolute repo path style: /path/from/repo/root
            if normalized.startswith("/"):
                resolved = (root / normalized.lstrip("/")).resolve()
            else:
                resolved = (markdown_file.parent / normalized).resolve()

            if not resolved.exists():
                issues.append((markdown_file, target, to_repo_relative(markdown_file, root)))
    return issues


def print_duplicate_report(duplicates: list[list[Path]], root: Path) -> None:
    if not duplicates:
        print("No duplicate markdown files detected.")
        return
    print("Duplicate markdown files detected:")
    for group in duplicates:
        print("- Duplicate group:")
        for path in group:
            print(f"  - {to_repo_relative(path, root)}")


def print_broken_link_report(broken: list[tuple[Path, str, str]], root: Path) -> None:
    if not broken:
        print("No broken local markdown links detected.")
        return
    print("Broken local markdown links detected:")
    for markdown_file, target, _ in broken:
        rel = to_repo_relative(markdown_file, root)
        print(f"- {rel}: {target}")


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()

    files = gather_markdown_files(root, args.include)
    if not files:
        print("No markdown files found for the configured include paths.")
        return 0

    duplicates = find_duplicate_markdown(files)
    broken_links = find_broken_local_links(files, root)

    print(f"Scanned {len(files)} markdown files.")
    print_duplicate_report(duplicates, root)
    print_broken_link_report(broken_links, root)

    has_issues = bool(duplicates or broken_links)
    if has_issues:
        print("Markdown hygiene check failed.")
        return 1

    print("Markdown hygiene check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
