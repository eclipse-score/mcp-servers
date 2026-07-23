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

from datetime import UTC, datetime

from score_context import (
    ContextDelta,
    Edge,
    EdgeRelation,
    Node,
    NodeType,
    Provenance,
    Signal,
    SourceRef,
    UpsertEdge,
    UpsertNode,
)


def test_context_delta_json_round_trip() -> None:
    observed_at = datetime(2026, 1, 1, tzinfo=UTC)
    provenance = Provenance(
        repo="eclipse-score/example",
        sha="abc123",
        adapter="needs",
        confidence=1.0,
        observed_at=observed_at,
    )
    delta = ContextDelta(
        signal=Signal(
            type="contract_change",
            source=SourceRef(repo="eclipse-score/example", ref="pull/42", sha="abc123"),
            provenance=provenance,
            weight=0.92,
            decays=True,
        ),
        graph_ops=[
            UpsertNode(
                node=Node(
                    id="contract__example__v1",
                    type=NodeType.CONTRACT,
                    title="Example contract",
                    provenance=provenance,
                )
            ),
            UpsertEdge(
                edge=Edge(
                    source="pull/42",
                    target="contract__example__v1",
                    relation=EdgeRelation.AFFECTS,
                    provenance=provenance,
                )
            ),
        ],
    )
    restored = ContextDelta.model_validate_json(delta.model_dump_json())
    assert restored == delta
