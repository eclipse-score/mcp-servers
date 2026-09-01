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

"""Deterministic intersession retrieval using lexical and graph grounding."""

from __future__ import annotations

import re
from dataclasses import dataclass

from context_sessions import OutcomeRecord, ReasoningRecord, SessionLog

W_SEMANTIC = 0.6
W_STRUCTURAL = 0.4
OUTCOME_BONUS = 0.2
# Deliberately far below D3MAS's cosine threshold of 0.65: Jaccard over short
# text is much sparser than cosine over embeddings.
SCORE_THRESHOLD = 0.15
TOP_K = 5
_MIN_TOKEN_LEN = 3


def tokenize(text: str) -> frozenset[str]:
    return frozenset(
        token
        for token in re.split(r"[^A-Za-z0-9]+", text.lower())
        if len(token) >= _MIN_TOKEN_LEN
    )


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def score_candidate(
    task_tokens: frozenset[str],
    current_nodes: set[str],
    reasoning: ReasoningRecord,
    verdict: str | None,
) -> float:
    semantic = jaccard(task_tokens, tokenize(reasoning.text))
    structural = (
        len(set(reasoning.grounded_nodes) & current_nodes) / len(current_nodes)
        if current_nodes
        else 0.0
    )
    bonus = (
        OUTCOME_BONUS
        if verdict == "pass"
        else -OUTCOME_BONUS
        if verdict == "fail"
        else 0.0
    )
    return W_SEMANTIC * semantic + W_STRUCTURAL * structural + bonus


@dataclass(frozen=True)
class PriorContext:
    reasoning_id: str
    session_id: str
    text: str
    kind: str
    grounded_nodes: tuple[str, ...]
    score: float
    verdict: str | None


def get_prior_context(
    log: SessionLog,
    session_id: str,
    task_text: str,
    current_nodes: set[str],
    top_k: int = TOP_K,
) -> tuple[PriorContext, ...]:
    records = log.read_all()
    outcomes = {
        record.task_id: record.verdict
        for record in records
        if isinstance(record, OutcomeRecord)
    }
    candidates: list[PriorContext] = []
    task_tokens = tokenize(task_text)
    for reasoning in records:
        if not isinstance(reasoning, ReasoningRecord):
            continue
        if reasoning.session_id == session_id:
            continue
        verdict = outcomes.get(reasoning.task_id)
        score = score_candidate(task_tokens, current_nodes, reasoning, verdict)
        if score >= SCORE_THRESHOLD:
            candidates.append(
                PriorContext(
                    reasoning_id=reasoning.id,
                    session_id=reasoning.session_id,
                    text=reasoning.text,
                    kind=reasoning.kind,
                    grounded_nodes=tuple(reasoning.grounded_nodes),
                    score=score,
                    verdict=verdict,
                )
            )
    candidates.sort(key=lambda item: (-item.score, item.reasoning_id))
    return tuple(candidates[:top_k])


def redundancy(prior_nodes: set[str], current_nodes: set[str]) -> float:
    if not current_nodes:
        return 0.0
    return len(prior_nodes & current_nodes) / len(current_nodes)
