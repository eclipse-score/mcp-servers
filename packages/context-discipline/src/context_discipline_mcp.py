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
        graph_path = self.repo_path / "graphify-out" / "graph.json"
        if not graph_path.exists():
            finding = (
                f"Graph query: {query}\n"
                f"No graph found at {graph_path}. Run setup_graphify first."
            )
        else:
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            terms = [term.lower() for term in query.split() if term.strip()]
            nodes = graph.get("nodes", [])
            matches = [
                node
                for node in nodes
                if all(
                    term in json.dumps(node, sort_keys=True).lower() for term in terms
                )
            ]
            finding = json.dumps({"query": query, "matches": matches}, sort_keys=True)
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


TOOLS = [
    {
        "name": "initialize_session",
        "description": "Initialize working memory for a coding session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "subgoals": {"type": "array", "items": {"type": "string"}},
                "assumptions": {"type": ["array", "object", "null"]},
            },
            "required": ["goal", "subgoals"],
        },
    },
    {
        "name": "query_graph",
        "description": "Query the generated Graphify code graph.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "record_decision",
        "description": "Record a decision and its reasons.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "decision": {"type": "string"},
                "reason": {"type": "array", "items": {"type": "string"}},
                "reversible": {"type": "boolean", "default": True},
            },
            "required": ["decision", "reason"],
        },
    },
    {
        "name": "record_outcome",
        "description": "Record a completed task for local learning.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "verdict": {"type": "string"},
                "coverage": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "surfaced_nodes": {"type": "array", "items": {"type": "string"}},
                "missing_nodes": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "task",
                "verdict",
                "coverage",
                "surfaced_nodes",
                "missing_nodes",
            ],
        },
    },
    {
        "name": "get_working_memory",
        "description": "Get current working memory entries.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_unverified_assumptions",
        "description": "Get assumptions that are not verified.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def call_tool(
    manager: ContextDisciplineMCP, name: str, arguments: dict[str, Any]
) -> Any:
    if name == "initialize_session":
        return manager.initialize_session(**arguments)
    if name == "query_graph":
        return manager.query_graph(**arguments)
    if name == "record_decision":
        return manager.record_decision(**arguments)
    if name == "record_outcome":
        return manager.record_outcome(**arguments)
    if name == "get_working_memory":
        return manager.get_working_memory()
    if name == "get_unverified_assumptions":
        return manager.get_unverified_assumptions()
    raise ValueError(f"Unknown tool: {name}")


def handle(manager: ContextDisciplineMCP, request: dict[str, Any]) -> str | None:
    if request.get("method") == "notifications/initialized":
        return None
    request_id = request.get("id")
    method = request.get("method")
    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "context-discipline", "version": "0.1.0"},
        }
        return json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result})
    if method == "tools/list":
        return json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
        )
    if method == "tools/call":
        try:
            params = request.get("params", {})
            result = call_tool(manager, params["name"], params.get("arguments", {}))
            content = [{"type": "text", "text": json.dumps(result)}]
            return json.dumps(
                {"jsonrpc": "2.0", "id": request_id, "result": {"content": content}}
            )
        except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
            return json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": str(exc)},
                }
            )
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"},
        }
    )


def serve() -> None:
    manager = ContextDisciplineMCP()
    for line in __import__("sys").stdin:
        if line.strip():
            output = handle(manager, json.loads(line))
            if output:
                print(output, flush=True)


def main() -> None:
    serve()


if __name__ == "__main__":
    main()
