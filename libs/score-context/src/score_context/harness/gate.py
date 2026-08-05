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

from pydantic import BaseModel, ConfigDict, Field

from score_context.harness.base import TaskSpec
from score_context.schema.experience import Route


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: str = Field(pattern="^(pass|fail)$")
    expected_node_ids: list[str]
    surfaced_node_ids: list[str]
    missing_node_ids: list[str]
    route: Route | None = Field(default=None)


def lane_a_gate(
    context: str,
    task_spec: TaskSpec,
    route: Route | None = None,
) -> GateResult:
    """Pass iff every expected natural key is surfaced in candidate context."""

    expected = task_spec.get("expected_node_ids", [])
    surfaced = [node_id for node_id in expected if node_id in context]
    missing = [node_id for node_id in expected if node_id not in context]
    return GateResult(
        verdict="pass" if not missing else "fail",
        expected_node_ids=expected,
        surfaced_node_ids=surfaced,
        missing_node_ids=missing,
        route=route,
    )
