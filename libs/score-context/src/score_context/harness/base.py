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

from abc import ABC, abstractmethod
from typing import TypedDict


class TaskSpec(TypedDict, total=False):
    id: str
    description: str
    seed_node_ids: list[str]
    expected_node_ids: list[str]
    top_n: int


class AssuranceHarness(ABC):
    """Stable candidate seam mirrored from the upstream score harness."""

    @abstractmethod
    def get_context(self, task_spec: TaskSpec) -> str:
        """Return deterministic context to prepend to an agent task."""

    def post_process(self, agent_output: str, task_spec: TaskSpec) -> dict[str, str]:
        """Default post-processing hook; Lane A does not require an agent."""

        return {"agent_output": agent_output}


class BaselineHarness(AssuranceHarness):
    """Baseline receives no selected context and should fail seeded tasks."""

    def get_context(self, task_spec: TaskSpec) -> str:
        return ""
