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
from pathlib import Path

from jsonschema import Draft202012Validator


def test_contract_instances_validate_against_vendored_schemas() -> None:
    root = Path(__file__).parents[3]
    for instance_name, schema_name in (
        ("repo-manifest.json", "repo-manifest.schema.json"),
        ("agent-card.json", "agent-card.schema.json"),
    ):
        instance = json.loads((root / ".github/score" / instance_name).read_text())
        schema = json.loads((root / ".github/references" / schema_name).read_text())
        Draft202012Validator(schema).validate(instance)  # pyright: ignore[reportUnknownMemberType]


def test_adapter_request_validates_against_vendored_schema() -> None:
    root = Path(__file__).parents[3]
    request = json.loads((root / "harness/spec/request_run.json").read_text())
    schema = json.loads(
        (root / "harness/contract/adapter_contract_v0_1.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(request)  # pyright: ignore[reportUnknownMemberType]
