# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Tests for the process graph refresh CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from refresh_process_graph import _SOURCE_FILE_HEADER, main, type_deltas

FIXTURE = Path(__file__).parent / "data" / "process_needs_min.json"
SOURCE_COMMIT = "531b538c89849af3807cfaf77a96a49a3225818a"
OBSERVED_AT = "2026-09-14T16:14:00+00:00"


def _refresh_args(repo_root: Path, summary_out: Path) -> list[str]:
    return [
        "--needs",
        str(FIXTURE),
        "--source-commit",
        SOURCE_COMMIT,
        "--repo-root",
        str(repo_root),
        "--observed-at",
        OBSERVED_AT,
        "--summary-out",
        str(summary_out),
    ]


def test_type_deltas_is_sorted_and_omits_unchanged_types() -> None:
    assert type_deltas(
        {"same": 2, "removed": 1, "changed": 2},
        {"same": 2, "added": 3, "changed": 5},
    ) == (("added", 3), ("changed", 3), ("removed", -1))


def test_refresh_missing_artifact_renders_additions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    summary_path = tmp_path / "summary.md"

    assert main([*_refresh_args(tmp_path, summary_path)]) == 0

    summary = summary_path.read_text(encoding="utf-8")
    assert "Source commit: `` → `531b538c89849af3807cfaf77a96a49a3225818a`" in summary
    assert "Total nodes: 0 → 8" in summary
    assert "Total edges: 0 → 10" in summary
    assert "  - +1 gd_req" in summary
    assert "skipped_needs=1, ignored_types=1, skipped_links=2" in summary
    assert "generated and reviewed via this summary" in summary
    assert capsys.readouterr().out == summary


def test_refresh_rewrites_source_metadata_without_machine_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    summary_path = tmp_path / "summary.md"

    assert main([*_refresh_args(tmp_path, summary_path)]) == 0

    source = (
        tmp_path / "packages" / "metamodel-flow" / "model" / "process_source.txt"
    ).read_text(encoding="utf-8")
    assert source.startswith(_SOURCE_FILE_HEADER)
    assert source.endswith("\n")
    assert "/home/ubuntu" not in source
    assert [
        line.split("=", 1)[0]
        for line in source.splitlines()
        if line and not line.startswith("#")
    ] == ["source_repo_url", "source_commit", "generator_command"]
    assert f"source_commit={SOURCE_COMMIT}" in source
    capsys.readouterr()


def test_refresh_is_byte_deterministic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    summary_path = tmp_path / "summary.md"
    args = _refresh_args(tmp_path, summary_path)

    assert main([*args]) == 0
    artifact_path = (
        tmp_path / "packages" / "metamodel-flow" / "model" / "process_graph.json"
    )
    first = artifact_path.read_bytes()
    source_path = (
        tmp_path / "packages" / "metamodel-flow" / "model" / "process_source.txt"
    )
    first_source = source_path.read_bytes()
    capsys.readouterr()

    assert main([*args]) == 0
    second = artifact_path.read_bytes()
    second_source = source_path.read_bytes()
    summary = capsys.readouterr().out

    assert first == second
    assert first_source == second_source
    assert "artefact is already current" in summary


def test_refresh_rewrites_changed_source_commit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    summary_path = tmp_path / "summary.md"
    first_args = _refresh_args(tmp_path, summary_path)

    assert main([*first_args]) == 0
    artifact_path = (
        tmp_path / "packages" / "metamodel-flow" / "model" / "process_graph.json"
    )
    source_path = (
        tmp_path / "packages" / "metamodel-flow" / "model" / "process_source.txt"
    )
    first_artifact = artifact_path.read_bytes()
    first_source = source_path.read_bytes()
    capsys.readouterr()

    second_args = [
        *first_args[:3],
        "different-upstream-commit",
        *first_args[4:],
    ]
    assert main(second_args) == 0
    summary = capsys.readouterr().out

    assert artifact_path.read_bytes() != first_artifact
    assert source_path.read_bytes() != first_source
    assert (
        "Source commit: `531b538c89849af3807cfaf77a96a49a3225818a` "
        "→ `different-upstream-commit`"
    ) in summary
