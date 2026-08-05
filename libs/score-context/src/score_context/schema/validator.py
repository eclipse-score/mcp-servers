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

"""Validate JSON artifacts against versioned schemas."""

import json
from pathlib import Path
from typing import cast

try:
    import jsonschema
except ImportError as err:
    raise ImportError("jsonschema required: pip install jsonschema") from err


# Schema directory relative to this file
# From: libs/score-context/src/score_context/schema/validator.py
# To: harness/schema/ (need 6 parent calls to reach workspace root)
SCHEMAS_DIR = Path(__file__).parents[5] / "harness" / "schema"


def load_schema(schema_name: str) -> dict[str, object]:
    """Load a schema file by name (e.g., 'graph_fragment_v1')."""
    schema_path = SCHEMAS_DIR / f"{schema_name}.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    with open(schema_path) as f:
        return cast(dict[str, object], json.load(f))


def validate_graph_fragment(path: Path) -> list[str]:
    """
    Validate graph fragment against schema.

    Args:
        path: Path to graph fragment JSON file

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []
    try:
        with open(path) as f:
            data = json.load(f)

        schema = load_schema("graph_fragment_v1")
        jsonschema.validate(data, schema)
    except json.JSONDecodeError as e:
        errors.append(f"JSON syntax error in {path}: {e}")
    except jsonschema.ValidationError as e:
        errors.append(
            f"Validation error in {path}: {e.message} "
            f"at path {'.'.join(str(p) for p in e.absolute_path)}"
        )
    except FileNotFoundError as e:
        errors.append(f"File not found: {e}")

    return errors


def validate_task_spec(path: Path) -> list[str]:
    """
    Validate task spec against schema.

    Args:
        path: Path to task spec JSON file

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []
    try:
        with open(path) as f:
            data = json.load(f)

        schema = load_schema("task_spec_v1")
        jsonschema.validate(data, schema)
    except json.JSONDecodeError as e:
        errors.append(f"JSON syntax error in {path}: {e}")
    except jsonschema.ValidationError as e:
        errors.append(
            f"Validation error in {path}: {e.message} "
            f"at path {'.'.join(str(p) for p in e.absolute_path)}"
        )
    except FileNotFoundError as e:
        errors.append(f"File not found: {e}")

    return errors


def validate_experience(path: Path) -> list[str]:
    """
    Validate experience artifact against schema.

    Args:
        path: Path to experience JSON file

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []
    try:
        with open(path) as f:
            data = json.load(f)

        schema = load_schema("experience_v1")
        jsonschema.validate(data, schema)
    except json.JSONDecodeError as e:
        errors.append(f"JSON syntax error in {path}: {e}")
    except jsonschema.ValidationError as e:
        errors.append(
            f"Validation error in {path}: {e.message} "
            f"at path {'.'.join(str(p) for p in e.absolute_path)}"
        )
    except FileNotFoundError as e:
        errors.append(f"File not found: {e}")

    return errors
