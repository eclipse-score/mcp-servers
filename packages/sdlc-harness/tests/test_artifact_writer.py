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

from pathlib import Path

import pytest
from sdlc_harness.artifact_writer import (
    check_stage_completeness,
    issue_directory,
    write_stage_artifact,
)


@pytest.mark.parametrize(
    "issue_id",
    ["", ".", "..", "../escape", "a/b", "/abs", "a/../b"],
)
def test_issue_directory_rejects_path_traversal(issue_id: str) -> None:
    with pytest.raises(ValueError):
        issue_directory(issue_id)


def test_issue_directory_accepts_plain_name(tmp_path: Path) -> None:
    stage_dir = str(tmp_path / ".stage")
    assert issue_directory("issue-123", stage_dir) == Path(stage_dir) / "issue-123"


def test_check_stage_completeness_specification_reports_missing_requirement(
    tmp_path: Path,
) -> None:
    stage_dir = str(tmp_path / ".stage")

    result = check_stage_completeness("issue-1", "specification", stage_dir)

    assert result == {
        "ok": False,
        "complete": False,
        "missing": ["01-requirement.md"],
    }


def test_check_stage_completeness_architecture_reports_missing_specification(
    tmp_path: Path,
) -> None:
    stage_dir = str(tmp_path / ".stage")
    write_stage_artifact("issue-1", "requirement", "Title", "Body", stage_dir=stage_dir)

    result = check_stage_completeness("issue-1", "architecture", stage_dir)

    assert result == {
        "ok": False,
        "complete": False,
        "missing": ["02-specification.md"],
    }


def test_check_stage_completeness_plan_reports_missing_architecture(
    tmp_path: Path,
) -> None:
    stage_dir = str(tmp_path / ".stage")
    write_stage_artifact("issue-1", "requirement", "Title", "Body", stage_dir=stage_dir)
    write_stage_artifact(
        "issue-1", "specification", "Title", "Body", stage_dir=stage_dir
    )

    result = check_stage_completeness("issue-1", "plan", stage_dir)

    assert result == {
        "ok": False,
        "complete": False,
        "missing": ["03-architecture.md"],
    }


def test_check_stage_completeness_implementation_reports_missing_tasks_directory(
    tmp_path: Path,
) -> None:
    stage_dir = str(tmp_path / ".stage")
    for artifact_type in ("requirement", "specification", "architecture", "plan"):
        write_stage_artifact(
            "issue-1", artifact_type, "Title", "Body", stage_dir=stage_dir
        )

    result = check_stage_completeness("issue-1", "implementation", stage_dir)

    assert result == {
        "ok": False,
        "complete": False,
        "missing": ["05-tasks/"],
    }


def test_check_stage_completeness_review_reports_missing_evidence(
    tmp_path: Path,
) -> None:
    stage_dir = str(tmp_path / ".stage")
    for artifact_type in ("requirement", "specification", "architecture", "plan"):
        write_stage_artifact(
            "issue-1", artifact_type, "Title", "Body", stage_dir=stage_dir
        )
    write_stage_artifact("issue-1", "task", "Task", "Body", stage_dir=stage_dir)

    result = check_stage_completeness("issue-1", "review", stage_dir)

    assert result == {
        "ok": False,
        "complete": False,
        "missing": ["harness/implementation-evidence.json"],
    }


def test_check_stage_completeness_review_complete_when_all_present(
    tmp_path: Path,
) -> None:
    stage_dir = str(tmp_path / ".stage")
    for artifact_type in ("requirement", "specification", "architecture", "plan"):
        write_stage_artifact(
            "issue-1", artifact_type, "Title", "Body", stage_dir=stage_dir
        )
    write_stage_artifact("issue-1", "task", "Task", "Body", stage_dir=stage_dir)
    evidence_path = (
        Path(stage_dir) / "issue-1" / "harness" / "implementation-evidence.json"
    )
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text("{}", encoding="utf-8")

    result = check_stage_completeness("issue-1", "review", stage_dir)

    assert result == {"ok": True, "complete": True, "missing": []}


def test_check_stage_completeness_rejects_unknown_stage(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        check_stage_completeness("issue-1", "unknown-stage", str(tmp_path / ".stage"))
