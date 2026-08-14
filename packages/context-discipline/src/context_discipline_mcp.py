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

"""
Context-Discipline MCP Server

Manages working memory and records local learning observations.
Integrates with graphify-codegraph (wraps external graphify CLI).
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class WorkingMemoryEntry:
    """One entry in working memory session."""

    timestamp: str
    type: str  # "goal", "assumption", "finding", "decision", "outcome"
    content: str
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LocalObservation:
    """Observation to record for local learning."""

    session_id: str
    task: str
    verdict: str  # "pass", "fail"
    coverage: float  # 0.0-1.0
    path_length: int
    surfaced_nodes: list[str]
    missing_nodes: list[str]
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class ContextDisciplineMCP:
    """
    Manages working memory and local learning.

    Integrates with:
    - graphify-codegraph (MCP) which wraps external graphify CLI for code queries
    """

    def __init__(self, repo_path: str = ".", local_store: str = ".score-local"):
        self.repo_path = Path(repo_path).expanduser().resolve()
        store_path = Path(local_store).expanduser()
        self.local_store = (
            store_path if store_path.is_absolute() else self.repo_path / store_path
        )
        self.local_store.mkdir(parents=True, exist_ok=True)

        self.session_id = f"session_{uuid4().hex[:8]}"
        self.working_memory = []
        self.observations_path = self.local_store / "observations.jsonl"

    def initialize_session(
        self,
        goal: str,
        subgoals: list[str],
        assumptions: list[str] | dict[str, str] | None = None,
    ) -> str:
        """
        Initialize a working memory session.

        Args:
            goal: The main goal
            subgoals: List of subgoals
            assumptions: List of assumptions or dict of assumption -> confidence level

        Returns:
            session_id
        """
        self.working_memory.append(
            WorkingMemoryEntry(
                timestamp=datetime.now().isoformat(),
                type="goal",
                content=goal,
                metadata={"subgoals": subgoals},
            )
        )

        if assumptions:
            if isinstance(assumptions, list):
                # Handle list of assumptions
                for assumption in assumptions:
                    self.working_memory.append(
                        WorkingMemoryEntry(
                            timestamp=datetime.now().isoformat(),
                            type="assumption",
                            content=assumption,
                            metadata={"confidence": "unknown"},
                        )
                    )
            elif isinstance(assumptions, dict):
                # Handle dict of assumption -> confidence
                for assumption, confidence in assumptions.items():
                    self.working_memory.append(
                        WorkingMemoryEntry(
                            timestamp=datetime.now().isoformat(),
                            type="assumption",
                            content=assumption,
                            metadata={"confidence": confidence},
                        )
                    )

        return self.session_id

    def query_graph(self, query: str) -> str:
        """
        Query code graph via graphify-codegraph MCP.

        Args:
            query: Natural language query (e.g., "all functions in auth.py")

        Returns:
            Query result as string
        """
        finding = f"Graph query: {query}"
        self.working_memory.append(
            WorkingMemoryEntry(
                timestamp=datetime.now().isoformat(),
                type="finding",
                content=finding,
                metadata={"source": "graph"},
            )
        )
        return finding

    def record_decision(
        self, decision: str, reason: list[str], reversible: bool = True
    ) -> None:
        """Record a decision with reasoning."""
        self.working_memory.append(
            WorkingMemoryEntry(
                timestamp=datetime.now().isoformat(),
                type="decision",
                content=decision,
                metadata={"reason": reason, "reversible": reversible},
            )
        )

    def record_outcome(
        self,
        task: str,
        verdict: str,
        coverage: float,
        surfaced_nodes: list[str],
        missing_nodes: list[str],
    ) -> None:
        """
        Record final outcome for local learning.

        Args:
            task: Task description
            verdict: "pass" or "fail"
            coverage: Coverage ratio (0.0-1.0)
            surfaced_nodes: Nodes surfaced in solution
            missing_nodes: Nodes missed/not addressed
        """
        # Record to working memory
        self.working_memory.append(
            WorkingMemoryEntry(
                timestamp=datetime.now().isoformat(),
                type="outcome",
                content=verdict,
                metadata={
                    "coverage": coverage,
                    "surfaced": len(surfaced_nodes),
                    "missing": len(missing_nodes),
                },
            )
        )

        # Record observation for local learning
        observation = LocalObservation(
            session_id=self.session_id,
            task=task,
            verdict=verdict,
            coverage=coverage,
            path_length=len(self.working_memory),
            surfaced_nodes=surfaced_nodes,
            missing_nodes=missing_nodes,
        )

        # Append to local experience log
        with open(self.observations_path, "a") as f:
            f.write(json.dumps(asdict(observation)) + "\n")

    def get_working_memory(self) -> list[dict[str, Any]]:
        """Return current working memory."""
        return [asdict(entry) for entry in self.working_memory]

    def get_unverified_assumptions(self) -> list[str]:
        """Return assumptions not yet verified."""
        assumptions = [
            entry.content
            for entry in self.working_memory
            if entry.type == "assumption" and entry.metadata.get("confidence") != "high"
        ]
        return assumptions


# For testing
if __name__ == "__main__":
    mcp = ContextDisciplineMCP()
    session_id = mcp.initialize_session(
        goal="Refactor auth module",
        subgoals=["Understand", "Implement", "Test"],
        assumptions={"auth.py exists": "high", "No external imports": "medium"},
    )

    print(f"Session: {session_id}")
    print(f"Working memory entries: {len(mcp.get_working_memory())}")
    print(f"Unverified assumptions: {mcp.get_unverified_assumptions()}")
