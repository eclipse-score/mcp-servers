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

from pathlib import Path

import pytest
from context_sessions import (
    ReasoningRecord,
    SessionLog,
    SessionRecord,
    TaskRecord,
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
