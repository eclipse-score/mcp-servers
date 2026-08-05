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

"""Experience learning data model: captured routes and class-level signals."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from score_context.schema.edges import EdgeRelation
from score_context.schema.provenance import Provenance


def _empty_traversals() -> list[Traversal]:
    return []


def _empty_route_hops() -> list[RouteHop]:
    return []


class Traversal(BaseModel):
    """One step in a route: source → target via relation."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    relation: EdgeRelation
    source_type: str = Field(min_length=1)
    target_type: str = Field(min_length=1)
    score_contributed: float
    reason: str = Field(min_length=1)


class Route(BaseModel):
    """The actual traversal path used to select context nodes."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    attempt: int = Field(ge=0)
    traversals: list[Traversal] = Field(default_factory=_empty_traversals)


class RouteHop(BaseModel):
    """One recorded graph hop, including its reusable edge class."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    relation: EdgeRelation
    source_type: str = Field(min_length=1)
    target_type: str = Field(min_length=1)


class ExperienceNode(BaseModel):
    """
    A recorded route + verdict. One experience artifact per harness run.
    Represents one navigation attempt through the graph for one task.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity
    id: str = Field(min_length=1)
    type: Literal["experience"]

    # Route metadata
    task_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    attempt: int = Field(ge=0)

    # The actual path taken
    route_edges: list[RouteHop] = Field(default_factory=_empty_route_hops)
    route_node_ids: list[str] = Field(default_factory=list)

    # Outcome
    verdict: Literal["pass", "fail"]
    surfaced_node_ids: list[str] = Field(default_factory=list)
    missing_node_ids: list[str] = Field(default_factory=list)

    # Quality signals
    coverage_ratio: float = Field(ge=0.0, le=1.0)
    path_length: int = Field(ge=0)

    # Provenance
    provenance: Provenance

    # Scoring context (for reproducibility)
    seed_node_ids: list[str] = Field(min_length=1)
    top_n: int = Field(ge=1)
    timestamp: datetime


class RouteObservationNode(BaseModel):
    """
    Aggregated statistics for a specific edge across many experiences.
    Derived by scanning experience artifacts.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: Literal["route_observation"]

    # Target
    relation: EdgeRelation
    source_type: str = Field(min_length=1)
    target_type: str = Field(min_length=1)

    # Aggregated signals
    success_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    total_uses: int = Field(ge=0)

    # Derived confidence
    success_ratio: float = Field(ge=0.0, le=1.0)
    confidence_trend: Literal["increasing", "stable", "decreasing"]

    # Metadata
    first_observed: datetime
    last_updated: datetime
    observed_in_experiments: list[str] = Field(default_factory=list)

    provenance: Provenance


class ConfidenceSignalNode(BaseModel):
    """
    Learning signal: the adjusted weight to apply to an edge for future scoring.
    Derived from RouteObservationNode statistics.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: Literal["confidence_signal"]

    # Target edge
    relation: EdgeRelation
    source_type: str = Field(min_length=1)
    target_type: str = Field(min_length=1)

    # Confidence adjustment
    base_weight: float = Field(ge=0.5)
    experience_adjustment: float = Field(ge=0.5, le=1.5)
    adjusted_weight: float = Field(ge=0.5)

    # Why this signal exists
    reason: str = Field(min_length=1)

    # Expiration
    created_at: datetime
    ttl_days: int = Field(ge=1, le=90)

    provenance: Provenance
