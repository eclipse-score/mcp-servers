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

from pathlib import Path

import pytest
from context_policy import (
    AttentionPolicy,
    OverlayPolicy,
    PrivacyPolicy,
    load_policy,
)


def test_missing_policy_uses_defaults(tmp_path: Path) -> None:
    policy = load_policy(tmp_path)
    assert policy.attention == AttentionPolicy()
    assert policy.privacy == PrivacyPolicy()
    assert policy.overlay == OverlayPolicy()


def test_policy_loads_written_values(tmp_path: Path) -> None:
    policy_path = tmp_path / "score-context" / "policy.toml"
    policy_path.parent.mkdir()
    policy_path.write_text(
        """
version = 1
[attention]
top_k = 3
half_life_days = 12
selection = "threshold"
rank_gap_ratio = 0.7
noise_floor = 0.04
live_ratio_floor = 0.3
outcome_reward = 0.1
structural_hops = 0
max_focus_nodes = 42
min_structural_ground = 3
[privacy]
retention_days = 10
[overlay]
max_nodes = 7
""",
        encoding="utf-8",
    )
    policy = load_policy(tmp_path)
    assert policy.attention.top_k == 3
    assert policy.attention.half_life_days == 12
    assert policy.attention.selection == "threshold"
    assert policy.attention.rank_gap_ratio == 0.7
    assert policy.attention.noise_floor == 0.04
    assert policy.attention.live_ratio_floor == 0.3
    assert policy.attention.outcome_reward == 0.1
    assert policy.attention.structural_hops == 0
    assert policy.attention.max_focus_nodes == 42
    assert policy.attention.min_structural_ground == 3
    assert policy.privacy.retention_days == 10
    assert policy.overlay.max_nodes == 7


def test_unknown_policy_version_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "policy.toml"
    path.write_text("version = 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown policy version"):
        load_policy(tmp_path, "policy.toml")


def test_unknown_policy_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "policy.toml"
    path.write_text("version = 1\n[privacy]\nunknown = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown"):
        load_policy(tmp_path, "policy.toml")


def test_unknown_policy_section_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "policy.toml"
    path.write_text("version = 1\n[unknown]\nvalue = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown"):
        load_policy(tmp_path, "policy.toml")


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("attention", "score_threshold", 1.1),
        ("attention", "noise_floor", 1.1),
        ("attention", "live_ratio_floor", 1.1),
        ("attention", "max_focus_nodes", 0),
        ("attention", "min_structural_ground", 0),
        ("privacy", "retention_days", 0),
        ("overlay", "max_nodes", 0),
    ],
)
def test_policy_rejects_out_of_range_values(
    tmp_path: Path, section: str, field: str, value: float | int
) -> None:
    path = tmp_path / "policy.toml"
    path.write_text(
        f"version = 1\n[{section}]\n{field} = {value}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=field):
        load_policy(tmp_path, "policy.toml")


def test_policy_rejects_float_for_integer_field(tmp_path: Path) -> None:
    path = tmp_path / "policy.toml"
    path.write_text("version = 1\n[overlay]\nmax_nodes = 1.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="max_nodes"):
        load_policy(tmp_path, "policy.toml")


@pytest.mark.parametrize("selection", ["invalid", 1, True])
def test_policy_rejects_invalid_selection(tmp_path: Path, selection: object) -> None:
    path = tmp_path / "policy.toml"
    value = f'"{selection}"' if isinstance(selection, str) else str(selection).lower()
    path.write_text(
        f"version = 1\n[attention]\nselection = {value}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="selection"):
        load_policy(tmp_path, "policy.toml")


def test_policy_rejects_out_of_range_rank_gap_ratio(tmp_path: Path) -> None:
    path = tmp_path / "policy.toml"
    path.write_text(
        "version = 1\n[attention]\nrank_gap_ratio = 1.1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="rank_gap_ratio"):
        load_policy(tmp_path, "policy.toml")


def test_policy_rejects_out_of_range_noise_floor(tmp_path: Path) -> None:
    path = tmp_path / "policy.toml"
    path.write_text(
        "version = 1\n[attention]\nnoise_floor = -0.1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="noise_floor"):
        load_policy(tmp_path, "policy.toml")


@pytest.mark.parametrize("hops", [-1, 2, 1.0, True])
def test_policy_rejects_invalid_structural_hops(tmp_path: Path, hops: object) -> None:
    path = tmp_path / "policy.toml"
    value = str(hops).lower() if not isinstance(hops, str) else f'"{hops}"'
    path.write_text(
        f"version = 1\n[attention]\nstructural_hops = {value}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="structural_hops"):
        load_policy(tmp_path, "policy.toml")
