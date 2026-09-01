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

"""Append-only session records mapped to the D3MAS layers.

| kind | D3MAS layer | fields |
| --- | --- | --- |
| session | agent | id, agent, goal, timestamp |
| task | Decompose | id, session_id, text, parent_id, timestamp |
| reasoning | Deduce | id, session_id, task_id, text, kind, grounded_nodes, timestamp |
| retrieval | Distribute | id, session_id, task_id, query, returned_nodes, timestamp |
| outcome | — | id, session_id, task_id, verdict, coverage, timestamp |
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4


def _timestamp() -> str:
    return datetime.now(tz=UTC).isoformat()


def _record_id(kind: str) -> str:
    return f"{kind}__{uuid4().hex[:8]}"


def _empty_nodes() -> list[str]:
    return []


@dataclass(frozen=True)
class SessionRecord:
    id: str = field(default_factory=lambda: _record_id("session"))
    agent: str = "unknown"
    goal: str = ""
    timestamp: str = field(default_factory=_timestamp)
    record_type: str = field(default="session", init=False)


@dataclass(frozen=True)
class TaskRecord:
    id: str = field(default_factory=lambda: _record_id("task"))
    session_id: str = ""
    text: str = ""
    parent_id: str | None = None
    timestamp: str = field(default_factory=_timestamp)
    record_type: str = field(default="task", init=False)


@dataclass(frozen=True)
class ReasoningRecord:
    id: str = field(default_factory=lambda: _record_id("reasoning"))
    session_id: str = ""
    task_id: str = ""
    text: str = ""
    kind: str = "finding"
    grounded_nodes: list[str] = field(default_factory=_empty_nodes)
    timestamp: str = field(default_factory=_timestamp)
    record_type: str = field(default="reasoning", init=False)


@dataclass(frozen=True)
class RetrievalRecord:
    id: str = field(default_factory=lambda: _record_id("retrieval"))
    session_id: str = ""
    task_id: str = ""
    query: str = ""
    returned_nodes: list[str] = field(default_factory=_empty_nodes)
    timestamp: str = field(default_factory=_timestamp)
    record_type: str = field(default="retrieval", init=False)


@dataclass(frozen=True)
class OutcomeRecord:
    id: str = field(default_factory=lambda: _record_id("outcome"))
    session_id: str = ""
    task_id: str = ""
    verdict: str = "fail"
    coverage: float = 0.0
    timestamp: str = field(default_factory=_timestamp)
    record_type: str = field(default="outcome", init=False)


type Record = (
    SessionRecord | TaskRecord | ReasoningRecord | RetrievalRecord | OutcomeRecord
)


def _record_dict(record: Record) -> dict[str, Any]:
    data = asdict(record)
    data["record_type"] = record.record_type
    return data


def _record_from_dict(data: dict[str, Any]) -> Record:
    record_type = cast(str | None, data.get("record_type"))
    values = dict(data)
    values.pop("record_type", None)
    if record_type == "reasoning":
        return ReasoningRecord(
            id=values["id"],
            session_id=values["session_id"],
            task_id=values["task_id"],
            text=values["text"],
            kind=cast(str, values["kind"]),
            grounded_nodes=list(cast(list[str], values.get("grounded_nodes", []))),
            timestamp=values["timestamp"],
        )
    constructors: dict[str, type[Record]] = {
        "session": SessionRecord,
        "task": TaskRecord,
        "retrieval": RetrievalRecord,
        "outcome": OutcomeRecord,
    }
    if record_type is None:
        raise ValueError("missing session record type")
    constructor = constructors.get(record_type)
    if constructor is None:
        raise ValueError(f"unknown session record kind: {record_type!r}")
    values.pop("kind", None)
    return constructor(**values)


class SessionLog:
    """Append-only JSONL collaboration record log."""

    def __init__(self, repo_path: str | Path, local_store: str = ".score-local"):
        repo = Path(repo_path).expanduser().resolve()
        store = Path(local_store).expanduser()
        root = store if store.is_absolute() else repo / store
        self.path = root / "sessions.jsonl"

    def append(self, record: Record) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(_record_dict(record), sort_keys=True) + "\n")

    def read_all(self) -> tuple[Record, ...]:
        if not self.path.exists():
            return ()
        records: list[Record] = []
        for line_number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                raw_data: Any = json.loads(line)
                if not isinstance(raw_data, dict):
                    raise TypeError("record must be an object")
                data = cast(dict[str, Any], raw_data)
                records.append(_record_from_dict(data))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"malformed session record on line {line_number}: {exc}"
                ) from exc
        return tuple(records)

    def records_for(self, session_id: str) -> tuple[Record, ...]:
        """Return this session's session record and records carrying its ID."""
        return tuple(
            record
            for record in self.read_all()
            if (isinstance(record, SessionRecord) and record.id == session_id)
            or (
                not isinstance(record, SessionRecord)
                and record.session_id == session_id
            )
        )

    def other_sessions(self, session_id: str) -> tuple[Record, ...]:
        """Return records excluding its session record and records carrying its ID."""
        return tuple(
            record
            for record in self.read_all()
            if (isinstance(record, SessionRecord) and record.id != session_id)
            or (
                not isinstance(record, SessionRecord)
                and record.session_id != session_id
            )
        )
