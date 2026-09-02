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

from datetime import UTC, datetime
from pathlib import Path

import pytest
from context_sessions import (
    ReasoningRecord,
    SessionLog,
    SessionRecord,
    TaskRecord,
    agent_salt,
    pseudonymize_agent,
)


def test_session_log_round_trip_and_filtering(tmp_path: Path) -> None:
    log = SessionLog(tmp_path)
    first = SessionRecord(id="session__one", agent="agent-a", goal="First")
    task = TaskRecord(
        id="task__one",
        session_id=first.id,
        text="Task",
    )
    reasoning = ReasoningRecord(
        id="reasoning__one",
        session_id=first.id,
        task_id=task.id,
        text="Finding",
        grounded_nodes=["node__one"],
    )
    other = SessionRecord(id="session__two", agent="agent-b", goal="Other")
    for record in (first, task, reasoning, other):
        log.append(record)

    assert log.read_all() == (first, task, reasoning, other)
    assert log.records_for(first.id) == (first, task, reasoning)
    assert log.other_sessions(first.id) == (other,)


def test_session_log_reports_malformed_line_number(tmp_path: Path) -> None:
    log = SessionLog(tmp_path)
    log.path.parent.mkdir(parents=True)
    log.path.write_text('{"record_type":"session"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        log.read_all()


def test_session_log_rejects_unknown_record_type(tmp_path: Path) -> None:
    log = SessionLog(tmp_path)
    log.path.parent.mkdir(parents=True)
    log.path.write_text(
        '{"record_type":"unknown","id":"record__one"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown session record kind"):
        log.read_all()


def test_agent_pseudonym_is_deterministic_and_salt_is_private(tmp_path: Path) -> None:
    salt = agent_salt(tmp_path / ".score-local")
    assert pseudonymize_agent("alice", salt) == pseudonymize_agent("alice", salt)
    assert pseudonymize_agent("alice", salt) != pseudonymize_agent("alice", "other")
    assert pseudonymize_agent("alice", salt) != "alice"
    assert (tmp_path / ".score-local" / "agent-salt").stat().st_mode & 0o777 == 0o600


def test_prune_drops_old_records_keeps_recent_and_unparsable(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 2, 1, tzinfo=UTC)
    log = SessionLog(tmp_path)
    records = (
        SessionRecord(id="session__old", timestamp="2025-01-01T00:00:00+00:00"),
        SessionRecord(id="session__recent", timestamp="2026-01-31T00:00:00+00:00"),
        SessionRecord(id="session__bad", timestamp="unknown"),
    )
    for record in records:
        log.append(record)

    assert log.prune(30, now=now) == 1
    assert [record.id for record in log.read_all()] == [
        "session__recent",
        "session__bad",
    ]
    assert log.path.read_text(encoding="utf-8").splitlines()[0].startswith('{"agent"')


def test_prune_missing_log_returns_zero_without_creating_file(tmp_path: Path) -> None:
    log = SessionLog(tmp_path)

    assert log.prune(30, now=datetime(2026, 2, 1, tzinfo=UTC)) == 0
    assert not log.path.exists()
