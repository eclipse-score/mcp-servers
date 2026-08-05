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

import time
import uuid
from datetime import UTC, datetime

from score_context.context import ContextEngine, ContextSelection
from score_context.graph import ContextGraph
from score_context.harness.base import AssuranceHarness, TaskSpec
from score_context.harness.gate import GateResult
from score_context.schema.edges import EdgeRelation
from score_context.schema.experience import ExperienceNode
from score_context.schema.provenance import Provenance


class ContextHarness(AssuranceHarness):
    """Candidate harness backed by the deterministic attention engine."""

    def __init__(
        self,
        graph: ContextGraph,
        repo: str,
        role: str,
        track_route: bool = False,
    ) -> None:
        self.graph = graph
        self.engine = ContextEngine(graph)
        self.repo = repo
        self.role = role
        self.track_route = track_route
        self.last_selection: ContextSelection | None = None
        self.run_id = uuid.uuid4().hex

    def get_context(
        self,
        task_spec: TaskSpec,
        experience_weights: dict[tuple[str, str, EdgeRelation], float] | None = None,
    ) -> str:
        top_n = task_spec.get("top_n", 5)
        self.last_selection = self.engine.get_context(
            task_spec,
            self.repo,
            self.role,
            top_n,
            track_route=self.track_route,
            experience_weights=experience_weights,
        )
        return self.last_selection.rendered

    def record_experience(
        self,
        gate_result: GateResult,
        task_spec: TaskSpec,
        repo: str = "unknown",
        adapter: str = "harness",
        confidence: float = 1.0,
    ) -> ExperienceNode:
        """
        Record a route + verdict as a learnable experience.
        Called by the adapter after lane_a_gate completes.

        Returns the ExperienceNode artifact for persistence.
        """
        if not self.last_selection:
            raise ValueError("No selection made; get_context must be called first")
        if not self.last_selection.route:
            raise ValueError(
                "No route captured; ContextHarness must be instantiated "
                "with track_route=True"
            )

        # Build experience node
        task_id = task_spec.get("id", "unknown")
        experience_id = f"exp_{task_id}_{self.run_id}_{int(time.time() * 1000)}"

        route = self.last_selection.route
        route_edges = [
            (t.source_id, t.target_id, t.relation.value)
            for t in route.traversals
            if t.source_id != "__SEED__"
        ]

        # Ensure verdict is properly typed
        verdict: str = gate_result.verdict
        if verdict not in ("pass", "fail"):
            verdict = "fail"

        experience = ExperienceNode(
            id=experience_id,
            type="experience",
            task_id=str(task_id),
            run_id=self.run_id,
            attempt=0,
            route_edges=route_edges,
            route_node_ids=[t.target_id for t in route.traversals],
            verdict=verdict,  # type: ignore
            surfaced_node_ids=gate_result.surfaced_node_ids,
            missing_node_ids=gate_result.missing_node_ids,
            coverage_ratio=(
                len(gate_result.surfaced_node_ids) / len(gate_result.expected_node_ids)
                if gate_result.expected_node_ids
                else 0.0
            ),
            path_length=len(route.traversals),
            provenance=Provenance(
                repo=repo,
                adapter=adapter,
                confidence=confidence,
                observed_at=datetime.now(UTC),
            ),
            seed_node_ids=gate_result.expected_node_ids or [],
            top_n=task_spec.get("top_n", 5),
            timestamp=datetime.now(UTC),
        )

        return experience
