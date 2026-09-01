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

"""Append-only persistence and deterministic class-level aggregation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast

from score_context.policy import Policy
from score_context.schema.experience import ExperienceNode


class _ClassStats(TypedDict):
    relation: str
    source_type: str
    target_type: str
    success_count: int
    failure_count: int


class ExperiencePersistence:
    """Store immutable experiences and one derived class-weight file."""

    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.experiences_path = self.artifacts_dir / "experiences.jsonl"
        self.weights_path = self.artifacts_dir / "weights.json"

    def append_experience(self, exp: ExperienceNode) -> Path:
        """Append exactly one canonical JSON object to the experience log."""
        payload = json.dumps(
            exp.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        with self.experiences_path.open("a", encoding="utf-8") as handle:
            handle.write(payload + "\n")
        return self.experiences_path

    def _load_experiences(self) -> list[ExperienceNode]:
        if not self.experiences_path.exists():
            return []
        experiences: list[ExperienceNode] = []
        for line in self.experiences_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                experiences.append(ExperienceNode.model_validate(json.loads(line)))
        return experiences

    def aggregate(self, policy: Policy) -> Path:
        """Aggregate each edge class and write deterministic weights."""
        stats: dict[tuple[str, str, str], _ClassStats] = {}
        experiences = self._load_experiences()
        latest = max(
            (exp.timestamp for exp in experiences),
            default=datetime.fromtimestamp(0, UTC),
        )

        for exp in experiences:
            classes = {
                (hop.relation.value, hop.source_type, hop.target_type)
                for hop in exp.route_edges
            }
            for relation, source_type, target_type in sorted(classes):
                key = (relation, source_type, target_type)
                if key not in stats:
                    stats[key] = {
                        "relation": relation,
                        "source_type": source_type,
                        "target_type": target_type,
                        "success_count": 0,
                        "failure_count": 0,
                    }
                count_key = (
                    "success_count" if exp.verdict == "pass" else "failure_count"
                )
                stats[key][count_key] += 1

        rows: list[dict[str, object]] = []
        learning = policy.learning
        for key in sorted(stats):
            item = stats[key]
            uses = item["success_count"] + item["failure_count"]
            ratio = item["success_count"] / uses if uses else 0.0
            age_days = max(
                0.0,
                (latest - _latest_for_class(experiences, key)).total_seconds() / 86400,
            )
            recency = 0.5 ** (age_days / learning.half_life_days)
            if uses >= learning.min_uses and ratio >= learning.boost_ratio:
                multiplier = min(
                    learning.boost_cap,
                    1.0 + (learning.boost_cap - 1.0) * recency,
                )
                reason = f"boosted_{item['success_count']}_of_{uses}_uses"
            elif uses >= learning.min_uses and ratio <= learning.dampen_ratio:
                multiplier = max(
                    learning.dampen_floor,
                    1.0 - (1.0 - learning.dampen_floor) * recency,
                )
                reason = f"dampened_{item['failure_count']}_of_{uses}_uses"
            else:
                multiplier = policy.scoring.neutral_multiplier
                reason = f"neutral_{uses}_uses"
            rows.append(
                {
                    "relation": item["relation"],
                    "source_type": item["source_type"],
                    "target_type": item["target_type"],
                    "base_weight": policy.base_weights.get(
                        item["relation"],
                        policy.scoring.default_relation_weight,
                    ),
                    "success_count": item["success_count"],
                    "failure_count": item["failure_count"],
                    "success_ratio": ratio,
                    "multiplier": multiplier,
                    "reason": reason,
                }
            )

        payload = json.dumps({"weights": rows}, indent=2, sort_keys=True) + "\n"
        self.weights_path.write_text(payload, encoding="utf-8")
        return self.weights_path

    def load_weights(self) -> dict[tuple[str, str, str], float]:
        """Read only the derived weights file for future scoring."""
        if not self.weights_path.exists():
            return {}
        raw = json.loads(self.weights_path.read_text(encoding="utf-8"))
        rows = cast(object, raw.get("weights", []))
        if not isinstance(rows, list):
            raise ValueError("weights.json.weights must be a list")
        weights: dict[tuple[str, str, str], float] = {}
        for row in cast(list[object], rows):
            if not isinstance(row, dict):
                raise ValueError("weights.json row must be an object")
            typed_row = cast(dict[str, object], row)
            multiplier = typed_row["multiplier"]
            if not isinstance(multiplier, (int, float, str)):
                raise ValueError("weights.json multiplier must be numeric")
            weights[
                (
                    str(typed_row["relation"]),
                    str(typed_row["source_type"]),
                    str(typed_row["target_type"]),
                )
            ] = float(multiplier)
        return weights


def _latest_for_class(
    experiences: list[ExperienceNode],
    edge_class: tuple[str, str, str],
) -> datetime:
    matching = [
        exp.timestamp
        for exp in experiences
        if edge_class
        in {
            (hop.relation.value, hop.source_type, hop.target_type)
            for hop in exp.route_edges
        }
    ]
    return max(matching, default=datetime.fromtimestamp(0, UTC))
