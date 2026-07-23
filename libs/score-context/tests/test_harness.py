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

from score_context.graph import compose_fragments
from score_context.harness import BaselineHarness, ContextHarness, lane_a_gate
from score_context.harness.adapter import execute


def test_baseline_fails_and_candidate_passes_lane_a() -> None:
    root = Path(__file__).parents[3]
    graph = compose_fragments([root / "harness/spec/graph_fragment.json"])
    task = json.loads((root / "harness/spec/task_001_contract_change.json").read_text())
    baseline_gate = lane_a_gate(BaselineHarness().get_context(task), task)
    candidate_gate = lane_a_gate(
        ContextHarness(graph, "mcp-servers", "developer").get_context(task),
        task,
    )
    assert baseline_gate.verdict == "fail"
    assert candidate_gate.verdict == "pass"


def test_adapter_envelope_and_error_codes(tmp_path: Path) -> None:
    root = Path(__file__).parents[3]
    request = json.loads((root / "harness/spec/request_run.json").read_text())
    response = execute(request, root)
    assert response.status == "pass"
    assert response.error_code is None
    assert response.traceability.issue_id == 1
    invalid = dict(request)
    invalid["contract_version"] = "v9.0.0"
    error = execute(invalid, root)
    assert error.status == "error"
    assert error.error_code == "E_CONTRACT_VERSION"
    unsupported = dict(request)
    unsupported["profile"] = "other"
    profile_error = execute(unsupported, root)
    assert profile_error.error_code == "E_PROFILE_UNSUPPORTED"
    assert list(tmp_path.glob("*.json")) == []
