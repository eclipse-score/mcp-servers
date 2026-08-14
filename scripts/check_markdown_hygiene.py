#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Check package Markdown files for duplicate content and broken local links."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections.abc import Iterable
from pathlib import Path

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Markdown hygiene in selected repository paths"
    )
    parser.add_argument("--root", default=".", help="Repository root path")
    parser.add_argument(
        "--include",
        action="append",
        default=["packages"],
        help="Path (file or directory) under root to include; repeatable",
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
    return sorted(set(files))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def find_duplicate_markdown(files: list[Path]) -> list[list[Path]]:
    by_hash: dict[str, list[Path]] = {}
    for path in files:
        by_hash.setdefault(sha256_of(path), []).append(path)
    return [group for group in by_hash.values() if len(group) > 1]


def strip_anchor_and_query(target: str) -> str:
    return target.split("#", 1)[0].split("?", 1)[0]


def is_external_link(target: str) -> bool:
    return target.lower().startswith(("http://", "https://", "mailto:", "tel:"))


def find_broken_local_links(files: list[Path], root: Path) -> list[tuple[Path, str]]:
    issues: list[tuple[Path, str]] = []
    for markdown_file in files:
        text = markdown_file.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = raw_target.strip()
            if not target or target.startswith("#") or is_external_link(target):
                continue
            if "{" in target or "}" in target:
                continue

            normalized = strip_anchor_and_query(target)
            if not normalized:
                continue
            if normalized.startswith("/"):
                resolved = (root / normalized.lstrip("/")).resolve()
            else:
                resolved = (markdown_file.parent / normalized).resolve()
            if not resolved.exists():
                issues.append((markdown_file, target))
    return issues


def print_duplicate_report(duplicates: list[list[Path]], root: Path) -> None:
    if not duplicates:
        print("No duplicate Markdown files detected.")
        return
    print("Duplicate Markdown files detected:")
    for group in duplicates:
        print("- Duplicate group:")
        for path in group:
            print(f"  - {to_repo_relative(path, root)}")


def print_broken_link_report(broken: list[tuple[Path, str]], root: Path) -> None:
    if not broken:
        print("No broken local Markdown links detected.")
        return
    print("Broken local Markdown links detected:")
    for markdown_file, target in broken:
        print(f"- {to_repo_relative(markdown_file, root)}: {target}")


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    files = gather_markdown_files(root, args.include)
    if not files:
        print("No Markdown files found for the configured include paths.")
        return 0

    duplicates = find_duplicate_markdown(files)
    broken_links = find_broken_local_links(files, root)
    print(f"Scanned {len(files)} Markdown files.")
    print_duplicate_report(duplicates, root)
    print_broken_link_report(broken_links, root)

    if duplicates or broken_links:
        print("Markdown hygiene check failed.")
        return 1
    print("Markdown hygiene check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
