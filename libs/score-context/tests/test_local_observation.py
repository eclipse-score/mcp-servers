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

"""Tests for local observation management."""

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from score_context.harness.local_observation import LocalObservationManager
from score_context.schema.nodes import NodeType
from score_context.schema.observation import (
    AgentObservation,
    DiscoveredNode,
    Route,
    RouteEdge,
)


@pytest.fixture
def temp_obs_dir():
    """Create temporary observation directory."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def manager(temp_obs_dir):
    """Create LocalObservationManager instance."""
    return LocalObservationManager(temp_obs_dir)


@pytest.fixture
def sample_observation() -> AgentObservation:
    """Create a sample observation for testing."""
    now = datetime.now(UTC)

    route = Route(
        nodes=["node_a", "node_b", "node_c"],
        edges=[
            RouteEdge(
                source="node_a",
                target="node_b",
                relation="depends_on",
                weight_used=1.0,
                score_contributed=0.5,
            ),
            RouteEdge(
                source="node_b",
                target="node_c",
                relation="implements",
                weight_used=0.8,
                score_contributed=0.3,
            ),
        ],
    )

    discovered = [
        DiscoveredNode(
            id="new_node_x",
            type="contract",  # Use enum value, not enum name
            title="New Service Contract",
            confidence=0.92,
            repo="my-repo",
            url="https://example.com/x",
        ),
        DiscoveredNode(
            id="new_node_y",
            type="document",  # Use enum value, not enum name
            title="API Documentation",
            confidence=0.88,
            repo="docs-repo",
        ),
    ]

    observation = AgentObservation(
        id="obs__run_001",
        agent_id="agent_001",
        task_id="task_001",
        timestamp=now,
        route=route,
        discovered_nodes=discovered,
        verdict="pass",
        coverage=0.85,
        importance_score=7.5,
    )

    return observation


class TestLocalObservationManagerInit:
    """Test LocalObservationManager initialization."""

    def test_init_creates_directories(self, temp_obs_dir):
        """Test that initialization creates required directories."""
        manager = LocalObservationManager(temp_obs_dir)

        assert manager.observations_dir.exists()
        assert manager.graph_dir.exists()
        assert manager.base_dir == temp_obs_dir

    def test_init_with_default_path(self):
        """Test initialization with default path."""
        # Just verify it doesn't crash
        manager = LocalObservationManager()
        assert manager.base_dir == Path(".score-context")


class TestObservationFiltering:
    """Test observation filtering logic."""

    def test_should_record_high_importance(self, manager, sample_observation):
        """Test that high importance observations are recorded."""
        # Importance 7.5, coverage 0.85 - should pass
        assert manager.should_record_observation(sample_observation) is True

    def test_should_not_record_low_importance(self, manager, sample_observation):
        """Test that low importance observations are filtered."""
        sample_observation.importance_score = 3.0  # Below threshold
        assert manager.should_record_observation(sample_observation) is False

    def test_should_not_record_low_coverage(self, manager, sample_observation):
        """Test that low coverage observations are filtered."""
        sample_observation.coverage = 0.2  # Below threshold 0.3
        assert manager.should_record_observation(sample_observation) is False

    def test_should_record_edge_cases(self, manager, sample_observation):
        """Test edge cases at boundaries."""
        # Exactly at importance threshold
        sample_observation.importance_score = 5.0
        sample_observation.coverage = 0.3
        assert manager.should_record_observation(sample_observation) is True


class TestGraphUpdates:
    """Test graph update functionality."""

    def test_update_adds_new_nodes(self, manager, sample_observation):
        """Test that new nodes are added to graph."""
        graph = manager.update_local_graph(sample_observation)

        # Check discovered nodes are in graph
        assert "new_node_x" in graph.nodes
        assert "new_node_y" in graph.nodes

        # Verify node properties
        node_x = graph.nodes["new_node_x"]
        assert node_x.title == "New Service Contract"
        assert node_x.type == NodeType.CONTRACT

    def test_update_adds_new_edges(self, manager, sample_observation):
        """Test that edges are added to graph."""
        graph = manager.update_local_graph(sample_observation)

        # Check edges from route are in graph
        assert len(graph.edges) >= 2

        # Verify edge properties
        edges_a_b = [
            e for e in graph.edges if e.source == "node_a" and e.target == "node_b"
        ]
        assert len(edges_a_b) > 0

    def test_update_preserves_existing_graph(self, manager, sample_observation):
        """Test that existing graph is preserved."""
        # First update
        graph1 = manager.update_local_graph(sample_observation)
        node_count_1 = len(graph1.nodes)

        # Second update with different observation
        obs2 = sample_observation.model_copy()
        obs2.id = "obs__run_002"
        obs2.discovered_nodes = [
            DiscoveredNode(id="another_node", type="ISSUE", title="Bug Report")
        ]

        graph2 = manager.update_local_graph(obs2)

        # New nodes should be added to existing
        assert len(graph2.nodes) > node_count_1
        assert "new_node_x" in graph2.nodes  # Still there
        assert "another_node" in graph2.nodes  # New one added

    def test_duplicate_nodes_not_added_twice(self, manager, sample_observation):
        """Test that duplicate nodes aren't added twice."""
        graph1 = manager.update_local_graph(sample_observation)
        node_count = len(graph1.nodes)

        # Try to add same observation again
        graph2 = manager.update_local_graph(sample_observation)

        # Node count should not increase
        assert len(graph2.nodes) == node_count


class TestObservationIndex:
    """Test observation indexing."""

    def test_build_observation_index(self, manager, sample_observation):
        """Test index building."""
        index = manager.build_observation_index(sample_observation)

        assert index.obs_id == "obs__run_001"
        assert index.task_id == "task_001"
        assert index.verdict == "pass"
        assert index.importance == 7.5
        assert "node_a" in index.nodes
        assert ("node_a", "node_b", "depends_on") in index.edges

    def test_rebuild_full_index(self, manager, sample_observation):
        """Test rebuilding full index from log."""
        # First record an observation
        manager.record_observation(sample_observation)

        # Rebuild index
        full_index = manager.rebuild_full_index()

        assert "by_edge" in full_index
        assert "by_node" in full_index
        assert "by_task" in full_index

    def test_index_queries_by_task(self, manager, sample_observation):
        """Test querying observations by task."""
        # Record observation
        manager.record_observation(sample_observation)

        # Query by task
        results = manager.query_observations_by_task("task_001")

        assert len(results) > 0
        assert results[0].task_id == "task_001"

    def test_index_queries_by_edge(self, manager, sample_observation):
        """Test querying observations by edge."""
        # Record observation
        manager.record_observation(sample_observation)

        # Query by edge
        results = manager.query_observations_by_edge("node_a", "node_b", "depends_on")

        assert len(results) > 0
        # At least one observation should use this edge
        assert any("node_a" in obs.route.nodes for obs in results)


class TestRecordObservation:
    """Test complete observation recording."""

    def test_record_observation_full_flow(self, manager, sample_observation):
        """Test complete recording pipeline."""
        result_path = manager.record_observation(sample_observation)

        # Should return path to observation file
        assert result_path is not None
        assert result_path.exists()

        # Verify stored observation
        stored_data = json.loads(result_path.read_text())
        assert stored_data["id"] == "obs__run_001"
        assert stored_data["verdict"] == "pass"

    def test_record_observation_updates_index(self, manager, sample_observation):
        """Test that recording updates the index."""
        manager.record_observation(sample_observation)

        # Load and check index
        index = manager.load_index()

        assert "by_task" in index
        task_obs = index.get("by_task", {}).get("task_001", [])
        assert len(task_obs) > 0

    def test_record_low_importance_returns_none(self, manager, sample_observation):
        """Test that low importance observations return None."""
        sample_observation.importance_score = 2.0

        result = manager.record_observation(sample_observation)

        assert result is None

    def test_observation_not_recorded_twice(self, manager, sample_observation):
        """Test that same observation ID isn't recorded twice."""
        # Record twice
        path1 = manager.record_observation(sample_observation)
        path2 = manager.record_observation(sample_observation)

        # Should be same path
        assert path1 == path2

        # Both should exist and have same content
        if path1 and path2:
            content1 = path1.read_text()
            content2 = path2.read_text()
            assert content1 == content2


class TestLocalGraphPersistence:
    """Test local graph file persistence."""

    def test_graph_saved_to_disk(self, manager, sample_observation):
        """Test that graph is saved to disk."""
        manager.update_local_graph(sample_observation)

        graph_file = manager.graph_dir / "graph.json"
        assert graph_file.exists()

        # Verify structure
        graph_data = json.loads(graph_file.read_text())
        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert "timestamp" in graph_data

    def test_graph_loaded_from_disk(self, manager, sample_observation):
        """Test that graph is loaded from disk on next update."""
        # First update
        graph1 = manager.update_local_graph(sample_observation)
        node_count_1 = len(graph1.nodes)

        # Create new manager to simulate fresh start
        manager2 = LocalObservationManager(manager.base_dir)

        # Create different observation
        obs2 = sample_observation.model_copy()
        obs2.id = "obs__run_002"
        obs2.discovered_nodes = [
            DiscoveredNode(id="third_node", type="ISSUE", title="Another Issue")
        ]

        # Update with new manager
        graph2 = manager2.update_local_graph(obs2)

        # Should have both previous and new nodes
        assert len(graph2.nodes) > node_count_1
        assert "new_node_x" in graph2.nodes
        assert "third_node" in graph2.nodes


class TestIndexPersistence:
    """Test index file persistence."""

    def test_index_log_appends(self, manager, sample_observation):
        """Test that index log is append-only."""
        # Record first observation
        manager.record_observation(sample_observation)

        log_line_count_1 = 0
        if manager.index_log.exists():
            log_line_count_1 = len(manager.index_log.read_text().strip().split("\n"))

        # Record second observation
        obs2 = sample_observation.model_copy()
        obs2.id = "obs__run_002"
        manager.record_observation(obs2)

        log_line_count_2 = 0
        if manager.index_log.exists():
            log_line_count_2 = len(manager.index_log.read_text().strip().split("\n"))

        # Should have one more line
        assert log_line_count_2 > log_line_count_1

    def test_rebuild_index_from_log(self, manager, sample_observation):
        """Test that full index can be rebuilt from log."""
        # Record multiple observations
        obs_list = []
        for i in range(3):
            obs = sample_observation.model_copy()
            obs.id = f"obs__run_{i:03d}"
            obs.task_id = f"task_{i % 2:03d}"  # Mix of 2 tasks
            obs_list.append(obs)
            manager.record_observation(obs)

        # Rebuild index
        full_index = manager.rebuild_full_index()

        # Should have entries for both tasks
        by_task = full_index.get("by_task", {})
        assert len(by_task) > 0
