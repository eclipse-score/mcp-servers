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

import json
from pathlib import Path

import pytest
from sdlc_harness.artifact_writer import write_stage_artifact
from sdlc_harness.implementation_tracking import record_implementation_evidence


def _make_task(stage_dir: str, issue_id: str = "issue-1") -> str:
    path = write_stage_artifact(issue_id, "task", "Task", "Body", stage_dir=stage_dir)[
        "path"
    ]
    return Path(path).name


def test_record_implementation_evidence_rejects_unknown_status(tmp_path: Path) -> None:
    stage_dir = str(tmp_path / ".stage")
    task_id = _make_task(stage_dir)

    with pytest.raises(ValueError):
        record_implementation_evidence(
            "issue-1",
            task_id,
            requirement_ids=[],
            source_files=[],
            tests=[],
            status="done",
            summary="summary",
            stage_dir=stage_dir,
        )


def test_record_implementation_evidence_requires_existing_task_artifact(
    tmp_path: Path,
) -> None:
    stage_dir = str(tmp_path / ".stage")

    with pytest.raises(ValueError):
        record_implementation_evidence(
            "issue-1",
            "task-999.md",
            requirement_ids=[],
            source_files=[],
            tests=[],
            status="completed",
            summary="summary",
            stage_dir=stage_dir,
        )


def test_record_implementation_evidence_replaces_entry_for_same_task_id(
    tmp_path: Path,
) -> None:
    stage_dir = str(tmp_path / ".stage")
    task_id = _make_task(stage_dir)

    record_implementation_evidence(
        "issue-1",
        task_id,
        requirement_ids=["req-1"],
        source_files=["a.py"],
        tests=[{"command": "pytest a", "status": "passed"}],
        status="in_progress",
        summary="first pass",
        stage_dir=stage_dir,
    )
    record_implementation_evidence(
        "issue-1",
        task_id,
        requirement_ids=["req-1", "req-2"],
        source_files=["a.py", "b.py"],
        tests=[{"command": "pytest b", "status": "passed"}],
        status="completed",
        summary="final pass",
        stage_dir=stage_dir,
    )

    evidence_path = (
        Path(stage_dir) / "issue-1" / "harness" / "implementation-evidence.json"
    )
    entries = json.loads(evidence_path.read_text(encoding="utf-8"))["entries"]

    assert len(entries) == 1
    assert entries[0]["status"] == "completed"
    assert entries[0]["summary"] == "final pass"
    assert entries[0]["source_files"] == ["a.py", "b.py"]
