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

"""Git-native persistence for experience learning artifacts."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from score_context.schema.edges import EdgeRelation
from score_context.schema.experience import (
    ConfidenceSignalNode,
    ExperienceNode,
    RouteObservationNode,
)
from score_context.schema.provenance import Provenance


class ExperiencePersistence:
    """Manages reading and writing experience artifacts to disk."""

    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = Path(artifacts_dir)
        self.experiences_dir = self.artifacts_dir / "experiences"
        self.observations_dir = self.artifacts_dir / "observations"
        self.signals_dir = self.artifacts_dir / "confidence_signals"

        # Create directories
        self.experiences_dir.mkdir(parents=True, exist_ok=True)
        self.observations_dir.mkdir(parents=True, exist_ok=True)
        self.signals_dir.mkdir(parents=True, exist_ok=True)

    def save_experience(self, exp: ExperienceNode) -> Path:
        """Write an experience artifact to disk."""
        task_dir = self.experiences_dir / exp.task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        path = task_dir / f"{exp.id}.json"
        path.write_text(
            exp.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path

    def save_observation(self, obs: RouteObservationNode) -> Path:
        """Write a route observation artifact to disk."""
        path = self.observations_dir / f"{obs.id}.json"
        path.write_text(
            obs.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path

    def save_signal(self, sig: ConfidenceSignalNode) -> Path:
        """Write a confidence signal artifact to disk."""
        path = self.signals_dir / f"{sig.id}.json"
        path.write_text(
            sig.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path

    def load_all_experience_weights(
        self,
    ) -> dict[tuple[str, str, EdgeRelation], float]:
        """Load all confidence signals and return as weight dict."""
        weights: dict[tuple[str, str, EdgeRelation], float] = {}

        if not self.signals_dir.exists():
            return weights

        for signal_file in self.signals_dir.glob("*.json"):
            try:
                data = json.loads(signal_file.read_text(encoding="utf-8"))
                sig = ConfidenceSignalNode(**data)

                # Apply TTL decay
                age_days = (datetime.now(UTC) - sig.created_at).days
                if age_days > sig.ttl_days:
                    # Signal expires; decay weight toward 1.0
                    decay = max(0.5, 1.0 - (age_days - sig.ttl_days) / 30.0)
                    adjusted = 1.0 + (sig.adjusted_weight - 1.0) * decay
                else:
                    adjusted = sig.adjusted_weight

                key = (sig.source_id, sig.target_id, sig.relation)
                weights[key] = adjusted
            except (json.JSONDecodeError, ValueError) as e:
                # Skip malformed signal files
                print(f"Warning: skipping malformed signal file {signal_file}: {e}")
                continue

        return weights

    def aggregate_observations(self) -> None:
        """
        Scan all experience artifacts and update observation aggregates.
        Called after a batch of harness runs.
        """
        if not self.experiences_dir.exists():
            return

        # Aggregate by edge
        edge_stats: dict[tuple[str, str, str], dict[str, object]] = {}

        for exp_file in self.experiences_dir.rglob("*.json"):
            try:
                data = json.loads(exp_file.read_text(encoding="utf-8"))
                exp = ExperienceNode(**data)

                for source, target, relation in exp.route_edges:
                    key = (source, target, relation)
                    if key not in edge_stats:
                        edge_stats[key] = {
                            "successes": 0,
                            "failures": 0,
                            "first_observed": exp.provenance.observed_at,
                            "last_observed": exp.provenance.observed_at,
                            "experiments": set(),
                        }

                    if exp.verdict == "pass":
                        edge_stats[key]["successes"] = (
                            cast(int, edge_stats[key]["successes"]) + 1
                        )
                    else:
                        edge_stats[key]["failures"] = (
                            cast(int, edge_stats[key]["failures"]) + 1
                        )

                    # Update last_observed
                    if exp.provenance.observed_at > cast(
                        datetime, edge_stats[key]["last_observed"]
                    ):
                        edge_stats[key]["last_observed"] = exp.provenance.observed_at

                    # Add task to experiments set
                    experiments_set: set[str] = cast(
                        set[str], edge_stats[key]["experiments"]
                    )
                    experiments_set.add(exp.task_id)
            except (json.JSONDecodeError, ValueError) as e:
                # Skip malformed experience files
                print(f"Warning: skipping malformed experience file {exp_file}: {e}")
                continue

        # Write observation nodes
        for (source, target, relation), stats in edge_stats.items():
            successes = cast(int, stats["successes"])
            failures = cast(int, stats["failures"])
            total = successes + failures
            ratio = successes / total if total > 0 else 0.0

            # Determine trend
            if successes >= 3 and ratio >= 0.8:
                trend = "increasing"
            elif failures >= 2 and ratio <= 0.3:
                trend = "decreasing"
            else:
                trend = "stable"

            obs = RouteObservationNode(
                id=f"obs_{source}_{target}_{relation}",
                type="route_observation",
                source_id=source,
                target_id=target,
                relation=cast(EdgeRelation, relation),
                success_count=successes,
                failure_count=failures,
                total_uses=total,
                success_ratio=ratio,
                confidence_trend=trend,
                first_observed=cast(datetime, stats["first_observed"]),
                last_updated=datetime.now(UTC),
                observed_in_experiments=list(cast(set[str], stats["experiments"])),
                provenance=Provenance(
                    repo="graph",
                    adapter="experience_learning",
                    confidence=1.0,
                    observed_at=datetime.now(UTC),
                ),
            )

            self.save_observation(obs)

            # Derive confidence signal
            signal = _compute_confidence_signal(obs)
            self.save_signal(signal)


def _compute_confidence_signal(obs: RouteObservationNode) -> ConfidenceSignalNode:
    """
    Compute the confidence adjustment for an edge based on observation statistics.

    Rules:
    - success_ratio >= 0.8 AND total_uses >= 3 → boost up to 1.3
    - success_ratio <= 0.3 AND total_uses >= 2 → dampen down to 0.5
    - Otherwise → 1.0 (no adjustment)
    """
    # Base weights from context.py
    BASE_WEIGHTS = {
        "affects": 3.0,
        "blocks": 3.0,
        "discussed_in": 2.5,
        "implements": 2.0,
        "depends_on": 2.0,
    }

    base_weight = BASE_WEIGHTS.get(obs.relation.value, 1.0)

    if obs.success_count >= 3 and obs.success_ratio >= 0.8:
        # Boost: successful route
        age_days = (datetime.now(UTC) - obs.last_updated).days
        recency_factor = 1.0 / (1.0 + age_days / 7.0)
        adjustment = 1.0 + (0.3 * recency_factor)  # Up to 1.3
        reason = f"passed_in_{obs.success_count}_runs"
    elif obs.failure_count >= 2 and obs.success_ratio <= 0.3:
        # Dampen: failed route
        age_days = (datetime.now(UTC) - obs.last_updated).days
        recency_factor = 1.0 / (1.0 + age_days / 7.0)
        adjustment = 1.0 - (0.5 * recency_factor)  # Down to 0.5
        reason = f"failed_in_{obs.failure_count}_runs"
    else:
        # Neutral
        adjustment = 1.0
        reason = f"mixed_results_{obs.total_uses}_runs"

    return ConfidenceSignalNode(
        id=f"conf_{obs.source_id}_{obs.target_id}_{obs.relation}",
        type="confidence_signal",
        source_id=obs.source_id,
        target_id=obs.target_id,
        relation=obs.relation,
        base_weight=base_weight,
        experience_adjustment=adjustment,
        adjusted_weight=base_weight * adjustment,
        reason=reason,
        created_at=datetime.now(UTC),
        ttl_days=30,
        provenance=Provenance(
            repo="graph",
            adapter="experience_learning",
            confidence=1.0,
            observed_at=datetime.now(UTC),
        ),
    )
