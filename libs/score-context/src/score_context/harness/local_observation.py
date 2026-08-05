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

"""Local observation management: agent records and updates graph immediately."""

import json
from datetime import UTC, datetime
from pathlib import Path

from score_context.graph import ContextGraph
from score_context.schema.edges import Edge, EdgeRelation
from score_context.schema.nodes import Node, NodeType
from score_context.schema.observation import AgentObservation, ObservationIndex
from score_context.schema.provenance import Provenance


class LocalObservationManager:
    """
    Manages agent observations locally (no central coordination).

    Steps:
    1. Collect observation from agent
    2. Filter by importance (agent decides)
    3. Update local graph incrementally
    4. Build observation index
    5. Store full observation file
    6. (Workflow handles git commit)
    """

    def __init__(self, observations_dir: Path = Path(".score-context")) -> None:
        """Initialize observation manager with base directory."""
        self.base_dir = Path(observations_dir)
        self.observations_dir = self.base_dir / "observations"
        self.graph_dir = self.base_dir / "graph"
        self.index_log = self.base_dir / "observation_index.jsonl"
        self.index_file = self.base_dir / "observation_index.json"

        # Create directories
        self.observations_dir.mkdir(parents=True, exist_ok=True)
        self.graph_dir.mkdir(parents=True, exist_ok=True)

    def should_record_observation(self, observation: AgentObservation) -> bool:
        """
        Step 1.2: Filter locally by importance.

        Not all observations are worth recording.
        Agent filters at source to reduce noise.

        Args:
            observation: The observation to evaluate

        Returns:
            True if observation should be recorded
        """
        # Filter criteria - both must pass
        min_importance = 5  # Configurable
        min_coverage = 0.3  # At least 30% coverage

        passes_importance = observation.importance_score >= min_importance
        passes_coverage = observation.coverage >= min_coverage

        # All observations (pass or fail) must meet BOTH criteria
        return passes_importance and passes_coverage

    def update_local_graph(self, observation: AgentObservation) -> ContextGraph:
        """
        Step 1.3: Update local graph incrementally.

        Add only NEW nodes and edges discovered by agent.
        Don't rewrite entire graph.

        Args:
            observation: The observation with discovered nodes/edges

        Returns:
            Updated graph
        """
        # Load current graph (or create if not exists)
        graph_file = self.graph_dir / "graph.json"

        if graph_file.exists():
            graph_data = json.loads(graph_file.read_text())
            graph = ContextGraph(
                nodes={n["id"]: Node(**n) for n in graph_data.get("nodes", [])},
                edges=[Edge(**e) for e in graph_data.get("edges", [])],
            )
        else:
            # Start with empty graph
            graph = ContextGraph(nodes={}, edges=[])

        # Step 1: Add new nodes from observation
        for node_data in observation.discovered_nodes:
            if node_data.id not in graph.nodes:
                # Create node with proper type
                try:
                    node_type = NodeType(node_data.type)
                except ValueError:
                    # Fall back to DOCUMENT if type not recognized
                    node_type = NodeType.DOCUMENT

                provenance = Provenance(
                    repo=node_data.repo or "unknown",
                    adapter="agent_discovery",
                    confidence=node_data.confidence,
                    observed_at=observation.timestamp,
                )

                node = Node(
                    id=node_data.id,
                    type=node_type,
                    title=node_data.title,
                    provenance=provenance,
                )
                graph.nodes[node_data.id] = node
                print(f"✨ Added node: {node_data.id}")

        # Step 2: Add new edges from observation
        for edge_data in observation.route.edges:
            # Check if edge already exists
            edge_exists = any(
                e.source == edge_data.source
                and e.target == edge_data.target
                and str(e.relation) == edge_data.relation
                for e in graph.edges
            )

            if not edge_exists:
                # Create edge with proper types
                provenance = Provenance(
                    repo="unknown",
                    adapter="agent_discovery",
                    confidence=0.90,
                    observed_at=observation.timestamp,
                )

                edge = Edge(
                    source=edge_data.source,
                    target=edge_data.target,
                    relation=EdgeRelation(edge_data.relation),
                    provenance=provenance,
                )
                graph.edges.append(edge)
                print(f"✨ Added edge: {edge_data.source} → {edge_data.target}")

        # Save graph to file (will only commit diffs to git)
        self._save_graph(graph)

        return graph

    def _save_graph(self, graph: ContextGraph) -> None:
        """Save graph to JSON file."""
        # Serialize nodes with proper datetime handling
        nodes_data = []
        for node in graph.nodes.values():
            node_dict = node.model_dump()
            # Convert provenance datetime to ISO string
            if isinstance(node_dict.get("provenance"), dict) and isinstance(
                node_dict["provenance"].get("observed_at"), datetime
            ):
                node_dict["provenance"]["observed_at"] = node_dict["provenance"][
                    "observed_at"
                ].isoformat()
            nodes_data.append(node_dict)

        # Serialize edges with proper datetime handling
        edges_data = []
        for edge in graph.edges:
            edge_dict = edge.model_dump()
            # Convert provenance datetime to ISO string
            if isinstance(edge_dict.get("provenance"), dict) and isinstance(
                edge_dict["provenance"].get("observed_at"), datetime
            ):
                edge_dict["provenance"]["observed_at"] = edge_dict["provenance"][
                    "observed_at"
                ].isoformat()
            edges_data.append(edge_dict)

        graph_data = {
            "version": "v1_local",
            "timestamp": datetime.now(UTC).isoformat(),
            "nodes": nodes_data,
            "edges": edges_data,
        }

        graph_file = self.graph_dir / "graph.json"
        graph_file.write_text(json.dumps(graph_data, indent=2))

    def build_observation_index(
        self, observation: AgentObservation
    ) -> ObservationIndex:
        """
        Step 1.4: Build observation index for fast queries.

        Index by edge, node, task for O(1) lookup later.
        Append to jsonl log (queryable).

        Args:
            observation: The observation to index

        Returns:
            Index entry
        """
        # Create index entry
        index_entry = ObservationIndex(
            obs_id=observation.id,
            task_id=observation.task_id,
            timestamp=observation.timestamp,
            verdict=observation.verdict,
            edges=[(e.source, e.target, e.relation) for e in observation.route.edges],
            nodes=observation.route.nodes,
            importance=observation.importance_score,
        )

        # Append to jsonl log (immutable, sequential)
        with open(self.index_log, "a") as f:
            f.write(index_entry.model_dump_json() + "\n")

        return index_entry

    def rebuild_full_index(self) -> dict[str, dict[str, list[str]]]:
        """
        Rebuild full index from jsonl log for fast lookups.

        Builds three indexes:
        - by_edge: which observations used this edge?
        - by_node: which observations visited this node?
        - by_task: which observations solved this task?

        Returns:
            Full index dict
        """
        index: dict[str, dict[str, list[str]]] = {
            "by_edge": {},
            "by_node": {},
            "by_task": {},
        }

        if not self.index_log.exists():
            return index

        # Scan jsonl log
        with open(self.index_log) as f:
            for line in f:
                entry_data = json.loads(line)
                entry = ObservationIndex(**entry_data)

                # Index by edges
                for edge in entry.edges:
                    edge_key = str(edge)  # Hashable
                    if edge_key not in index["by_edge"]:
                        index["by_edge"][edge_key] = []
                    index["by_edge"][edge_key].append(entry.obs_id)

                # Index by nodes
                for node in entry.nodes:
                    if node not in index["by_node"]:
                        index["by_node"][node] = []
                    index["by_node"][node].append(entry.obs_id)

                # Index by task
                if entry.task_id not in index["by_task"]:
                    index["by_task"][entry.task_id] = []
                index["by_task"][entry.task_id].append(entry.obs_id)

        # Save rebuilt index
        self.index_file.write_text(json.dumps(index, indent=2))

        return index

    def store_observation(self, observation: AgentObservation) -> Path:
        """
        Step 1.5: Store full observation file for audit trail.

        Args:
            observation: The observation to store

        Returns:
            Path to stored file
        """
        obs_file = self.observations_dir / f"{observation.id}.json"
        obs_file.write_text(observation.model_dump_json(indent=2))

        print(f"💾 Stored observation: {obs_file}")
        return obs_file

    def record_observation(self, observation: AgentObservation) -> Path | None:
        """
        Complete local observation recording (Steps 1.1-1.5).

        Orchestrates:
        1. Filter by importance
        2. Update local graph
        3. Build observation index
        4. Store full file

        Returns:
            Path to stored file if recorded, None if filtered out
        """
        # Step 1.2: Filter
        if not self.should_record_observation(observation):
            print(
                f"⏭️  Observation filtered (importance={observation.importance_score})"
            )
            return None

        # Step 1.3: Update graph
        self.update_local_graph(observation)

        # Step 1.4: Build index
        self.build_observation_index(observation)
        self.rebuild_full_index()

        # Step 1.5: Store
        obs_file = self.store_observation(observation)

        print("✅ Observation recorded locally")
        return obs_file

    def load_index(self) -> dict[str, dict[str, list[str]]]:
        """Load the built index for queries."""
        if self.index_file.exists():
            return json.loads(self.index_file.read_text())
        return {"by_edge": {}, "by_node": {}, "by_task": {}}

    def query_observations_by_edge(
        self, source: str, target: str, relation: str
    ) -> list[AgentObservation]:
        """Query: which observations used this edge?"""
        index = self.load_index()
        edge_key = str((source, target, relation))

        obs_ids = index.get("by_edge", {}).get(edge_key, [])
        observations: list[AgentObservation] = []

        for obs_id in obs_ids:
            obs_file = self.observations_dir / f"{obs_id}.json"
            if obs_file.exists():
                obs_data = json.loads(obs_file.read_text())
                observations.append(AgentObservation(**obs_data))

        return observations

    def query_observations_by_task(self, task_id: str) -> list[AgentObservation]:
        """Query: which observations solved this task?"""
        index = self.load_index()
        obs_ids = index.get("by_task", {}).get(task_id, [])

        observations: list[AgentObservation] = []
        for obs_id in obs_ids:
            obs_file = self.observations_dir / f"{obs_id}.json"
            if obs_file.exists():
                obs_data = json.loads(obs_file.read_text())
                observations.append(AgentObservation(**obs_data))

        return observations
