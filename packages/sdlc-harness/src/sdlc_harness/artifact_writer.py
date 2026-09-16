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

"""Create and validate deterministic SDLC stage artifacts."""

import re
from pathlib import Path
from typing import Any

ARTIFACT_PATHS = {
    "requirement": "01-requirement.md",
    "specification": "02-specification.md",
    "architecture": "03-architecture.md",
    "plan": "04-plan.yaml",
}
STAGE_REQUIREMENTS = {
    "specification": ["01-requirement.md"],
    "architecture": ["01-requirement.md", "02-specification.md"],
    "plan": ["01-requirement.md", "02-specification.md", "03-architecture.md"],
    "implementation": [
        "01-requirement.md",
        "02-specification.md",
        "03-architecture.md",
        "04-plan.yaml",
        "05-tasks/",
    ],
    "review": [
        "01-requirement.md",
        "02-specification.md",
        "03-architecture.md",
        "04-plan.yaml",
        "05-tasks/",
        "harness/run.json",
    ],
}
_SPDX_TAG = "SPDX-License-Identifier"
SPDX_MARKDOWN = f"<!-- {_SPDX_TAG}: Apache-2.0 -->\n"


def issue_directory(issue_id: str, stage_dir: str = ".stage") -> Path:
    """Return the stage directory for an issue, rejecting path traversal."""
    issue_path = Path(issue_id)
    if issue_path.name != issue_id or issue_id in {"", ".", ".."}:
        raise ValueError("issue_id must be a single directory name")
    return Path(stage_dir) / issue_id


def write_stage_artifact(
    issue_id: str,
    artifact_type: str,
    title: str,
    content: str,
    links: dict[str, Any] | None = None,
    stage_dir: str = ".stage",
) -> dict[str, str]:
    """Write a stage artifact with SPDX and traceability frontmatter."""
    issue_dir = issue_directory(issue_id, stage_dir)
    path = _artifact_path(issue_dir, artifact_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    if artifact_type == "plan":
        document = _yaml_document(title, content, links or {})
    else:
        document = _markdown_document(title, content, links or {})
    path.write_text(document, encoding="utf-8")
    return {"ok": "true", "path": str(path)}


def check_stage_completeness(
    issue_id: str, stage: str, stage_dir: str = ".stage"
) -> dict[str, Any]:
    """Report whether the prerequisite artifacts for an SDLC stage are present."""
    if stage not in STAGE_REQUIREMENTS:
        raise ValueError(f"Unknown SDLC stage: {stage}")
    issue_dir = issue_directory(issue_id, stage_dir)
    missing: list[str] = []
    for required_path in STAGE_REQUIREMENTS[stage]:
        path = issue_dir / required_path.rstrip("/")
        if required_path.endswith("/"):
            if not path.is_dir() or not any(path.iterdir()):
                missing.append(required_path)
        elif not path.is_file():
            missing.append(required_path)
    complete = not missing
    return {"ok": complete, "complete": complete, "missing": missing}


def bootstrap_sdlc_issue(
    issue_id: str, title: str, requirement: str, stage_dir: str = ".stage"
) -> dict[str, Any]:
    """Create a complete, review-marked SDLC draft from one requirement."""
    issue_dir = issue_directory(issue_id, stage_dir)
    if issue_dir.exists() and any(issue_dir.iterdir()):
        raise ValueError(f"Stage directory is not empty: {issue_dir}")

    drafts = [
        (
            "requirement",
            title,
            requirement,
            {"issue": issue_id},
        ),
        (
            "specification",
            f"{title} specification",
            _specification_draft(requirement),
            {"satisfies": issue_id},
        ),
        (
            "architecture",
            f"{title} architecture",
            _architecture_draft(requirement),
            {"implements": issue_id},
        ),
        (
            "plan",
            f"{title} implementation plan",
            _plan_draft(),
            {"implements": issue_id},
        ),
        (
            "task",
            "Inspect existing implementation",
            _task_one_draft(),
            {"implements": issue_id},
        ),
        (
            "task",
            "Implement approved behavior",
            _task_two_draft(),
            {"implements": issue_id},
        ),
        (
            "task",
            "Verify approved behavior",
            _task_three_draft(),
            {"implements": issue_id},
        ),
    ]
    paths = [
        write_stage_artifact(
            issue_id, artifact_type, artifact_title, content, links, stage_dir
        )["path"]
        for artifact_type, artifact_title, content, links in drafts
    ]
    return {
        "ok": True,
        "issue_id": issue_id,
        "paths": paths,
        "next": (
            "Review and replace every [DRAFT] section using repository evidence "
            "before implementation."
        ),
    }


def assess_sdlc_issue(issue_id: str, stage_dir: str = ".stage") -> dict[str, Any]:
    """Assess whether SDLC drafts contain required analysis, not just files."""
    issue_dir = issue_directory(issue_id, stage_dir)
    requirement = _read_artifact(issue_dir / "01-requirement.md")
    specification = _read_artifact(issue_dir / "02-specification.md")
    architecture = _read_artifact(issue_dir / "03-architecture.md")
    plan = _read_artifact(issue_dir / "04-plan.yaml")
    tasks = _read_task_artifacts(issue_dir / "05-tasks")
    downstream = "\n".join([specification, architecture, plan, *tasks])
    dependencies = sorted(set(re.findall(r"(?<!\w)#\d+\b", requirement)))

    assessment = {
        "requirement": _artifact_status(requirement),
        "specification": _artifact_status(specification),
        "architecture": _artifact_status(architecture),
        "dependency_analysis": _dependency_status(dependencies, downstream),
        "repository_evidence": _evidence_status(downstream),
        "implementation_plan": _artifact_status(plan),
        "tasks": _tasks_status(tasks),
    }
    findings = _assessment_findings(assessment, dependencies)
    return {
        "ok": not findings,
        "issue_id": issue_id,
        "assessment": assessment,
        "dependencies": dependencies,
        "findings": findings,
    }


def _artifact_path(issue_dir: Path, artifact_type: str) -> Path:
    if artifact_type == "task":
        task_dir = issue_dir / "05-tasks"
        task_dir.mkdir(parents=True, exist_ok=True)
        task_number = len(list(task_dir.glob("task-*.md"))) + 1
        return task_dir / f"task-{task_number:03d}.md"
    try:
        return issue_dir / ARTIFACT_PATHS[artifact_type]
    except KeyError as exc:
        raise ValueError(f"Unknown artifact type: {artifact_type}") from exc


def _markdown_document(title: str, content: str, links: dict[str, Any]) -> str:
    frontmatter = _frontmatter(title, links)
    return f"{SPDX_MARKDOWN}---\n{frontmatter}---\n\n# {title}\n\n{content.rstrip()}\n"


def _yaml_document(title: str, content: str, links: dict[str, Any]) -> str:
    link_lines = _link_lines(links, "  ") or "  {}"
    indented_content = "\n".join(f"  {line}" for line in content.rstrip().splitlines())
    return (
        f"# {_SPDX_TAG}: Apache-2.0\n"
        f"title: {title}\nlinks:\n{link_lines}\ncontent: |\n{indented_content}\n"
    )


def _frontmatter(title: str, links: dict[str, Any]) -> str:
    link_lines = _link_lines(links, "  ") or "  {}"
    return f"title: {title}\nlinks:\n{link_lines}\n"


def _link_lines(links: dict[str, Any], indent: str) -> str:
    return "\n".join(f"{indent}{key}: {value}" for key, value in links.items())


def _specification_draft(requirement: str) -> str:
    return (
        "## [DRAFT] Required behavior\n\n"
        f"{requirement}\n\n"
        "## [DRAFT] Acceptance criteria\n\n"
        "- Define observable success behavior.\n"
        "- Define failure behavior and error reporting.\n"
        "- Define focused test cases."
    )


def _architecture_draft(requirement: str) -> str:
    return (
        "## [DRAFT] Repository analysis required\n\n"
        f"The architecture must support: {requirement}\n\n"
        "Identify the owning components, existing lifecycle, public interfaces, "
        "and extension points from repository evidence before implementation."
    )


def _plan_draft() -> str:
    return (
        "[DRAFT] Replace these generic steps with file-specific work.\n\n"
        "1. Inspect the existing implementation and tests.\n"
        "2. Resolve specification and architecture decisions from repository "
        "evidence.\n"
        "3. Implement the approved minimal change.\n"
        "4. Add focused regression coverage.\n"
        "5. Run relevant tests and record actual evidence."
    )


def _task_one_draft() -> str:
    return (
        "[DRAFT] Locate the owner, current behavior, and focused tests. "
        "Record exact files and APIs before editing."
    )


def _task_two_draft() -> str:
    return "[DRAFT] Implement the approved behavior using existing repository patterns."


def _task_three_draft() -> str:
    return "[DRAFT] Add focused tests and record the real test commands and results."


def _read_artifact(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _read_task_artifacts(task_dir: Path) -> list[str]:
    if not task_dir.is_dir():
        return []
    return [path.read_text(encoding="utf-8") for path in task_dir.glob("task-*.md")]


def _artifact_status(content: str) -> str:
    if not content:
        return "missing"
    if "[DRAFT]" in content:
        return "mostly_placeholder"
    return "complete"


def _dependency_status(dependencies: list[str], downstream: str) -> str:
    if not dependencies:
        return "not_applicable"
    analysis = _section_content(downstream, "dependency analysis")
    if (
        analysis
        and "[DRAFT]" not in analysis
        and all(dependency in analysis for dependency in dependencies)
    ):
        return "complete"
    return "missing"


def _evidence_status(content: str) -> str:
    evidence = _section_content(content, "repository evidence")
    return "complete" if evidence and "[DRAFT]" not in evidence else "missing"


def _tasks_status(tasks: list[str]) -> str:
    if not tasks:
        return "missing"
    if any("[DRAFT]" in task for task in tasks):
        return "mostly_placeholder"
    return "complete"


def _assessment_findings(
    assessment: dict[str, str], dependencies: list[str]
) -> list[str]:
    findings = [
        f"{name.replace('_', ' ')} is {status.replace('_', ' ')}"
        for name, status in assessment.items()
        if status not in {"complete", "not_applicable"}
    ]
    if assessment["dependency_analysis"] == "missing":
        findings.append(
            "Analyze these requirement dependencies in downstream artifacts: "
            + ", ".join(dependencies)
        )
    if assessment["repository_evidence"] == "missing":
        findings.append(
            "Add a 'Repository evidence' section with inspected files, symbols, "
            "and test targets."
        )
    return findings


def _section_content(content: str, heading: str) -> str:
    match = re.search(
        rf"(?ims)^#+\s+{re.escape(heading)}\s*$\n(.*?)(?=^#+\s|\Z)",
        content,
    )
    return match.group(1).strip() if match else ""
