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


class EdgeRelation(StrEnum):
    """Superset of score_metamodel links and ADR trace relations."""

    # Relations reused from score_metamodel.yaml needs_extra_links.
    CONTAINS = "contains"
    HAS = "has"
    INPUT = "input"
    OUTPUT = "output"
    RESPONSIBLE = "responsible"
    APPROVED_BY = "approved_by"
    SUPPORTED_BY = "supported_by"
    COMPLIES = "complies"
    REALIZES = "realizes"
    DERIVED_FROM = "derived_from"
    COVERS = "covers"
    CONSISTS_OF = "consists_of"
    BELONGS_TO = "belongs_to"
    SATISFIED_BY = "satisfied_by"
    SATISFIES = "satisfies"
    FULFILS = "fulfils"
    IMPLEMENTS = "implements"
    USES = "uses"
    PROVIDES = "provides"
    INCLUDES = "includes"
    INCLUDED_BY = "included_by"
    MITIGATED_BY = "mitigated_by"
    VIOLATES = "violates"
    FULLY_VERIFIES = "fully_verifies"
    PARTIALLY_VERIFIES = "partially_verifies"

    # New relations from the ADR trace model.
    AFFECTS = "affects"
    DEPENDS_ON = "depends_on"
    DISCUSSED_IN = "discussed_in"
    BLOCKS = "blocks"
    SUPERSEDES = "supersedes"
    CONFLICTS_WITH = "conflicts_with"
    AUTHORED_BY = "authored_by"
    OWNS = "owns"


class Edge(BaseModel):
    """A typed, provenance-bearing relation between two natural-key nodes."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    relation: EdgeRelation
    provenance: Provenance
    attributes: dict[str, str] = Field(default_factory=dict)


# ADR terminology is mapped to the existing vocabulary where semantics overlap.
ADR_RELATION_MAPPINGS: dict[str, tuple[str, ...]] = {
    "implements": ("implements",),
    "verifies": ("fully_verifies", "partially_verifies"),
    "supersedes": ("supersedes", "dec_rec.status transition to superseded"),
    "affects": ("affects",),
    "depends_on": ("depends_on",),
    "discussed_in": ("discussed_in",),
    "blocks": ("blocks",),
    "conflicts_with": ("conflicts_with",),
    "authored_by": ("authored_by",),
    "owns": ("owns",),
}
