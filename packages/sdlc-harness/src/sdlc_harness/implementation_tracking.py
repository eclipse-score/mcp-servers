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

"""Record and report implementation evidence for SDLC stage artifacts."""

import json
from pathlib import Path
from typing import Any

from .artifact_writer import issue_directory

EVIDENCE_FILENAME = "implementation-evidence.json"
VALID_STATUSES = {"completed", "blocked", "failed", "in_progress"}


def record_implementation_evidence(
    issue_id: str,
    task_id: str,
    requirement_ids: list[str],
    source_files: list[str],
    tests: list[dict[str, str]],
    status: str,
    summary: str,
    stage_dir: str = ".stage",
) -> dict[str, Any]:
    """Store or replace one task's implementation evidence."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Unknown implementation status: {status}")

    issue_dir = issue_directory(issue_id, stage_dir)
    task_path = issue_dir / "05-tasks" / task_id
    if not task_path.is_file():
        raise ValueError(f"Task artifact not found: {task_path}")

    evidence_path = issue_dir / "harness" / EVIDENCE_FILENAME
    evidence = _read_evidence(evidence_path)
    entry = {
        "task_id": task_id,
        "requirement_ids": requirement_ids,
        "source_files": source_files,
        "tests": tests,
        "status": status,
        "summary": summary,
    }
    entries = [item for item in evidence["entries"] if item["task_id"] != task_id]
    entries.append(entry)
    evidence["entries"] = sorted(entries, key=lambda item: item["task_id"])
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(evidence_path), "entry": entry}


def assess_implementation_progress(
    issue_id: str, stage_dir: str = ".stage"
) -> dict[str, Any]:
    """Summarize task, file, requirement, and test evidence for an issue."""
    issue_dir = issue_directory(issue_id, stage_dir)
    tasks = sorted(path.name for path in (issue_dir / "05-tasks").glob("task-*.md"))
    evidence = _read_evidence(issue_dir / "harness" / EVIDENCE_FILENAME)["entries"]
    evidence_by_task = {entry["task_id"]: entry for entry in evidence}
    completed_tasks = [
        task_id
        for task_id in tasks
        if evidence_by_task.get(task_id, {}).get("status") == "completed"
    ]
    linked_files = sorted(
        {source_file for entry in evidence for source_file in entry["source_files"]}
    )
    linked_requirements = sorted(
        {
            requirement_id
            for entry in evidence
            for requirement_id in entry["requirement_ids"]
        }
    )
    tests = [test for entry in evidence for test in entry["tests"]]
    passed_tests = [test for test in tests if test.get("status") == "passed"]
    failures = _progress_findings(tasks, evidence_by_task, evidence, tests)
    total_tasks = len(tasks)
    return {
        "ok": not failures,
        "issue_id": issue_id,
        "tasks": {
            "total": total_tasks,
            "completed": len(completed_tasks),
            "percentage": _percentage(len(completed_tasks), total_tasks),
            "without_evidence": [
                task for task in tasks if task not in evidence_by_task
            ],
        },
        "requirements": {
            "linked": linked_requirements,
            "count": len(linked_requirements),
        },
        "source_files": {"linked": linked_files, "count": len(linked_files)},
        "tests": {"total": len(tests), "passed": len(passed_tests), "results": tests},
        "findings": failures,
    }


def write_sphinx_progress_report(
    issue_id: str, report_path: str, stage_dir: str = ".stage"
) -> dict[str, str]:
    """Write an RST report with a progress table and sphinx-needs flow directive."""
    progress = assess_implementation_progress(issue_id, stage_dir)
    report = Path(report_path)
    report.parent.mkdir(parents=True, exist_ok=True)
    task_lines = _task_table_lines(issue_id, progress, stage_dir)
    requirement_ids = progress["requirements"]["linked"]
    need_filter = " or ".join(f"id == '{need_id}'" for need_id in requirement_ids)
    report.write_text(
        ".. SPDX-License-Identifier: Apache-2.0\n\n"
        f"{issue_id} Implementation Progress\n"
        f"{'=' * (len(issue_id) + 24)}\n\n"
        "Task completion: "
        f"{progress['tasks']['completed']}/{progress['tasks']['total']} "
        f"({progress['tasks']['percentage']}%).\n\n"
        ".. list-table:: Implementation evidence\n"
        "   :header-rows: 1\n\n"
        "   * - Task\n"
        "     - Status\n"
        "     - Source files\n"
        "     - Tests\n"
        f"{task_lines}\n"
        ".. needflow:: Requirement implementation trace\n"
        "\n"
        f"   :filter: {need_filter or 'False'}\n",
        encoding="utf-8",
    )
    return {"ok": "true", "path": str(report)}


def _read_evidence(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.is_file():
        return {"entries": []}
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"Invalid implementation evidence: {path}")
    return {"entries": entries}


def _progress_findings(
    tasks: list[str],
    evidence_by_task: dict[str, dict[str, Any]],
    evidence: list[dict[str, Any]],
    tests: list[dict[str, str]],
) -> list[str]:
    findings = [
        f"Task has no evidence: {task}"
        for task in tasks
        if task not in evidence_by_task
    ]
    findings.extend(
        f"Task is not completed: {entry['task_id']} ({entry['status']})"
        for entry in evidence
        if entry["status"] != "completed"
    )
    findings.extend(
        f"Test did not pass: {test.get('command', '<unnamed>')}"
        for test in tests
        if test.get("status") != "passed"
    )
    return findings


def _percentage(completed: int, total: int) -> int:
    return round(completed / total * 100) if total else 0


def _task_table_lines(issue_id: str, progress: dict[str, Any], stage_dir: str) -> str:
    issue_dir = issue_directory(issue_id, stage_dir)
    evidence = _read_evidence(issue_dir / "harness" / EVIDENCE_FILENAME)["entries"]
    evidence_by_task = {entry["task_id"]: entry for entry in evidence}
    lines: list[str] = []
    for task_id in sorted(evidence_by_task):
        entry = evidence_by_task[task_id]
        files = ", ".join(entry["source_files"]) or "-"
        tests = ", ".join(test.get("command", "-") for test in entry["tests"]) or "-"
        lines.extend(
            [
                f"   * - {task_id}",
                f"     - {entry['status']}",
                f"     - {files}",
                f"     - {tests}",
            ]
        )
    return "\n".join(lines)
