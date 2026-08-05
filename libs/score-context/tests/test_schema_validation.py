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

"""Test that existing artifacts conform to JSON schemas."""

from pathlib import Path

import pytest
from score_context.schema.validator import (
    validate_graph_fragment,
    validate_task_spec,
)


class TestGraphFragmentValidation:
    """Ensure graph fragments conform to schema."""

    def test_seed_graph_fragment_validates(self):
        """Current seed graph must be valid."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "harness/spec/graph_fragment.json"
        )
        errors = validate_graph_fragment(path)
        assert not errors, f"Graph fragment validation failed: {errors}"

    def test_graph_fragment_has_version(self):
        """Graph fragment must have fragment_version."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "harness/spec/graph_fragment.json"
        )
        import json

        data = json.loads(path.read_text())
        assert "fragment_version" in data, "Missing fragment_version"
        assert data["fragment_version"] == "v1"

    def test_graph_fragment_has_adapter_metadata(self):
        """Graph fragment must have adapter metadata."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "harness/spec/graph_fragment.json"
        )
        import json

        data = json.loads(path.read_text())
        assert "adapter" in data, "Missing adapter metadata"
        assert "name" in data["adapter"]
        assert "version" in data["adapter"]
        assert "sha256" in data["adapter"]


class TestTaskSpecValidation:
    """Ensure task specs conform to schema."""

    @pytest.mark.parametrize(
        "task_file",
        [
            "task_001_contract_change.json",
            "task_002_module_blocked.json",
        ],
    )
    def test_task_spec_validates(self, task_file):
        """All task specs must be valid."""
        path = Path(__file__).parent.parent.parent.parent / f"harness/spec/{task_file}"
        errors = validate_task_spec(path)
        assert not errors, f"{task_file} validation failed: {errors}"

    @pytest.mark.parametrize(
        "task_file",
        [
            "task_001_contract_change.json",
            "task_002_module_blocked.json",
        ],
    )
    def test_task_spec_has_version(self, task_file):
        """Task specs must have task_version."""
        path = Path(__file__).parent.parent.parent.parent / f"harness/spec/{task_file}"
        import json

        data = json.loads(path.read_text())
        assert "task_version" in data, f"{task_file} missing task_version"
        assert data["task_version"] == "v1"

    @pytest.mark.parametrize(
        "task_file",
        [
            "task_001_contract_change.json",
            "task_002_module_blocked.json",
        ],
    )
    def test_task_spec_has_required_fields(self, task_file):
        """Task specs must have required fields."""
        path = Path(__file__).parent.parent.parent.parent / f"harness/spec/{task_file}"
        import json

        data = json.loads(path.read_text())
        assert "id" in data, f"{task_file} missing id"
        assert "seed_node_ids" in data, f"{task_file} missing seed_node_ids"
        assert "expected_node_ids" in data, f"{task_file} missing expected_node_ids"
        assert isinstance(data["seed_node_ids"], list)
        assert isinstance(data["expected_node_ids"], list)
