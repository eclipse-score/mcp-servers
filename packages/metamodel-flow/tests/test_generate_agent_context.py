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
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from generate_agent_context import (
    build_projection,
    load_metamodel_yaml,
    render_projection,
)

MODEL_DIR = Path(__file__).parent / "data"
SIMPLE_MODEL_PATH = MODEL_DIR / "simple_model.yaml"


def _projection(path: Path) -> dict[str, Any]:
    raw_bytes = path.read_bytes()
    return build_projection(
        load_metamodel_yaml(path), hashlib.sha256(raw_bytes).hexdigest()
    )


def test_small_fixture_matches_complete_golden_json() -> None:
    fixture = SIMPLE_MODEL_PATH
    expected = (MODEL_DIR / "simple_expected.json").read_text(encoding="utf-8")

    assert render_projection(_projection(fixture)) == expected


def test_projection_is_deterministic() -> None:
    fixture = MODEL_DIR / "nested_model.yaml"
    first = render_projection(_projection(fixture)).encode()
    second = render_projection(_projection(fixture)).encode()

    assert first == second


def test_digest_changes_with_input_bytes_and_repeats_for_identical_input(
    tmp_path: Path,
) -> None:
    source = SIMPLE_MODEL_PATH
    original = source.read_bytes()
    first_path = tmp_path / "first.yaml"
    second_path = tmp_path / "second.yaml"
    first_path.write_bytes(original)
    second_path.write_bytes(original)

    first = _projection(first_path)["metamodel_digest"]
    second = _projection(second_path)["metamodel_digest"]
    changed_path = tmp_path / "changed.yaml"
    changed_path.write_bytes(original + b"\n")
    changed = _projection(changed_path)["metamodel_digest"]

    assert first == second
    assert changed != first


def test_nested_graph_rules_round_trip_without_interpretation() -> None:
    projection = _projection(MODEL_DIR / "nested_model.yaml")
    rule = projection["graph_rules"][0]

    assert rule["condition_raw"] == {
        "and": [
            "status == valid",
            {"or": ["safety == QM", "safety == ASIL_B"]},
        ]
    }
    assert rule["check_raw"] == {
        "required_link": {
            "or": ["status == valid", "status == draft"],
        }
    }


def test_type_options_override_inherited_base_options() -> None:
    projection = _projection(MODEL_DIR / "precedence_model.yaml")
    options = {
        option["name"]: option for option in projection["need_types"][0]["options"]
    }

    assert options["shared"] == {
        "name": "shared",
        "pattern": "^type$",
        "required": False,
        "inherited": False,
    }
