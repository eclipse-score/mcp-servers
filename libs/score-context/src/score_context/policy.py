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

"""Scoring and experience-learning policy loaded from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class LearningPolicy(BaseModel):
    """Tunable thresholds and bounds for class-level learning."""

    model_config = ConfigDict(extra="forbid")

    min_uses: int = Field(ge=1)
    boost_ratio: float = Field(ge=0.0, le=1.0)
    dampen_ratio: float = Field(ge=0.0, le=1.0)
    boost_cap: float = Field(ge=1.0)
    dampen_floor: float = Field(gt=0.0, le=1.0)
    half_life_days: int = Field(ge=1)


class ScoringPolicy(BaseModel):
    """First-cut scorer constants kept outside the scoring implementation."""

    model_config = ConfigDict(extra="forbid")

    seed_score: float = Field(gt=0.0)
    degree_factor: float = Field(ge=0.0)
    freshness_years: float = Field(gt=0.0)
    default_relation_weight: float = Field(gt=0.0)
    neutral_multiplier: float = Field(gt=0.0)


class Policy(BaseModel):
    """All configurable relation weights and learning knobs."""

    model_config = ConfigDict(extra="forbid")

    base_weights: dict[str, float]
    learning: LearningPolicy
    scoring: ScoringPolicy

    @classmethod
    def from_yaml(cls, path: Path) -> Policy:
        """Load and validate one policy YAML document."""
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("policy must be a YAML object")
        return cls.model_validate(raw)


DEFAULT_POLICY = Policy(
    base_weights={
        "affects": 3.0,
        "blocks": 3.0,
        "discussed_in": 2.5,
        "implements": 2.0,
        "depends_on": 2.0,
    },
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


def load_policy(path: Path | None = None) -> Policy:
    """Load a policy when available, otherwise return standalone defaults."""
    if path is None:
        return DEFAULT_POLICY
    return Policy.from_yaml(path)
