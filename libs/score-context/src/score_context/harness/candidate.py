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

from score_context.context import ContextEngine, ContextSelection
from score_context.graph import ContextGraph
from score_context.harness.base import AssuranceHarness, TaskSpec


class ContextHarness(AssuranceHarness):
    """Candidate harness backed by the deterministic attention engine."""

    def __init__(self, graph: ContextGraph, repo: str, role: str) -> None:
        self.graph = graph
        self.engine = ContextEngine(graph)
        self.repo = repo
        self.role = role
        self.last_selection: ContextSelection | None = None

    def get_context(self, task_spec: TaskSpec) -> str:
        top_n = task_spec.get("top_n", 5)
        self.last_selection = self.engine.get_context(
            task_spec,
            self.repo,
            self.role,
            top_n,
        )
        return self.last_selection.rendered
