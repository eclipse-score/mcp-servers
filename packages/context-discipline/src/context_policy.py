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

"""Versioned, stdlib-only policy for context attention and overlays."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
from typing import Any, cast

POLICY_VERSION = 1


@dataclass(frozen=True)
class AttentionPolicy:
    w_semantic: float = 0.6
    w_structural: float = 0.4
    outcome_bonus: float = 0.2
    score_threshold: float = 0.15
    top_k: int = 5
    half_life_days: float = 30.0
    min_corroboration: int = 2

    def __post_init__(self) -> None:
        for field_name in (
            "w_semantic",
            "w_structural",
            "outcome_bonus",
            "score_threshold",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or not 0.0 <= value <= 1.0
            ):
                raise ValueError(f"{field_name} must be between 0.0 and 1.0")
        if type(self.top_k) is not int:
            raise ValueError("top_k must be an integer")
        if self.top_k < 1:
            raise ValueError("top_k must be at least 1")
        if (
            type(self.half_life_days) not in (int, float)
            or not isfinite(self.half_life_days)
            or self.half_life_days <= 0
        ):
            raise ValueError("half_life_days must be greater than 0")
        if type(self.min_corroboration) is not int:
            raise ValueError("min_corroboration must be an integer")
        if self.min_corroboration < 1:
            raise ValueError("min_corroboration must be at least 1")


@dataclass(frozen=True)
class PrivacyPolicy:
    retention_days: int = 90
    max_prior_chars: int = 800
    max_prior_total_chars: int = 4000

    def __post_init__(self) -> None:
        for field_name in (
            "retention_days",
            "max_prior_chars",
            "max_prior_total_chars",
        ):
            value = getattr(self, field_name)
            if type(value) is not int:
                raise ValueError(f"{field_name} must be an integer")
            if value < 1:
                raise ValueError(f"{field_name} must be at least 1")


@dataclass(frozen=True)
class OverlayPolicy:
    max_nodes: int = 20000
    max_edges: int = 60000
    max_title_chars: int = 200
    max_attribute_chars: int = 500
    max_attributes: int = 20
    max_added_nodes_per_change: int = 200
    max_added_edges_per_change: int = 400

    def __post_init__(self) -> None:
        for field_name in (
            "max_nodes",
            "max_edges",
            "max_title_chars",
            "max_attribute_chars",
            "max_attributes",
            "max_added_nodes_per_change",
            "max_added_edges_per_change",
        ):
            value = getattr(self, field_name)
            if type(value) is not int:
                raise ValueError(f"{field_name} must be an integer")
            if value < 1:
                raise ValueError(f"{field_name} must be at least 1")


@dataclass(frozen=True)
class Policy:
    version: int = POLICY_VERSION
    attention: AttentionPolicy = field(default_factory=AttentionPolicy)
    privacy: PrivacyPolicy = field(default_factory=PrivacyPolicy)
    overlay: OverlayPolicy = field(default_factory=OverlayPolicy)


_SECTION_FIELDS: dict[str, dict[str, type]] = {
    "attention": {
        "w_semantic": float,
        "w_structural": float,
        "outcome_bonus": float,
        "score_threshold": float,
        "top_k": int,
        "half_life_days": float,
        "min_corroboration": int,
    },
    "privacy": {
        "retention_days": int,
        "max_prior_chars": int,
        "max_prior_total_chars": int,
    },
    "overlay": {
        "max_nodes": int,
        "max_edges": int,
        "max_title_chars": int,
        "max_attribute_chars": int,
        "max_attributes": int,
        "max_added_nodes_per_change": int,
        "max_added_edges_per_change": int,
    },
}


def _validate_int(value: Any, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")


def _validate_float(value: Any, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number")


def _section_values(name: str, raw: Any) -> dict[str, Any]:
    if type(raw) is not dict:
        raise ValueError(f"{name} must be a TOML table")
    raw = cast(dict[str, Any], raw)
    expected = _SECTION_FIELDS[name]
    unknown = sorted(set(raw) - set(expected))
    if unknown:
        raise ValueError(f"unknown policy key {name}.{unknown[0]!r}")
    values = dict(raw)
    for field_name, field_type in expected.items():
        if field_name not in values:
            continue
        if field_type is int:
            _validate_int(values[field_name], f"{name}.{field_name}")
        else:
            _validate_float(values[field_name], f"{name}.{field_name}")
    return values


def load_policy(
    repo_path: str | Path, policy_file: str = "score-context/policy.toml"
) -> Policy:
    """Load the repository policy, returning defaults when it is absent."""
    repo = Path(repo_path).expanduser().resolve()
    path = Path(policy_file).expanduser()
    policy_path = path if path.is_absolute() else repo / path
    if not policy_path.exists():
        return Policy()
    with policy_path.open("rb") as stream:
        raw = tomllib.load(stream)
    if type(raw) is not dict:
        raise ValueError("policy must be a TOML table")
    if "version" not in raw:
        raise ValueError("policy version is required")
    _validate_int(raw["version"], "version")
    if raw["version"] != POLICY_VERSION:
        raise ValueError(f"unknown policy version: {raw['version']!r}")
    unknown_sections = sorted(set(raw) - {"version", *_SECTION_FIELDS})
    if unknown_sections:
        raise ValueError(f"unknown policy section {unknown_sections[0]!r}")
    return Policy(
        version=raw["version"],
        attention=AttentionPolicy(
            **_section_values("attention", raw.get("attention", {}))
        ),
        privacy=PrivacyPolicy(**_section_values("privacy", raw.get("privacy", {}))),
        overlay=OverlayPolicy(**_section_values("overlay", raw.get("overlay", {}))),
    )
