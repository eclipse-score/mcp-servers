# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
"""Checked-in Fabro workflows stay in sync with the generator and validate natively."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from graphify_fabro_conversion import convert_sdlc_to_fabro_dot  # noqa: E402

WORKFLOWS = PACKAGE_ROOT / "workflows"
EXAMPLE_REQUIREMENT = "Example requirement: replace with the requirement text"

requires_fabro = pytest.mark.skipif(
    shutil.which("fabro") is None, reason="fabro CLI not installed"
)


def test_sdlc_lifecycle_workflow_matches_generator() -> None:
    checked_in = (WORKFLOWS / "sdlc-lifecycle.fabro").read_text(encoding="utf-8")
    generated = convert_sdlc_to_fabro_dot("ISSUE-1", EXAMPLE_REQUIREMENT)
    assert checked_in == generated


@requires_fabro
@pytest.mark.parametrize("name", ["sdlc-lifecycle.fabro", "local-smoke.fabro"])
def test_workflow_passes_fabro_validate(tmp_path: Path, name: str) -> None:
    target = tmp_path / name
    shutil.copyfile(WORKFLOWS / name, target)
    result = subprocess.run(
        ["fabro", "validate", str(target)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "warning:" not in output
