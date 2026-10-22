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

"""Provide a code graph for the current repository without touching the worktree.

Order: an existing ``graphify-out/graph.json`` in the repository, then the
user cache under ``~/.local/share/score-agent``. For eclipse-score repositories
an empty cache is seeded from the central graph registry (merge-base commit,
then ``main``). The cache is refreshed by a local code-only build in the
background whenever HEAD moved.
"""

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import IO, Any

# Platform-compatible locking (fcntl is Unix-only)
try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]

REGISTRY = "https://ghcr.io"
NAMESPACE = "eclipse-score/mcp-servers/graphs"
MANIFEST_TYPE = "application/vnd.oci.image.manifest.v1+json"
LAYER_TYPE = "application/vnd.eclipse-score.graph.v1.tar+gzip"
ARTIFACT_FILES = {"graph.json", "manifest.json", "needs.json", "metadata.json"}
MAX_BLOB_BYTES = 256 * 1024 * 1024
TIMEOUT_SECONDS = 15
REMOTE_RE = re.compile(r"github\.com[:/]eclipse-score/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")
TAG_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}")
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")

Opener = Callable[[urllib.request.Request], IO[bytes]]


def _open(request: urllib.request.Request) -> IO[bytes]:
    return urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS)


def log(message: str) -> None:
    print(f"graphify-codegraph: {message}", file=sys.stderr)


def git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def repo_root(cwd: Path) -> Path | None:
    top = git(cwd, "rev-parse", "--show-toplevel")
    return Path(top) if top else None


def module_name(root: Path) -> str | None:
    match = REMOTE_RE.search(git(root, "remote", "get-url", "origin") or "")
    return match.group(1) if match else None


def cache_root() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "score-agent"


def cache_dir(root: Path) -> Path:
    digest = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:12]
    return cache_root() / f"{root.name}-{digest}"


def candidate_tags(root: Path) -> list[str]:
    tags: list[str] = []
    for upstream in ("origin/HEAD", "origin/main"):
        base = git(root, "merge-base", "HEAD", upstream)
        if base:
            tags.append(base)
            break
    return [*tags, "main"]


def _get(opener: Opener, url: str, headers: dict[str, str]) -> bytes:
    with opener(urllib.request.Request(url, headers=headers)) as response:
        data = response.read(MAX_BLOB_BYTES + 1)
    if len(data) > MAX_BLOB_BYTES:
        raise ValueError(f"response from {url} is too large")
    return data


def _unpack(blob: bytes, dest: Path) -> None:
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
        for member in archive.getmembers():
            name = member.name.removeprefix("./")
            if member.isfile() and name in ARTIFACT_FILES:
                handle = archive.extractfile(member)
                if handle is not None:
                    files[name] = handle.read()
    if "graph.json" not in files:
        raise ValueError("artifact has no graph.json")
    json.loads(files["graph.json"])
    dest.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        partial = dest / f".{name}.partial"
        partial.write_bytes(content)
        partial.replace(dest / name)


def resolve_graph_path(cwd: Path) -> Path | None:
    """Resolve the graph path for a repository (shared with context-discipline).

    Returns the path to the graph.json file, checking in order:
    1. Repository's graphify-out/graph.json
    2. User cache under ~/.local/share/score-agent

    Returns None if:
    - SCORE_AGENT_GRAPH=off is set
    - Not in a git repository
    """
    if os.environ.get("SCORE_AGENT_GRAPH", "").lower() in {"0", "off", "false"}:
        return None
    root = repo_root(cwd)
    if root is None:
        return None
    in_repo = root / "graphify-out" / "graph.json"
    if in_repo.exists():
        return in_repo
    cache = cache_dir(root)
    graph = cache / "graph.json"
    if graph.exists():
        return graph
    return None


def _acquire_lock(cache: Path) -> io.TextIOWrapper | None:
    """Acquire cache lock in a platform-compatible way."""
    cache.mkdir(parents=True, exist_ok=True)
    lock_file = (cache / ".lock").open("w")
    if fcntl is not None:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
        except BlockingIOError:
            lock_file.close()
            return None
    return lock_file


def _release_lock(lock_file: io.TextIOWrapper) -> None:
    """Release cache lock."""
    if fcntl is not None:
        fcntl.flock(lock_file, fcntl.LOCK_UN)  # type: ignore[attr-defined]
    lock_file.close()


def fetch(module: str, tag: str, dest: Path, opener: Opener = _open) -> bool:
    """Download graph ``module:tag`` into ``dest``; verify the blob digest."""
    if not TAG_RE.fullmatch(tag) or not TAG_RE.fullmatch(module):
        return False
    repository = f"{NAMESPACE}/{module}"
    try:
        token_url = f"{REGISTRY}/token?scope=repository:{repository}:pull"
        token: Any = json.loads(_get(opener, token_url, {}))["token"]
        auth = {"Authorization": f"Bearer {token}"}
        manifest: Any = json.loads(
            _get(
                opener,
                f"{REGISTRY}/v2/{repository}/manifests/{tag}",
                {**auth, "Accept": MANIFEST_TYPE},
            )
        )
        digest = next(
            str(layer["digest"])
            for layer in manifest["layers"]
            if layer.get("mediaType") == LAYER_TYPE
        )
        if not DIGEST_RE.fullmatch(digest):
            raise ValueError(f"unexpected digest {digest!r}")
        blob = _get(opener, f"{REGISTRY}/v2/{repository}/blobs/{digest}", auth)
        if "sha256:" + hashlib.sha256(blob).hexdigest() != digest:
            raise ValueError("digest mismatch")
        _unpack(blob, dest)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        StopIteration,
        tarfile.TarError,
        urllib.error.URLError,
    ) as exc:
        log(f"no central graph {module}:{tag} ({type(exc).__name__})")
        return False
    log(f"loaded central graph {module}:{tag}")
    return True


def build(root: Path, cache: Path) -> bool:
    """Build a code-only graph into ``cache`` unless another build holds the lock."""
    head = git(root, "rev-parse", "HEAD") or ""
    cache.mkdir(parents=True, exist_ok=True)

    # Platform-compatible file locking
    if fcntl is not None:
        lock_file = (cache / ".lock").open("w")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
        except BlockingIOError:
            lock_file.close()
            return False
    else:
        lock_file = (cache / ".lock").open("w")

    try:
        out = cache / "build"
        # Clear GRAPHIFY_OUT to prevent interference with --out flag
        env = os.environ.copy()
        env.pop("GRAPHIFY_OUT", None)
        with (cache / "build.log").open("w") as build_log:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "graphify",
                    "extract",
                    str(root),
                    "--code-only",
                    "--out",
                    str(out),
                ],
                stdin=subprocess.DEVNULL,
                stdout=build_log,
                stderr=subprocess.STDOUT,
                check=False,
                env=env,
            )
        built = out / "graphify-out" / "graph.json"
        if result.returncode != 0 or not built.exists():
            log(f"local graph build failed, see {cache / 'build.log'}")
            return False
        built.replace(cache / "graph.json")
        (cache / "head").write_text(head, encoding="utf-8")
    finally:
        if fcntl is not None:
            fcntl.flock(lock_file, fcntl.LOCK_UN)  # type: ignore[attr-defined]
        lock_file.close()

    log("local graph build finished")
    return True


def prepare(
    cwd: Path,
    fetcher: Callable[[str, str, Path], bool] = fetch,
    builder: Callable[[Path, Path], bool] = build,
) -> tuple[Path | None, threading.Thread | None]:
    """Return the graph path to serve and the background build, if started."""
    if os.environ.get("SCORE_AGENT_GRAPH", "").lower() in {"0", "off", "false"}:
        return None, None
    root = repo_root(cwd)
    if root is None:
        return None, None
    in_repo = root / "graphify-out" / "graph.json"
    if in_repo.exists():
        return in_repo, None
    cache = cache_dir(root)
    graph = cache / "graph.json"
    module = module_name(root)

    # Seed from registry with locking to prevent race conditions
    if not graph.exists() and module and not os.environ.get("SCORE_AGENT_OFFLINE"):
        lock_file = _acquire_lock(cache)
        if lock_file is not None:
            try:
                # Recheck after acquiring lock (another process may have seeded)
                if not graph.exists():
                    for tag in candidate_tags(root):
                        if fetcher(module, tag, cache):
                            break
            finally:
                _release_lock(lock_file)

    head_file = cache / "head"
    head = git(root, "rev-parse", "HEAD")
    current = head_file.exists() and head_file.read_text(encoding="utf-8") == head
    if current and graph.exists():
        return graph, None
    thread = threading.Thread(target=builder, args=(root, cache), daemon=True)
    thread.start()
    return graph, thread
