# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".apm"
    / "hooks"
    / "scripts"
    / "session_discipline_hook.py"
)


def _state_home(tmp_path: Path) -> Path:
    return tmp_path / "xdg-state"


def _session_log(tmp_path: Path) -> Path:
    digest = hashlib.sha256(str(tmp_path.resolve()).encode("utf-8")).hexdigest()[:16]
    return (
        _state_home(tmp_path)
        / "score-agent"
        / f"{tmp_path.name}-{digest}"
        / "sessions.jsonl"
    )


def run_hook(
    tmp_path: Path, mode: str, payload: object
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "XDG_STATE_HOME": str(_state_home(tmp_path))}
    return subprocess.run(
        [sys.executable, str(SCRIPT), mode],
        cwd=tmp_path,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def test_session_start_emits_context_and_writes_marker(tmp_path: Path) -> None:
    result = run_hook(tmp_path, "session-start", {"source": "startup"})

    assert result.returncode == 0
    output = json.loads(result.stdout)
    hook_output = output["hookSpecificOutput"]
    assert hook_output["hookEventName"] == "SessionStart"
    assert hook_output["additionalContext"]
    marker = json.loads(
        (tmp_path / ".score-local" / "hook_session.json").read_text(encoding="utf-8")
    )
    assert marker["started_at"]


def test_pre_tool_use_is_silent_without_marker(tmp_path: Path) -> None:
    result = run_hook(tmp_path, "pre-tool-use", {"tool_name": "read_file"})

    assert result.returncode == 0
    assert result.stdout == ""


def test_pre_tool_use_asks_without_session_record(tmp_path: Path) -> None:
    marker_path = tmp_path / ".score-local" / "hook_session.json"
    marker_path.parent.mkdir()
    marker_path.write_text(
        json.dumps({"started_at": "2026-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )

    result = run_hook(tmp_path, "pre-tool-use", {"tool_name": "read_file"})

    assert result.returncode == 0
    output = json.loads(result.stdout)
    hook_output = output["hookSpecificOutput"]
    assert hook_output["permissionDecision"] == "ask"


def test_pre_tool_use_is_silent_after_session_record(tmp_path: Path) -> None:
    marker_path = tmp_path / ".score-local" / "hook_session.json"
    marker_path.parent.mkdir()
    marker_path.write_text(
        json.dumps({"started_at": "2026-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    log_path = _session_log(tmp_path)
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        json.dumps(
            {
                "record_type": "session",
                "timestamp": "2026-01-01T00:00:01+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_hook(tmp_path, "pre-tool-use", {"tool_name": "read_file"})

    assert result.returncode == 0
    assert result.stdout == ""


def test_pre_tool_use_ignores_repo_local_session_log(tmp_path: Path) -> None:
    marker_path = tmp_path / ".score-local" / "hook_session.json"
    marker_path.parent.mkdir()
    marker_path.write_text(
        json.dumps({"started_at": "2026-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    (tmp_path / ".score-local" / "sessions.jsonl").write_text(
        json.dumps(
            {
                "record_type": "session",
                "timestamp": "2026-01-01T00:00:01+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_hook(tmp_path, "pre-tool-use", {"tool_name": "read_file"})

    output = json.loads(result.stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_pre_tool_use_allows_initialize_session_without_record(tmp_path: Path) -> None:
    marker_path = tmp_path / ".score-local" / "hook_session.json"
    marker_path.parent.mkdir()
    marker_path.write_text(
        json.dumps({"started_at": "2026-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )

    result = run_hook(
        tmp_path,
        "pre-tool-use",
        {"tool_name": "mcp__context_discipline__initialize_session"},
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_malformed_input_fails_open(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "session-start"],
        cwd=tmp_path,
        input="not-json",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""
