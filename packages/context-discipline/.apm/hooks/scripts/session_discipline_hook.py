#!/usr/bin/env python3
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

"""Fail-open session lifecycle hooks for context-discipline."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

MARKER_PATH = Path(".score-local/hook_session.json")
SESSION_LOG_PATH = Path(".score-local/sessions.jsonl")
UTC = timezone(timedelta(0))


def _timestamp() -> str:
    return datetime.now(tz=UTC).isoformat()


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _output(payload: dict[str, Any]) -> None:
    print(json.dumps(payload))


def _session_start(repo: Path) -> None:
    started_at = _timestamp()
    marker = repo / MARKER_PATH
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"started_at": started_at}), encoding="utf-8")
    _output(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    f"Context discipline: repository {repo.name} | call "
                    "initialize_session as the first tool call of this session "
                    "and print its announcement verbatim before any other output."
                ),
            }
        }
    )


def _session_recorded_after(repo: Path, started_at: datetime) -> bool:
    log = repo / SESSION_LOG_PATH
    if not log.is_file():
        return False
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
            if not isinstance(record, dict) or record.get("record_type") != "session":
                continue
            timestamp = _parse_timestamp(record.get("timestamp"))
            if timestamp is not None and timestamp > started_at:
                return True
        except (OSError, TypeError, ValueError):
            continue
    return False


def _pre_tool_use(repo: Path, data: dict[str, Any]) -> None:
    tool_name = str(data.get("tool_name", ""))
    if "initialize_session" in tool_name:
        return
    marker = repo / MARKER_PATH
    try:
        marker_data = json.loads(marker.read_text(encoding="utf-8"))
        started_at = _parse_timestamp(marker_data.get("started_at"))
    except (OSError, TypeError, ValueError):
        return
    if started_at is None or _session_recorded_after(repo, started_at):
        return
    _output(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": (
                    "context-discipline: no session recorded for this agent "
                    "session. Call initialize_session first, then print its "
                    "announcement verbatim."
                ),
            }
        }
    )


def main() -> int:
    try:
        data = json.loads(sys.stdin.read())
        if not isinstance(data, dict):
            return 0
        repo = Path.cwd()
        mode = sys.argv[1]
        if mode == "session-start":
            _session_start(repo)
        elif mode == "pre-tool-use":
            _pre_tool_use(repo, data)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
