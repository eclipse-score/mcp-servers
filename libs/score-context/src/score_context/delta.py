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

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from score_context.schema.edges import Edge
from score_context.schema.nodes import Node
from score_context.schema.provenance import Provenance, SourceRef


class Signal(BaseModel):
    """Source-local attention signal carried by a context delta."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1)
    source: SourceRef
    provenance: Provenance
    weight: float
    decays: bool


class UpsertNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["upsert_node"] = "upsert_node"
    node: Node


class UpsertEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["upsert_edge"] = "upsert_edge"
    edge: Edge


GraphOp = Annotated[UpsertNode | UpsertEdge, Field(discriminator="op")]


class ContextDelta(BaseModel):
    """The only normalized unit future source adapters emit."""

    model_config = ConfigDict(extra="forbid")

    signal: Signal
    graph_ops: list[GraphOp]
