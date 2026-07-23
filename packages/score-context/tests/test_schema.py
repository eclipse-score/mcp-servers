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

import pytest
from pydantic import ValidationError
from score_context.schema.edges import Edge, EdgeRelation
from score_context.schema.nodes import NEEDS_MODEL_TYPES, Node, NodeType
from score_context.schema.provenance import Provenance


def provenance() -> Provenance:
    return Provenance(
        repo="eclipse-score/example",
        adapter="test",
        confidence=1.0,
        observed_at=datetime.now(UTC),
    )


def test_node_and_edge_construction() -> None:
    node = Node(
        id="stkh_req__example__1",
        type=NodeType.STKH_REQ,
        title="Example requirement",
        provenance=provenance(),
    )
    edge = Edge(
        source=node.id,
        target="feat__example__1",
        relation=EdgeRelation.SATISFIED_BY,
        provenance=provenance(),
    )
    assert node.type == NodeType.STKH_REQ
    assert edge.relation == EdgeRelation.SATISFIED_BY


def test_invalid_node_and_edge_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Node.model_validate(
            {
                "id": "",
                "type": "not-a-node-type",
                "title": "invalid",
                "provenance": provenance().model_dump(),
            }
        )
    with pytest.raises(ValidationError):
        Edge.model_validate(
            {
                "source": "a",
                "target": "b",
                "relation": "not-a-relation",
                "provenance": provenance().model_dump(),
            }
        )


def test_needs_types_match_metamodel_type_ids() -> None:
    metamodel = """
    tsf tenet assertion std_req std_wp workflow gd_req gd_temp gd_chklst
    gd_guidl gd_method workproduct role doc_concept doc_getstrt document doc_tool
    stkh_req feat_req comp_req tool_req aou_req feat feat_arc_sta feat_arc_dyn
    logic_arc_int logic_arc_int_op mod mod_view_sta mod_view_dyn comp comp_arc_sta
    comp_arc_dyn real_arc_int real_arc_int_op review_header plat_saf_dfa
    feat_saf_dfa comp_saf_dfa feat_saf_fmea comp_saf_fmea feat_sec_threat
    comp_sec_threat plat_sec_threat feat_sec_ana comp_sec_ana plat_sec_ana
    testcase dec_rec
    """
    expected = frozenset(metamodel.split())
    assert expected == NEEDS_MODEL_TYPES
