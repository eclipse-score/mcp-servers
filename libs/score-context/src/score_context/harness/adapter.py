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

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from score_context.graph import compose_fragments
from score_context.harness.base import BaselineHarness, TaskSpec
from score_context.harness.candidate import ContextHarness
from score_context.harness.gate import lane_a_gate

CONTRACT_VERSION = "v0.1.0"
ERROR_CODES = {
    "E_INPUT_INVALID",
    "E_CONTRACT_VERSION",
    "E_PROFILE_UNSUPPORTED",
    "E_CANDIDATE_INVALID",
    "E_TASK_SPEC_INVALID",
    "E_RUNTIME_FAILURE",
    "E_ARTIFACT_WRITE",
}


class AdapterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["v0.1.0"]
    operation: Literal["validate", "run", "report"]
    issue_id: int = Field(ge=1)
    task_spec: str = Field(min_length=1)
    candidate_path: str = Field(min_length=1)
    artifacts_dir: str = Field(min_length=1)
    profile: Literal["iso26262"]
    strict: bool


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    type: str


class Traceability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: int
    task_id: str
    run_id: str


class AdapterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["v0.1.0"]
    operation: Literal["validate", "run", "report"]
    status: Literal["pass", "fail", "error"]
    error_code: str | None
    summary: str
    artifacts: list[Artifact]
    traceability: Traceability


def _load_task(path: Path) -> TaskSpec:
    task = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(task, dict):
        raise ValueError("task spec must be a JSON object")
    task_object = cast(dict[str, object], task)
    if not isinstance(task_object.get("id"), str):
        raise ValueError("task spec.id must be a string")
    if not isinstance(task_object.get("seed_node_ids"), list):
        raise ValueError("task spec.seed_node_ids must be a list")
    if not isinstance(task_object.get("expected_node_ids"), list):
        raise ValueError("task spec.expected_node_ids must be a list")
    return cast(TaskSpec, task_object)


def _response(
    request: AdapterRequest,
    status: Literal["pass", "fail", "error"],
    summary: str,
    task_id: str,
    run_id: str,
    artifacts: list[Artifact],
    error_code: str | None = None,
) -> AdapterResponse:
    if error_code is not None and error_code not in ERROR_CODES:
        raise ValueError(f"unknown error code: {error_code}")
    return AdapterResponse(
        contract_version=CONTRACT_VERSION,
        operation=request.operation,
        status=status,
        error_code=error_code,
        summary=summary,
        artifacts=artifacts,
        traceability=Traceability(
            issue_id=request.issue_id,
            task_id=task_id,
            run_id=run_id,
        ),
    )


def execute(request_data: dict[str, object], root: Path) -> AdapterResponse:
    """Execute one adapter request against the committed seed graph."""

    raw_operation = request_data.get("operation")
    operation = cast(
        Literal["validate", "run", "report"],
        raw_operation if raw_operation in {"validate", "run", "report"} else "run",
    )
    raw_issue_id = request_data.get("issue_id")
    issue_id = raw_issue_id if isinstance(raw_issue_id, int) and raw_issue_id > 0 else 1
    raw_version = request_data.get("contract_version")
    if raw_version != CONTRACT_VERSION:
        return AdapterResponse(
            contract_version=CONTRACT_VERSION,
            operation=operation,
            status="error",
            error_code="E_CONTRACT_VERSION",
            summary="unsupported contract version",
            artifacts=[],
            traceability=Traceability(
                issue_id=issue_id,
                task_id="unknown",
                run_id=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
            ),
        )
    if request_data.get("profile") != "iso26262":
        return AdapterResponse(
            contract_version=CONTRACT_VERSION,
            operation=operation,
            status="error",
            error_code="E_PROFILE_UNSUPPORTED",
            summary="unsupported profile",
            artifacts=[],
            traceability=Traceability(
                issue_id=issue_id,
                task_id="unknown",
                run_id=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
            ),
        )
    try:
        request = AdapterRequest.model_validate(request_data)
    except ValidationError as error:
        return AdapterResponse(
            contract_version=CONTRACT_VERSION,
            operation=operation,
            status="error",
            error_code="E_INPUT_INVALID",
            summary=str(error),
            artifacts=[],
            traceability=Traceability(
                issue_id=issue_id,
                task_id="unknown",
                run_id=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
            ),
        )
    task_path = root / request.task_spec
    candidate_path = root / request.candidate_path
    if not candidate_path.is_file():
        return _response(
            request,
            "error",
            "candidate path does not identify a file",
            "unknown",
            datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
            [],
            "E_CANDIDATE_INVALID",
        )
    try:
        task = _load_task(task_path)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return _response(
            request,
            "error",
            str(error),
            "unknown",
            datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
            [],
            "E_TASK_SPEC_INVALID",
        )
    task_id = str(task.get("id", "unknown"))
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = root / request.artifacts_dir
    artifact_name = "validation.json" if request.operation == "validate" else "run.json"
    artifact_path = artifact_dir / artifact_name
    if request.operation == "report":
        try:
            existing = json.loads(artifact_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return _response(
                request,
                "error",
                str(error),
                task_id,
                run_id,
                [],
                "E_RUNTIME_FAILURE",
            )
        gate = existing["candidate"]["gate"]
        response_artifacts = [
            Artifact(
                path=request.artifacts_dir + "/" + artifact_name,
                type="run_result",
            )
        ]
        return _response(
            request,
            gate["verdict"],
            "existing run report returned",
            task_id,
            str(existing["run_id"]),
            response_artifacts,
        )
    try:
        graph = compose_fragments([root / "harness/spec/graph_fragment.json"])
        candidate = ContextHarness(graph, "mcp-servers", "developer")
        baseline = BaselineHarness()
        candidate_context = candidate.get_context(task)
        baseline_context = baseline.get_context(task)
        candidate_gate = lane_a_gate(candidate_context, task)
        baseline_gate = lane_a_gate(baseline_context, task)
        result = {
            "run_id": run_id,
            "task_id": task_id,
            "candidate": {
                "context": candidate_context,
                "gate": candidate_gate.model_dump(mode="json"),
            },
            "baseline": {
                "context": baseline_context,
                "gate": baseline_gate.model_dump(mode="json"),
            },
        }
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        return _response(
            request,
            "error",
            str(error),
            task_id,
            run_id,
            [],
            "E_ARTIFACT_WRITE",
        )
    except (KeyError, TypeError, ValueError) as error:
        return _response(
            request,
            "error",
            str(error),
            task_id,
            run_id,
            [],
            "E_RUNTIME_FAILURE",
        )
    status: Literal["pass", "fail"] = (
        "pass" if candidate_gate.verdict == "pass" else "fail"
    )
    return _response(
        request,
        status,
        "candidate gate completed",
        task_id,
        run_id,
        [Artifact(path=request.artifacts_dir + "/" + artifact_name, type="run_result")],
    )
