# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Tests for the metamodel data exporter."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import export_metamodel_data as exporter
import pytest

SOURCE_COMMIT = "e537c617cb1805cdef39cf5b93e9f2e8810aabcb"
MODEL_DATA = Path(__file__).parents[1] / "model" / "metamodel-data.json"

MINIMAL_METAMODEL = """\
needs_types_base_options:
  mandatory_options:
    id: "^[a-z_]+__[a-z0-9_]+$"
  optional_options:
    status: "^(valid|draft)$"
needs_types:
  comp_req:
    title: Component Requirement
    prefix: comp_req__
    tags: [requirement]
    parts: 2
    mandatory_options:
      version: "^[0-9]+$"
    optional_options:
      safety: "^(QM|ASIL_B)$"
    mandatory_links:
      satisfies: feat_req
    optional_links:
      mitigated_by: ANY
  feat_req:
    title: Feature Requirement
    prefix: feat_req__
    parts: 2
needs_extra_links:
  satisfies:
    outgoing: satisfies
    incoming: satisfied by
prohibited_words_checks:
  no_weasel:
    types: [comp_req]
    forbidden: [should, might]
graph_checks:
  qm_only:
    needs:
      include: comp_req
      condition: safety == QM
    check:
      fulfils: safety != QM
    explanation: A QM element cannot implement ASIL requirements.
"""


@pytest.fixture
def metamodel_path(tmp_path: Path) -> Path:
    path = tmp_path / "metamodel.yaml"
    path.write_text(MINIMAL_METAMODEL, encoding="utf-8")
    return path


def _export(path: Path) -> dict[str, Any]:
    data = exporter.load_metamodel_yaml(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return exporter.build_metamodel_data(data, digest, SOURCE_COMMIT)


def test_builds_expected_sections(metamodel_path: Path) -> None:
    data = _export(metamodel_path)

    assert list(data) == [
        "$schema",
        "schema_version",
        "metamodel_digest",
        "source",
        "base_options",
        "prohibited_words",
        "link_types",
        "need_types",
        "graph_rules",
    ]
    assert data["schema_version"] == 1
    assert data["source"] == {
        "repo_url": "https://github.com/eclipse-score/docs-as-code.git",
        "commit": SOURCE_COMMIT,
    }


def test_need_type_options_merge_base_and_type_options(metamodel_path: Path) -> None:
    data = _export(metamodel_path)
    need_types = {item["name"]: item for item in data["need_types"]}

    options = {option["name"]: option for option in need_types["comp_req"]["options"]}
    assert options["id"] == {
        "name": "id",
        "pattern": "^[a-z_]+__[a-z0-9_]+$",
        "required": True,
        "inherited": True,
    }
    assert options["status"]["required"] is False
    assert options["version"]["inherited"] is False
    assert need_types["comp_req"]["links"] == [
        {"name": "mitigated_by", "targets": [], "any_target": True, "required": False},
        {
            "name": "satisfies",
            "targets": ["feat_req"],
            "any_target": False,
            "required": True,
        },
    ]


def test_link_types_and_graph_rules(metamodel_path: Path) -> None:
    data = _export(metamodel_path)

    assert data["link_types"] == [
        {
            "name": "mitigated_by",
            "outgoing": None,
            "incoming": None,
            "declared": False,
        },
        {
            "name": "satisfies",
            "outgoing": "satisfies",
            "incoming": "satisfied by",
            "declared": True,
        },
    ]
    assert data["graph_rules"] == [
        {
            "name": "qm_only",
            "applies_to": ["comp_req"],
            "condition_raw": "safety == QM",
            "check_raw": {"fulfils": "safety != QM"},
            "explanation": "A QM element cannot implement ASIL requirements.",
        }
    ]


def test_export_is_deterministic(metamodel_path: Path) -> None:
    first = exporter.render_data(_export(metamodel_path))
    second = exporter.render_data(_export(metamodel_path))

    assert first == second
    assert first.endswith("\n")


def test_main_writes_output_with_explicit_source_commit(
    metamodel_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "model" / "metamodel-data.json"

    assert (
        exporter.main(
            [
                "--metamodel",
                str(metamodel_path),
                "--output",
                str(output),
                "--source-commit",
                SOURCE_COMMIT,
            ]
        )
        == 0
    )

    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["source"]["commit"] == SOURCE_COMMIT
    assert str(output) in capsys.readouterr().out


def test_main_rejects_missing_metamodel(tmp_path: Path) -> None:
    assert (
        exporter.main(
            [
                "--metamodel",
                str(tmp_path / "absent.yaml"),
                "--output",
                str(tmp_path / "out.json"),
                "--source-commit",
                SOURCE_COMMIT,
            ]
        )
        == 1
    )
    assert not (tmp_path / "out.json").exists()


def test_committed_model_records_a_full_source_commit() -> None:
    data = json.loads(MODEL_DATA.read_text(encoding="utf-8"))

    assert re.fullmatch(r"[0-9a-f]{40}", data["source"]["commit"])
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", data["metamodel_digest"])
