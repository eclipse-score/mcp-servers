#!/usr/bin/env python3
# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************
"""Refresh the committed metamodel projection from docs-as-code.

Fetches ``metamodel.yaml`` at a docs-as-code commit, regenerates
``model/agent_context.json`` and ``model/source.txt`` and re-renders the
instruction Markdown.  ``--check`` only reports whether the projection
changed (exit code 1) and writes nothing.

Usage:
    refresh_model.py [--ref main|SHA] [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from agent_context import parse_agent_context
from export_metamodel_data import (
    build_metamodel_data,
    load_metamodel_yaml_bytes,
    render_data,
)
from generate_agent_context import project_metamodel, render_projection
from render_markdown import write_output

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/eclipse-score/docs-as-code.git"
METAMODEL_PATH = "src/extensions/score_metamodel/metamodel.yaml"
RAW_URL = "https://raw.githubusercontent.com/eclipse-score/docs-as-code/{sha}/{path}"
MAX_BYTES = 4 * 1024 * 1024
TIMEOUT_SECONDS = 30
SHA_RE = re.compile(r"[0-9a-f]{40}")
BRANCH_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}")
REFRESH_COMMAND = "uv run python packages/metamodel-flow/src/refresh_model.py"
DATA_FILE = "metamodel-data.json"

Fetcher = Callable[[str], bytes]


def resolve_ref(ref: str) -> str:
    """Return the commit SHA for a docs-as-code branch name or full SHA."""
    if SHA_RE.fullmatch(ref):
        return ref
    if not BRANCH_RE.fullmatch(ref) or ".." in ref:
        raise ValueError(f"invalid ref {ref!r}")
    result = subprocess.run(
        ["git", "ls-remote", "--", REPO_URL, f"refs/heads/{ref}"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=True,
    )
    sha = result.stdout.split("\t", 1)[0].strip()
    if not SHA_RE.fullmatch(sha):
        raise ValueError(f"branch {ref!r} not found in {REPO_URL}")
    return sha


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
        data: bytes = response.read(MAX_BYTES + 1)
    return data


def fetch_metamodel(sha: str, fetcher: Fetcher = fetch) -> bytes:
    if not SHA_RE.fullmatch(sha):
        raise ValueError(f"invalid commit {sha!r}")
    raw = fetcher(RAW_URL.format(sha=sha, path=METAMODEL_PATH))
    if len(raw) > MAX_BYTES:
        raise ValueError(f"metamodel.yaml exceeds {MAX_BYTES} bytes")
    return raw


def source_text(sha: str) -> str:
    return (
        "# SPDX"
        "-License-Identifier: Apache-2.0\n"
        "# Copyright (c) 2026 Contributors to the Eclipse Foundation\n"
        "\n"
        f"source_repo_url={REPO_URL}\n"
        f"source_path={METAMODEL_PATH}\n"
        f"source_commit={sha}\n"
        f"generator_command={REFRESH_COMMAND} --ref {sha}\n"
    )


def _content(projection: dict[str, Any]) -> dict[str, Any]:
    """Projection without the digest, which also changes for comment edits."""
    return {
        key: value for key, value in projection.items() if key != "metamodel_digest"
    }


def _data_content(data: dict[str, Any]) -> dict[str, Any]:
    """Metamodel data without the digest and source commit, which change on any edit."""
    return {
        key: value
        for key, value in data.items()
        if key not in ("metamodel_digest", "source")
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def refresh(
    sha: str,
    *,
    package_root: Path = PACKAGE_ROOT,
    check: bool = False,
    fetcher: Fetcher = fetch,
) -> bool:
    """Regenerate the model files; return True if their content changed.

    Files are written only when content changed, so the recorded source commit
    always matches the content that is committed.
    """
    raw = fetch_metamodel(sha, fetcher)
    projection = project_metamodel(raw)
    parse_agent_context(projection)
    data = build_metamodel_data(
        load_metamodel_yaml_bytes(raw),
        hashlib.sha256(raw).hexdigest(),
        sha,
        REPO_URL,
    )
    model_dir = package_root / "model"
    model_path = model_dir / "agent_context.json"
    data_path = model_dir / DATA_FILE
    changed = _content(projection) != _content(_load_json(model_path)) or _data_content(
        data
    ) != _data_content(_load_json(data_path))
    if check or not changed:
        return changed
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path.write_text(render_projection(projection), encoding="utf-8")
    data_path.write_text(render_data(data), encoding="utf-8")
    (model_dir / "source.txt").write_text(source_text(sha), encoding="utf-8")
    write_output(package_root)
    return changed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh the metamodel projection from docs-as-code."
    )
    parser.add_argument("--ref", default="main", help="docs-as-code branch or SHA")
    parser.add_argument(
        "--check", action="store_true", help="only report drift (exit code 1)"
    )
    parser.add_argument(
        "--package-root", type=Path, default=PACKAGE_ROOT, help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)
    try:
        sha = resolve_ref(args.ref)
        changed = refresh(sha, package_root=args.package_root, check=args.check)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"refresh_model: {error}", file=sys.stderr)
        return 2
    if not args.check:
        print(f"Refreshed from docs-as-code {sha} (changed: {changed}).")
        return 0
    if not changed:
        print(f"metamodel-flow is up to date with docs-as-code {sha}.")
        return 0
    print(
        f"The S-CORE metamodel in docs-as-code changed at {sha}.\n\n"
        "Refresh `packages/metamodel-flow` and open a PR:\n\n"
        f"```\n{REFRESH_COMMAND} --ref {sha}\n```"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
