# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Tests for deterministic metamodel instruction rendering."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from agent_context import load_agent_context
from render_markdown import render_markdown

PACKAGE_ROOT = Path(__file__).parents[1]
MODEL_PATH = PACKAGE_ROOT / "model" / "agent_context.json"
INSTRUCTION_PATH = (
    PACKAGE_ROOT / ".apm" / "instructions" / "score-artifact-model.instructions.md"
)
RENDERER = PACKAGE_ROOT / "src" / "render_markdown.py"


def test_committed_markdown_matches_fresh_render() -> None:
    context = load_agent_context(MODEL_PATH)

    assert INSTRUCTION_PATH.read_text(encoding="utf-8") == render_markdown(context)


def test_rendering_is_deterministic() -> None:
    context = load_agent_context(MODEL_PATH)

    assert render_markdown(context) == render_markdown(context)


def test_rendered_frontmatter_has_instruction_metadata() -> None:
    rendered = render_markdown(load_agent_context(MODEL_PATH))
    lines = rendered.splitlines()
    start = lines.index("---")
    end = lines.index("---", start + 1)
    frontmatter = dict(line.split(": ", 1) for line in lines[start + 1 : end])

    assert frontmatter == {
        "name": "score-artifact-model",
        "description": (
            "Normative S-CORE artifact model — need types, options, links and "
            "graph rules"
        ),
        "applyTo": '"**/*.rst"',
    }


def test_real_projection_is_structurally_rendered() -> None:
    context = load_agent_context(MODEL_PATH)
    rendered = render_markdown(context)

    for need_type in context.need_types:
        assert f"`{need_type.name}`" in rendered
    for rule in context.graph_rules:
        assert f"`{rule.name}`" in rendered
        condition = (
            rule.condition_raw
            if isinstance(rule.condition_raw, str)
            else json.dumps(
                rule.condition_raw, ensure_ascii=False, indent=2, sort_keys=True
            )
        )
        assert condition in rendered
    assert "`links` — undeclared built-in link type." in rendered


def test_check_mode_detects_drift_without_mutating_package(tmp_path: Path) -> None:
    package_root = tmp_path / "metamodel-flow"
    (package_root / "model").mkdir(parents=True)
    instruction_dir = package_root / ".apm" / "instructions"
    instruction_dir.mkdir(parents=True)
    shutil.copy2(MODEL_PATH, package_root / "model" / "agent_context.json")
    instruction_dir.joinpath(INSTRUCTION_PATH.name).write_text(
        render_markdown(load_agent_context(MODEL_PATH)), encoding="utf-8"
    )

    clean = subprocess.run(
        [
            sys.executable,
            str(RENDERER),
            "--check",
            "--package-root",
            str(package_root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert clean.returncode == 0

    instruction_path = instruction_dir / INSTRUCTION_PATH.name
    instruction_path.write_text("tampered\n", encoding="utf-8")
    drift = subprocess.run(
        [
            sys.executable,
            str(RENDERER),
            "--check",
            "--package-root",
            str(package_root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert drift.returncode != 0
    assert "--write" in drift.stdout
