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

"""Agent observation model: what was learned from a task run."""

from datetime import datetime

from pydantic import BaseModel, Field


class RouteEdge(BaseModel):
    """An edge traversed during task execution."""

    source: str
    target: str
    relation: str
    weight_used: float
    score_contributed: float | None = None


class RouteNode(BaseModel):
    """A node visited during task execution."""

    id: str
    entry_time: datetime | None = None
    exit_time: datetime | None = None


class DiscoveredNode(BaseModel):
    """A new node discovered by agent during traversal."""

    id: str
    type: str
    title: str
    source: str = "agent_discovery"
    confidence: float = Field(default=0.95, ge=0, le=1)
    repo: str | None = None
    url: str | None = None


class Route(BaseModel):
    """The complete path taken through the graph."""

    nodes: list[str]  # List of node IDs in order
    edges: list[RouteEdge]


class AgentObservation(BaseModel):
    """
    Complete observation from one agent task run.

    Contains:
    - What route was taken (edges traversed)
    - What new nodes were discovered
    - Whether the task succeeded
    - Quality metrics
    """

    id: str = Field(description="Unique observation ID (obs__{run_id})")
    agent_id: str = Field(description="ID of agent that ran task")
    task_id: str = Field(description="Which task was evaluated")
    timestamp: datetime = Field(description="When observation was recorded")

    # ROUTING DATA
    route: Route = Field(description="Path taken through graph")

    # GRAPH EVOLUTION DATA
    discovered_nodes: list[DiscoveredNode] = Field(
        default_factory=list, description="New nodes encountered"
    )

    # VERDICT
    verdict: str = Field(description="pass or fail", pattern="^(pass|fail)$")

    # QUALITY METRICS
    coverage: float = Field(
        default=1.0, ge=0, le=1, description="Fraction of expected nodes found"
    )
    importance_score: float = Field(
        default=5.0,
        ge=0,
        le=10,
        description="Agent's rating of observation importance (0-10)",
    )

    class Config:
        """Allow datetime serialization."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class ObservationIndex(BaseModel):
    """
    Index entry for fast lookup of observations.
    Stored as jsonl in observation_index.jsonl.
    """

    obs_id: str
    task_id: str
    timestamp: datetime
    verdict: str
    edges: list[tuple[str, str, str]]  # List of (source, target, relation)
    nodes: list[str]  # List of node IDs traversed
    importance: float
    source_repo: str | None = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
