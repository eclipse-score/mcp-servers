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

from context_attention import (
    SCORE_THRESHOLD,
    get_prior_context,
    redundancy,
    score_candidate,
)
from context_sessions import (
    OutcomeRecord,
    ReasoningRecord,
    Record,
    SessionLog,
)


def make_log(path: Path, records: list[Record]) -> SessionLog:
    log = SessionLog(path)
    for record in records:
        log.append(record)
    return log


def test_prior_context_excludes_own_session_and_fail_scores_lower(
    tmp_path: Path,
) -> None:
    own = ReasoningRecord(
        id="reasoning__own",
        session_id="session__current",
        task_id="task__current",
        text="contract change",
        grounded_nodes=["node__one"],
    )
    prior = ReasoningRecord(
        id="reasoning__prior",
        session_id="session__prior",
        task_id="task__prior",
        text="contract change",
        grounded_nodes=["node__one"],
    )
    log = make_log(
        tmp_path,
        [
            own,
            prior,
            OutcomeRecord(
                id="outcome__fail",
                session_id="session__prior",
                task_id="task__prior",
                verdict="fail",
                coverage=0.2,
            ),
        ],
    )
    fail_score = score_candidate(
        frozenset({"contract", "change"}),
        {"node__one"},
        prior,
        "fail",
    )
    pass_score = score_candidate(
        frozenset({"contract", "change"}),
        {"node__one"},
        prior,
        "pass",
    )
    assert pass_score > fail_score
    selected = get_prior_context(
        log,
        "session__current",
        "contract change",
        {"node__one"},
    )
    assert [item.reasoning_id for item in selected] == ["reasoning__prior"]


def test_threshold_and_top_k_are_deterministic(tmp_path: Path) -> None:
    records: list[Record] = []
    for index in range(6):
        records.append(
            ReasoningRecord(
                id=f"reasoning__{index}",
                session_id=f"session__{index}",
                task_id=f"task__{index}",
                text="matching task",
                grounded_nodes=["node__one"],
            )
        )
        records.append(
            OutcomeRecord(
                id=f"outcome__{index}",
                session_id=f"session__{index}",
                task_id=f"task__{index}",
                verdict="pass",
                coverage=1.0,
            )
        )
    log = make_log(tmp_path, list(reversed(records)))
    selected = get_prior_context(
        log,
        "session__current",
        "matching task",
        {"node__one"},
        top_k=2,
    )
    assert len(selected) == 2
    assert [item.reasoning_id for item in selected] == [
        "reasoning__0",
        "reasoning__1",
    ]
    below = ReasoningRecord(
        id="reasoning__below",
        session_id="session__below",
        task_id="task__below",
        text="unrelated",
    )
    assert score_candidate(frozenset({"task"}), set(), below, None) < SCORE_THRESHOLD


def test_redundancy_handles_empty_disjoint_and_identical_sets() -> None:
    assert redundancy(set(), set()) == 0.0
    assert redundancy({"other"}, {"node"}) == 0.0
    assert redundancy({"node"}, {"node"}) == 1.0
