# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Tests for refreshing the committed projection from docs-as-code."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import refresh_model
from agent_context import AgentContextValidationError, load_agent_context
from generate_agent_context import project_metamodel, render_projection

DATA = Path(__file__).parent / "data"
PACKAGE_ROOT = Path(__file__).parents[1]
SHA = "a" * 40


def _valid_model(tmp_path: Path) -> Path:
    text = (DATA / "simple_model.yaml").read_text(encoding="utf-8")
    text = text.replace(
        "    check_all:\n      link1: opt1 == test\n",
        "    check_all:\n      link1: opt1 == test\n"
        "    explanation: Link must be valid.\n",
    )
    path = tmp_path / "metamodel.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def _package(tmp_path: Path) -> Path:
    root = tmp_path / "metamodel-flow"
    shutil.copytree(PACKAGE_ROOT / "model", root / "model")
    return root


def _fetcher(path: Path) -> refresh_model.Fetcher:
    def fetch(url: str) -> bytes:
        assert url == refresh_model.RAW_URL.format(
            sha=SHA, path=refresh_model.METAMODEL_PATH
        )
        return path.read_bytes()

    return fetch


def test_refresh_writes_model_source_and_instructions(tmp_path: Path) -> None:
    root = _package(tmp_path)

    source = _valid_model(tmp_path)

    changed = refresh_model.refresh(SHA, package_root=root, fetcher=_fetcher(source))

    assert changed
    model = root / "model" / "agent_context.json"
    assert model.read_text(encoding="utf-8") == render_projection(
        project_metamodel(source.read_bytes())
    )
    load_agent_context(model)
    assert f"source_commit={SHA}\n" in (root / "model" / "source.txt").read_text(
        encoding="utf-8"
    )
    instructions = (
        root / ".apm" / "instructions" / "score-artifact-model.instructions.md"
    )
    assert instructions.is_file()


def test_check_reports_drift_without_writing(tmp_path: Path) -> None:
    root = _package(tmp_path)
    before = (root / "model" / "agent_context.json").read_bytes()

    changed = refresh_model.refresh(
        SHA,
        package_root=root,
        check=True,
        fetcher=_fetcher(_valid_model(tmp_path)),
    )

    assert changed
    assert (root / "model" / "agent_context.json").read_bytes() == before
    assert not (root / ".apm").exists()


def test_check_ignores_digest_only_changes(tmp_path: Path) -> None:
    root = _package(tmp_path)
    fetcher = _fetcher(_valid_model(tmp_path))
    refresh_model.refresh(SHA, package_root=root, fetcher=fetcher)
    model = root / "model" / "agent_context.json"
    payload = json.loads(model.read_text(encoding="utf-8"))
    payload["metamodel_digest"] = "sha256:" + "0" * 64
    model.write_text(json.dumps(payload), encoding="utf-8")

    assert not refresh_model.refresh(
        SHA, package_root=root, check=True, fetcher=fetcher
    )


def test_invalid_projection_is_not_written(tmp_path: Path) -> None:
    root = _package(tmp_path)
    before = (root / "model" / "agent_context.json").read_bytes()

    with pytest.raises(AgentContextValidationError):
        refresh_model.refresh(
            SHA, package_root=root, fetcher=_fetcher(DATA / "simple_model.yaml")
        )

    assert (root / "model" / "agent_context.json").read_bytes() == before


def test_oversized_metamodel_is_rejected() -> None:
    def fetch(url: str) -> bytes:
        return b"x" * (refresh_model.MAX_BYTES + 1)

    with pytest.raises(ValueError, match="exceeds"):
        refresh_model.fetch_metamodel(SHA, fetch)


@pytest.mark.parametrize("ref", ["", "-x", "a..b", "main;rm", "x" * 200])
def test_invalid_refs_are_rejected(ref: str) -> None:
    with pytest.raises(ValueError):
        refresh_model.resolve_ref(ref)


def test_full_sha_is_used_without_lookup() -> None:
    assert refresh_model.resolve_ref(SHA) == SHA


def test_invalid_commit_is_not_fetched() -> None:
    with pytest.raises(ValueError):
        refresh_model.fetch_metamodel("main", _fetcher(DATA / "simple_model.yaml"))


@pytest.mark.parametrize("raw", [b"", b"- a\n- b\n"])
def test_refresh_rejects_non_mapping_root_without_writing(
    tmp_path: Path, raw: bytes
) -> None:
    root = _package(tmp_path)
    model = root / "model" / "agent_context.json"
    before = model.read_bytes()
    source = tmp_path / "metamodel.yaml"
    source.write_bytes(raw)

    with pytest.raises(ValueError, match="root must be a mapping"):
        refresh_model.refresh(SHA, package_root=root, fetcher=_fetcher(source))

    assert model.read_bytes() == before
    assert not (root / ".apm").exists()


def test_check_reports_drift_when_only_a_graph_check_changes(tmp_path: Path) -> None:
    root = _package(tmp_path)
    source = _valid_model(tmp_path)
    refresh_model.refresh(SHA, package_root=root, fetcher=_fetcher(source))
    assert not refresh_model.refresh(
        SHA, package_root=root, check=True, fetcher=_fetcher(source)
    )

    text = source.read_text(encoding="utf-8")
    source.write_text(
        text.replace("      link1: opt1 == test\n", "      link1: opt1 == other\n"),
        encoding="utf-8",
    )

    assert refresh_model.refresh(
        SHA, package_root=root, check=True, fetcher=_fetcher(source)
    )
