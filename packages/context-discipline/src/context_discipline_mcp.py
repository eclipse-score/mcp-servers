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

Manages working memory, durable context overlays, and local session retrieval.
Integrates with graphify-codegraph (wraps external graphify CLI).
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from context_attention import get_prior_context
from context_merge import MergedGraph
from context_overlay import OverlayEdge, OverlayNode, OverlayStore, Provenance
from context_sessions import (
    OutcomeRecord,
    ReasoningRecord,
    RetrievalRecord,
    SessionLog,
    SessionRecord,
    TaskRecord,
)


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

        self.session_id = f"session__{uuid4().hex[:8]}"
        self.working_memory = []
        self.observations_path = self.local_store / "observations.jsonl"
        self.session_log = SessionLog(self.repo_path, local_store)
        self.overlay_store = OverlayStore(self.repo_path)
        self.overlay_store.load()
        self.session_log.append(
            SessionRecord(id=self.session_id, agent="unknown", goal="")
        )
        self.goal_task_id: str | None = None

    def initialize_session(
        self,
        goal: str,
        subgoals: list[str],
        assumptions: list[str] | dict[str, str] | None = None,
        agent: str = "unknown",
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
        self.session_log.append(
            SessionRecord(id=self.session_id, agent=agent, goal=goal)
        )
        goal_task = TaskRecord(session_id=self.session_id, text=goal)
        self.goal_task_id = goal_task.id
        self.session_log.append(goal_task)
        for subgoal in subgoals:
            self.session_log.append(
                TaskRecord(
                    session_id=self.session_id,
                    text=subgoal,
                    parent_id=goal_task.id,
                )
            )
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
        Query the generated local Graphify code graph.

        Args:
            query: Natural language query (e.g., "all functions in auth.py")

        Returns:
            Query result as string
        """
        graph_path = self.repo_path / "graphify-out" / "graph.json"
        graph = MergedGraph.build(self.repo_path)
        terms = [term.lower() for term in query.split() if term.strip()]
        nodes = tuple(graph.nodes.values())
        serialized_nodes = [
            (
                node,
                json.dumps(
                    {
                        "id": node.id,
                        "label": node.label,
                        "type": node.type,
                    },
                    sort_keys=True,
                ).lower(),
            )
            for node in nodes
        ]
        matched_nodes = [
            asdict(node)
            for node, serialized in serialized_nodes
            if all(term in serialized for term in terms)
        ]
        if not graph_path.exists():
            finding = (
                f"Graph query: {query}\n"
                f"No graph found at {graph_path}. Run setup_graphify first."
            )
        else:
            finding = json.dumps(
                {"query": query, "matches": matched_nodes}, sort_keys=True
            )
        self.session_log.append(
            RetrievalRecord(
                session_id=self.session_id,
                task_id=self.goal_task_id or "",
                query=query,
                returned_nodes=[node["id"] for node in matched_nodes],
            )
        )
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
        self,
        decision: str,
        reason: list[str],
        reversible: bool = True,
        grounded_nodes: list[str] | None = None,
    ) -> None:
        """Record a decision with reasoning."""
        self.session_log.append(
            ReasoningRecord(
                session_id=self.session_id,
                task_id=self.goal_task_id or "",
                text=decision,
                kind="decision",
                grounded_nodes=grounded_nodes or [],
            )
        )
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

        task_id = self.goal_task_id or ""
        for record in reversed(self.session_log.records_for(self.session_id)):
            if isinstance(record, TaskRecord) and record.text == task:
                task_id = record.id
                break
        self.session_log.append(
            OutcomeRecord(
                session_id=self.session_id,
                task_id=task_id,
                verdict=verdict,
                coverage=coverage,
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

    def get_prior_context(
        self, task_text: str, current_nodes: list[str]
    ) -> list[dict[str, Any]]:
        """Retrieve relevant reasoning from other sessions."""
        return [
            asdict(item)
            for item in get_prior_context(
                self.session_log, self.session_id, task_text, set(current_nodes)
            )
        ]

    def add_overlay_node(
        self,
        id: str,
        type: str,
        title: str,
        relation: str,
        target: str,
        confidence: float,
    ) -> dict[str, Any]:
        """Add a durable domain node and relation to the merged graph."""
        graph = MergedGraph.build(self.repo_path)
        if not graph.has_node(target):
            raise ValueError(f"overlay target node not found: {target}")
        provenance = Provenance(
            repo=str(self.repo_path),
            adapter="context-discipline",
            confidence=confidence,
            observed_at=datetime.now(tz=UTC).isoformat(),
        )
        node = OverlayNode(
            id=id,
            type=type,
            title=title,
            provenance=provenance,
        )
        edge = OverlayEdge(
            source=id,
            target=target,
            relation=relation,
            provenance=provenance,
        )
        self.overlay_store.upsert_node(node)
        self.overlay_store.upsert_edge(edge)
        self.overlay_store.save()
        return {"node": asdict(node), "edge": asdict(edge)}


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
                "agent": {"type": "string", "default": "unknown"},
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
                "grounded_nodes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
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
    {
        "name": "get_prior_context",
        "description": "Retrieve relevant reasoning from other sessions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_text": {"type": "string"},
                "current_nodes": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["task_text", "current_nodes"],
        },
    },
    {
        "name": "add_overlay_node",
        "description": "Add a durable S-CORE node and relation to the graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "type": {"type": "string"},
                "title": {"type": "string"},
                "relation": {"type": "string"},
                "target": {"type": "string"},
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
            },
            "required": [
                "id",
                "type",
                "title",
                "relation",
                "target",
                "confidence",
            ],
        },
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
    if name == "get_prior_context":
        return manager.get_prior_context(**arguments)
    if name == "add_overlay_node":
        return manager.add_overlay_node(**arguments)
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
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
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
            try:
                output = handle(manager, json.loads(line))
            except (json.JSONDecodeError, TypeError) as exc:
                output = json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": f"Invalid JSON-RPC request: {exc}",
                        },
                    }
                )
            if output:
                print(output, flush=True)


def main() -> None:
    serve()


if __name__ == "__main__":
    main()
