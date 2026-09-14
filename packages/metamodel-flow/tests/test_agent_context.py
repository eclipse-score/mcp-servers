# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Tests for loading and validating the metamodel projection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent_context import AgentContextValidationError, load_agent_context

MODEL_PATH = Path(__file__).parents[1] / "model" / "agent_context.json"


def _payload() -> dict[str, object]:
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def test_committed_projection_passes_validation() -> None:
    context = load_agent_context(MODEL_PATH)

    assert context.schema_version == 1
    assert len(context.need_types) == 50
    assert len(context.link_types) == 28
    assert len(context.graph_rules) == 5


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 2),
        ("metamodel_digest", "sha256:not-a-digest"),
        ("base_options", []),
        ("prohibited_words", {}),
        ("link_types", {}),
        ("need_types", {}),
        ("graph_rules", {}),
    ],
)
def test_invalid_top_level_fields_are_rejected(
    tmp_path: Path, field: str, value: object
) -> None:
    payload = _payload()
    payload[field] = value
    path = tmp_path / "agent_context.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(AgentContextValidationError, match=field):
        load_agent_context(path)


@pytest.mark.parametrize(
    "field",
    ["base_options", "prohibited_words", "link_types", "need_types", "graph_rules"],
)
def test_missing_top_level_sections_are_rejected(tmp_path: Path, field: str) -> None:
    payload = _payload()
    del payload[field]
    path = tmp_path / "agent_context.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(AgentContextValidationError, match=field):
        load_agent_context(path)
