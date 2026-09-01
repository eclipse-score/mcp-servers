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

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from score_context.cli import main


def test_demo_is_deterministic_and_flips_gate() -> None:
    root = Path(__file__).parents[3]
    output_one = StringIO()
    output_two = StringIO()
    with redirect_stdout(output_one):
        assert main(["demo"]) == 0
    with redirect_stdout(output_two):
        assert main(["demo"]) == 0
    assert output_one.getvalue() == output_two.getvalue()
    assert "lane_a_gate: fail" in output_one.getvalue()
    assert "lane_a_gate: pass" in output_one.getvalue()
    assert "moved into selection: dec_rec__demo__1" in output_one.getvalue()
    assert root.joinpath("harness/demo/weights.json").exists()
