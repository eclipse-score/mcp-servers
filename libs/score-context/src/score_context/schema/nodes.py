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

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from score_context.schema.provenance import Provenance


class NodeType(StrEnum):
    """Node vocabulary split between S-CORE needs and trace/event sources."""

    # Needs-model nodes: identifiers reused from score_metamodel.yaml.
    TSF = "tsf"
    TENET = "tenet"
    ASSERTION = "assertion"
    STD_REQ = "std_req"
    STD_WP = "std_wp"
    WORKFLOW = "workflow"
    GD_REQ = "gd_req"
    GD_TEMP = "gd_temp"
    GD_CHKLST = "gd_chklst"
    GD_GUIDL = "gd_guidl"
    GD_METHOD = "gd_method"
    WORKPRODUCT = "workproduct"
    ROLE = "role"
    DOC_CONCEPT = "doc_concept"
    DOC_GETSTRT = "doc_getstrt"
    DOCUMENT = "document"
    DOC_TOOL = "doc_tool"
    STKH_REQ = "stkh_req"
    FEAT_REQ = "feat_req"
    COMP_REQ = "comp_req"
    TOOL_REQ = "tool_req"
    AOU_REQ = "aou_req"
    FEAT = "feat"
    FEAT_ARC_STA = "feat_arc_sta"
    FEAT_ARC_DYN = "feat_arc_dyn"
    LOGIC_ARC_INT = "logic_arc_int"
    LOGIC_ARC_INT_OP = "logic_arc_int_op"
    MOD = "mod"
    MOD_VIEW_STA = "mod_view_sta"
    MOD_VIEW_DYN = "mod_view_dyn"
    COMP = "comp"
    COMP_ARC_STA = "comp_arc_sta"
    COMP_ARC_DYN = "comp_arc_dyn"
    REAL_ARC_INT = "real_arc_int"
    REAL_ARC_INT_OP = "real_arc_int_op"
    REVIEW_HEADER = "review_header"
    PLAT_SAF_DFA = "plat_saf_dfa"
    FEAT_SAF_DFA = "feat_saf_dfa"
    COMP_SAF_DFA = "comp_saf_dfa"
    FEAT_SAF_FMEA = "feat_saf_fmea"
    COMP_SAF_FMEA = "comp_saf_fmea"
    FEAT_SEC_THREAT = "feat_sec_threat"
    COMP_SEC_THREAT = "comp_sec_threat"
    PLAT_SEC_THREAT = "plat_sec_threat"
    FEAT_SEC_ANA = "feat_sec_ana"
    COMP_SEC_ANA = "comp_sec_ana"
    PLAT_SEC_ANA = "plat_sec_ana"
    TESTCASE = "testcase"
    DEC_REC = "dec_rec"

    # Trace/event nodes: new vocabulary, intentionally outside sphinx-needs.
    ISSUE = "issue"
    DISCUSSION = "discussion"
    PULL_REQUEST = "pull_request"
    COMMIT = "commit"
    CODE_CHANGE = "code_change"
    CONTRACT = "contract"
    REPO = "repo"
    MODULE = "module"
    TEAM = "team"
    PERSON = "person"
    ARTIFACT = "artifact"
    CI_RESULT = "ci_result"

    # Experience learning nodes (Phase 2).
    EXPERIENCE = "experience"
    ROUTE_OBSERVATION = "route_observation"
    CONFIDENCE_SIGNAL = "confidence_signal"


NEEDS_MODEL_TYPES = frozenset(
    node_type.value
    for node_type in NodeType
    if node_type.value
    not in {
        "issue",
        "discussion",
        "pull_request",
        "commit",
        "code_change",
        "contract",
        "repo",
        "module",
        "team",
        "person",
        "artifact",
        "ci_result",
        "experience",
        "route_observation",
        "confidence_signal",
    }
)


class Node(BaseModel):
    """A graph node identified by an existing natural key."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: NodeType
    title: str = Field(min_length=1)
    safety: str | None = None
    provenance: Provenance
    attributes: dict[str, str] = Field(default_factory=dict)
