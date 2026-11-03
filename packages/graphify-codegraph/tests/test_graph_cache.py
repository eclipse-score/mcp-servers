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

import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import IO

import graph_cache
import pytest

GRAPH = json.dumps({"nodes": [], "links": []}).encode()


def artifact(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def registry(blob: bytes, digest: str | None = None) -> graph_cache.Opener:
    digest = digest or "sha256:" + hashlib.sha256(blob).hexdigest()
    manifest = {"layers": [{"mediaType": graph_cache.LAYER_TYPE, "digest": digest}]}
    base = f"{graph_cache.REGISTRY}/v2/{graph_cache.NAMESPACE}/baselibs"
    responses = {
        f"{graph_cache.REGISTRY}/token?scope=repository:"
        f"{graph_cache.NAMESPACE}/baselibs:pull": json.dumps({"token": "x"}).encode(),
        f"{base}/manifests/main": json.dumps(manifest).encode(),
        f"{base}/blobs/{digest}": blob,
    }

    def opener(request: urllib.request.Request) -> IO[bytes]:
        url = request.full_url
        if url not in responses:
            raise urllib.error.URLError("not found")
        return io.BytesIO(responses[url])

    return opener


def test_fetch_verifies_and_unpacks(tmp_path: Path) -> None:
    blob = artifact({"./graph.json": GRAPH, "./metadata.json": b"{}"})
    assert graph_cache.fetch("baselibs", "main", tmp_path, registry(blob))
    assert (tmp_path / "graph.json").read_bytes() == GRAPH
    assert (tmp_path / "metadata.json").exists()
    provenance = json.loads((tmp_path / "registry.json").read_text())
    assert provenance["tag"] == "main"
    assert provenance["digest"] == "sha256:" + hashlib.sha256(blob).hexdigest()


def test_fetch_rejects_digest_mismatch(tmp_path: Path) -> None:
    blob = artifact({"graph.json": GRAPH})
    wrong = "sha256:" + "0" * 64
    assert not graph_cache.fetch("baselibs", "main", tmp_path, registry(blob, wrong))
    assert not (tmp_path / "graph.json").exists()


def test_fetch_ignores_unexpected_members(tmp_path: Path) -> None:
    blob = artifact({"graph.json": GRAPH, "../evil.json": b"x", "sub/graph.json": b"x"})
    assert graph_cache.fetch("baselibs", "main", tmp_path / "cache", registry(blob))
    assert sorted(p.name for p in (tmp_path / "cache").iterdir()) == [
        "graph.json",
        "registry.json",
    ]
    assert not (tmp_path / "evil.json").exists()


@pytest.mark.parametrize(("module", "tag"), [("baselibs", "../x"), ("a/b", "main")])
def test_fetch_rejects_bad_names(tmp_path: Path, module: str, tag: str) -> None:
    assert not graph_cache.fetch(module, tag, tmp_path, registry(b""))


def test_fetch_missing_artifact(tmp_path: Path) -> None:
    assert not graph_cache.fetch("baselibs", "abc", tmp_path, registry(b""))


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.delenv("SCORE_AGENT_GRAPH", raising=False)
    monkeypatch.delenv("SCORE_AGENT_OFFLINE", raising=False)
    root = tmp_path / "baselibs"
    root.mkdir()
    git(root, "init", "-q")
    git(
        root, "remote", "add", "origin", "https://github.com/eclipse-score/baselibs.git"
    )
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    git(root, "add", "-A")
    git(
        root,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.invalid",
        "commit",
        "-qm",
        "c",
    )
    return root


def test_module_name(repo: Path) -> None:
    assert graph_cache.module_name(repo) == "baselibs"
    git(repo, "remote", "set-url", "origin", "git@github.com:other/baselibs.git")
    assert graph_cache.module_name(repo) is None


def test_prepare_uses_registry_without_building(repo: Path) -> None:
    fetched: list[str] = []
    built: list[Path] = []

    def fetcher(module: str, tag: str, dest: Path) -> bool:
        fetched.append(f"{module}:{tag}")
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "graph.json").write_bytes(GRAPH)
        return True

    def builder(root: Path, cache: Path) -> bool:
        built.append(root)
        return True

    graph, thread = graph_cache.prepare(repo, fetcher, builder)
    assert thread is None
    assert graph == graph_cache.cache_dir(repo) / "graph.json"
    assert fetched == ["baselibs:main"]
    assert built == []
    assert not (repo / "graphify-out").exists()


def test_prepare_skips_build_when_current(repo: Path) -> None:
    cache = graph_cache.cache_dir(repo)
    cache.mkdir(parents=True)
    (cache / "graph.json").write_bytes(GRAPH)
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    (cache / "head").write_text(head, encoding="utf-8")
    (cache / "registry.json").write_text("{}", encoding="utf-8")

    def fail(*_: object) -> bool:
        raise AssertionError("must not be called")

    assert graph_cache.prepare(repo, fail, fail) == (cache / "graph.json", None)


def test_prepare_falls_back_to_graph_in_repo(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SCORE_AGENT_OFFLINE", "1")
    (repo / "graphify-out").mkdir()
    (repo / "graphify-out" / "graph.json").write_bytes(GRAPH)
    graph, thread = graph_cache.prepare(repo)
    assert graph == repo / "graphify-out" / "graph.json"
    assert thread is None


def test_prepare_disabled(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCORE_AGENT_GRAPH", "off")
    assert graph_cache.prepare(repo) == (None, None)


def test_prepare_upgrades_local_graph_without_rebuilding(repo: Path) -> None:
    cache = graph_cache.cache_dir(repo)
    cache.mkdir(parents=True)
    (cache / "graph.json").write_bytes(GRAPH)
    (repo / "graphify-out").mkdir()
    (repo / "graphify-out" / "graph.json").write_bytes(GRAPH)

    def fetcher(module: str, tag: str, dest: Path) -> bool:
        (dest / "registry.json").write_text('{"tag": "main"}')
        return True

    def forbidden_builder(root: Path, dest: Path) -> bool:
        raise AssertionError("prebuilt graph must not be rebuilt")

    graph, thread = graph_cache.prepare(repo, fetcher, forbidden_builder)
    assert graph == cache / "graph.json"
    assert thread is None
    assert graph_cache.resolve_graph_path(repo) == graph


def test_prepare_rechecks_prebuilt_after_one_day(repo: Path) -> None:
    cache = graph_cache.cache_dir(repo)
    cache.mkdir(parents=True)
    (cache / "graph.json").write_bytes(GRAPH)
    provenance = cache / "registry.json"
    provenance.write_text("{}")
    old = time.time() - 25 * 60 * 60
    os.utime(provenance, (old, old))
    fetched: list[str] = []

    def fetcher(module: str, tag: str, dest: Path) -> bool:
        fetched.append(tag)
        return True

    graph, thread = graph_cache.prepare(repo, fetcher)
    assert fetched == ["main"]
    assert graph == cache / "graph.json"
    assert thread is None


def test_prepare_reuses_cache_when_download_fails(repo: Path) -> None:
    cache = graph_cache.cache_dir(repo)
    cache.mkdir(parents=True)
    (cache / "graph.json").write_bytes(GRAPH)

    def unavailable(module: str, tag: str, dest: Path) -> bool:
        return False

    def forbidden_builder(root: Path, dest: Path) -> bool:
        raise AssertionError("usable cache must not be rebuilt")

    assert graph_cache.prepare(repo, unavailable, forbidden_builder) == (
        cache / "graph.json",
        None,
    )


def test_prepare_builds_only_when_no_graph_is_available(repo: Path) -> None:
    built: list[Path] = []

    def unavailable(module: str, tag: str, dest: Path) -> bool:
        return False

    def builder(root: Path, dest: Path) -> bool:
        built.append(root)
        (dest / "graph.json").write_bytes(GRAPH)
        return True

    graph, thread = graph_cache.prepare(repo, unavailable, builder)
    assert thread is not None
    thread.join()
    assert built == [repo]
    assert graph is not None and graph.exists()


def test_prepare_force_local_bypasses_prebuilt(repo: Path) -> None:
    cache = graph_cache.cache_dir(repo)
    cache.mkdir(parents=True)
    (cache / "graph.json").write_bytes(GRAPH)
    (cache / "registry.json").write_text("{}")
    built: list[Path] = []

    def forbidden_fetch(module: str, tag: str, dest: Path) -> bool:
        raise AssertionError("explicit local refresh must not download")

    def builder(root: Path, dest: Path) -> bool:
        built.append(root)
        return True

    _, thread = graph_cache.prepare(repo, forbidden_fetch, builder, force_local=True)
    assert thread is not None
    thread.join()
    assert built == [repo]


def test_prepare_only_reports_prebuilt_provenance(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import serve

    cache = graph_cache.cache_dir(repo)
    cache.mkdir(parents=True)
    (cache / "graph.json").write_bytes(GRAPH)
    (cache / "registry.json").write_text('{"tag": "main"}')
    monkeypatch.setattr(
        sys, "argv", ["graphify-codegraph", "--prepare-only", "--repo-path", str(repo)]
    )
    serve.main()
    result = json.loads(capsys.readouterr().out)
    assert result["ok"]
    assert result["source"] == "prebuilt"
    assert result["provenance"]["tag"] == "main"


def test_prepare_only_reports_failed_local_refresh(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import serve

    cache = graph_cache.cache_dir(repo)
    cache.mkdir(parents=True)
    (cache / "graph.json").write_bytes(GRAPH)
    (cache / "registry.json").write_text('{"tag": "main"}')

    def failed_build(root: Path, dest: Path) -> bool:
        return False

    monkeypatch.setattr(serve, "build", failed_build)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "graphify-codegraph",
            "--prepare-only",
            "--repo-path",
            str(repo),
            "--force-local",
        ],
    )
    serve.main()
    result = json.loads(capsys.readouterr().out)
    assert not result["ok"]
    assert (cache / "graph.json").read_bytes() == GRAPH


def test_build_writes_only_to_cache(repo: Path, tmp_path: Path) -> None:
    pytest.importorskip("graphify")
    cache = tmp_path / "cache"
    assert graph_cache.build(repo, cache)
    assert json.loads((cache / "graph.json").read_text(encoding="utf-8"))
    assert (cache / "head").exists()
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    assert status.stdout == ""


def test_resolve_graph_path_prefers_in_repo(repo: Path) -> None:
    """resolve_graph_path should find in-repo graph first."""
    (repo / "graphify-out").mkdir()
    (repo / "graphify-out" / "graph.json").write_bytes(GRAPH)

    result = graph_cache.resolve_graph_path(repo)
    assert result == repo / "graphify-out" / "graph.json"


def test_resolve_graph_path_falls_back_to_cache(repo: Path) -> None:
    """resolve_graph_path should check user cache when in-repo graph missing."""
    cache = graph_cache.cache_dir(repo)
    cache.mkdir(parents=True)
    (cache / "graph.json").write_bytes(GRAPH)

    result = graph_cache.resolve_graph_path(repo)
    assert result == cache / "graph.json"


def test_resolve_graph_path_returns_none_when_missing(repo: Path) -> None:
    """resolve_graph_path should return None when no graph exists."""
    result = graph_cache.resolve_graph_path(repo)
    assert result is None


def test_resolve_graph_path_respects_disabled(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """resolve_graph_path should respect SCORE_AGENT_GRAPH=off."""
    monkeypatch.setenv("SCORE_AGENT_GRAPH", "off")
    (repo / "graphify-out").mkdir()
    (repo / "graphify-out" / "graph.json").write_bytes(GRAPH)

    result = graph_cache.resolve_graph_path(repo)
    assert result is None


def test_resolve_graph_path_returns_none_outside_git(tmp_path: Path) -> None:
    """resolve_graph_path should return None outside a git repository."""
    not_a_repo = tmp_path / "notarepo"
    not_a_repo.mkdir()

    result = graph_cache.resolve_graph_path(not_a_repo)
    assert result is None


def test_build_clears_graphify_out_env(
    tmp_path: Path, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """build should not inherit GRAPHIFY_OUT from environment."""
    pytest.importorskip("graphify")
    # Set a potentially interfering GRAPHIFY_OUT
    monkeypatch.setenv("GRAPHIFY_OUT", "wrong-output-dir")

    cache = tmp_path / "cache"
    assert graph_cache.build(repo, cache)
    # Graph should be in cache, not in wrong-output-dir
    assert (cache / "graph.json").exists()
    assert not (repo / "wrong-output-dir").exists()


def test_prepare_locking_prevents_race_condition(repo: Path, tmp_path: Path) -> None:
    """prepare should lock during seeding to prevent race conditions."""
    # Simulate a race: first call starts, second call should skip seeding
    seeded: list[str] = []

    def fake_fetch(module: str, tag: str, dest: Path) -> bool:
        seeded.append(f"{module}:{tag}")
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "graph.json").write_bytes(GRAPH)
        (dest / "registry.json").write_text("{}", encoding="utf-8")
        return True

    def fake_builder(root: Path, cache: Path) -> bool:
        return True

    # First call should seed
    _, thread1 = graph_cache.prepare(repo, fake_fetch, fake_builder)
    thread1.join() if thread1 else None

    # Second call should find graph already exists (no re-seed)
    seeded.clear()
    _, thread2 = graph_cache.prepare(repo, fake_fetch, fake_builder)
    thread2.join() if thread2 else None

    # Second call should not have seeded (graph already exists)
    assert seeded == []
