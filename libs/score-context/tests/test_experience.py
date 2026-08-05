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

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from score_context.harness.experience import ExperiencePersistence
from score_context.policy import LearningPolicy, Policy, ScoringPolicy
from score_context.schema.edges import EdgeRelation
from score_context.schema.experience import ExperienceNode, RouteHop
from score_context.schema.provenance import Provenance


def _experience(verdict: str, run_id: str) -> ExperienceNode:
    return ExperienceNode(
        id=f"exp_{run_id}",
        type="experience",
        task_id="task",
        run_id=run_id,
        attempt=0,
        route_edges=[
            RouteHop(
                source_id="pr_a",
                target_id="dec_a",
                relation=EdgeRelation.DISCUSSED_IN,
                source_type="pull_request",
                target_type="dec_rec",
            )
        ],
        verdict=cast(Literal["pass", "fail"], verdict),
        coverage_ratio=1.0 if verdict == "pass" else 0.0,
        path_length=1,
        provenance=Provenance(
            repo="test",
            adapter="test",
            confidence=1.0,
            observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        seed_node_ids=["pr_a"],
        top_n=2,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _policy() -> Policy:
    return Policy(
        base_weights={"discussed_in": 2.5},
        learning=LearningPolicy(
            min_uses=3,
            boost_ratio=0.8,
            dampen_ratio=0.3,
            boost_cap=1.5,
            dampen_floor=0.5,
            half_life_days=14,
        ),
        scoring=ScoringPolicy(
            seed_score=100.0,
            degree_factor=0.1,
            freshness_years=365.0,
            default_relation_weight=1.0,
            neutral_multiplier=1.0,
        ),
    )


def test_append_and_class_aggregate_are_idempotent(tmp_path: Path) -> None:
    persistence = ExperiencePersistence(tmp_path)
    persistence.append_experience(_experience("pass", "1"))
    persistence.append_experience(_experience("pass", "2"))
    persistence.append_experience(_experience("pass", "3"))

    assert len(persistence.experiences_path.read_text().splitlines()) == 3
    persistence.aggregate(_policy())
    first = persistence.weights_path.read_bytes()
    persistence.aggregate(_policy())
    assert persistence.weights_path.read_bytes() == first

    rows = json.loads(first)["weights"]
    assert rows[0]["relation"] == "discussed_in"
    assert rows[0]["source_type"] == "pull_request"
    assert rows[0]["target_type"] == "dec_rec"
    assert persistence.load_weights() == {
        ("discussed_in", "pull_request", "dec_rec"): 1.5
    }
