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

"""Ordered graph sources used by the merged context graph."""

from __future__ import annotations

import json
import os
import posixpath
import re
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from context_merge import MergedEdge, MergedNode, link_reasoning
from context_overlay import OverlayStore, Provenance
from context_policy import Policy
from context_sessions import (
    AttentionRecord,
    ReasoningRecord,
    Record,
    RetrievalRecord,
    SessionLog,
    SessionRecord,
    TaskClassRecord,
    TaskRecord,
)

PROCESS_ID_PATTERN = r"^(wf|rl|wp|gd_(req|temp|guidl|chklst)|std_(req|wp))__"
PROCESS_ID_RE = re.compile(PROCESS_ID_PATTERN)


@dataclass(frozen=True)
class SourceGraph:
    layer: str
    nodes: tuple[MergedNode, ...]
    edges: tuple[MergedEdge, ...]
    read_only: bool
    loaded: bool = False


class GraphSource(Protocol):
    layer: str
    read_only: bool

    def load(self, repo: Path, policy: Policy) -> SourceGraph: ...


def _session_edges(records: tuple[Record, ...]) -> tuple[MergedEdge, ...]:
    edges: list[MergedEdge] = []
    sessions = [record for record in records if isinstance(record, SessionRecord)]
    tasks = [record for record in records if isinstance(record, TaskRecord)]
    reasonings = [record for record in records if isinstance(record, ReasoningRecord)]
    retrievals = [record for record in records if isinstance(record, RetrievalRecord)]
    for session in sessions:
        for task in tasks:
            if task.session_id == session.id:
                edges.append(
                    MergedEdge(session.id, task.id, "contains", "collaboration")
                )
    for task in tasks:
        if task.parent_id:
            edges.append(
                MergedEdge(task.parent_id, task.id, "contains", "collaboration")
            )
    for reasoning in reasonings:
        if reasoning.task_id:
            edges.append(
                MergedEdge(
                    reasoning.id, reasoning.task_id, "belongs_to", "collaboration"
                )
            )
        edges.extend(
            MergedEdge(reasoning.id, node_id, "supported_by", "collaboration")
            for node_id in reasoning.grounded_nodes
        )
    edges.extend(
        MergedEdge(newer, older, "derived_from", "collaboration")
        for newer, older in link_reasoning(records)
    )
    for retrieval in retrievals:
        edges.extend(
            MergedEdge(retrieval.id, node_id, "covers", "collaboration")
            for node_id in retrieval.returned_nodes
        )
    return tuple(edges)


class CodeGraphSource:
    layer = "code"
    read_only = True

    def load(self, repo: Path, policy: Policy) -> SourceGraph:
        path = repo / "graphify-out" / "graph.json"
        if not path.exists():
            return SourceGraph(self.layer, (), (), self.read_only, False)
        data = json.loads(path.read_text(encoding="utf-8"))
        nodes: list[MergedNode] = []
        for raw in data.get("nodes", []):
            source_file = raw.get("source_file")
            normalized_source_file = ""
            source_file_keys: tuple[str, ...] = ()
            if source_file is not None:
                raw_source_file = str(source_file)
                normalized_source_file = posixpath.normpath(
                    raw_source_file.replace("\\", "/")
                )
                keys = {raw_source_file, normalized_source_file}
                source_path = Path(normalized_source_file)
                if source_path.is_absolute():
                    with suppress(ValueError):
                        normalized_source_file = (
                            source_path.resolve().relative_to(repo).as_posix()
                        )
                        keys.add(normalized_source_file)
                source_file_keys = tuple(sorted(keys))
            nodes.append(
                MergedNode(
                    id=str(raw["id"]),
                    label=str(raw.get("label", raw["id"])),
                    type=str(raw.get("type") or raw.get("file_type", "")),
                    layer=self.layer,
                    source_file=normalized_source_file,
                    source_file_keys=source_file_keys,
                )
            )
        raw_edges = data.get("links", data.get("edges", []))
        edges = tuple(
            MergedEdge(
                source=str(raw["source"]),
                target=str(raw["target"]),
                relation=str(raw.get("relation", "")),
                layer=self.layer,
            )
            for raw in raw_edges
        )
        return SourceGraph(self.layer, tuple(nodes), edges, self.read_only, True)


class OverlaySource:
    layer = "domain"
    read_only = False

    def load(self, repo: Path, policy: Policy) -> SourceGraph:
        overlay = OverlayStore(repo)
        overlay.load()
        nodes = tuple(
            MergedNode(
                raw.id,
                raw.title,
                raw.type,
                self.layer,
                provenance=raw.provenance,
            )
            for raw in overlay.nodes
        )
        edges = tuple(
            MergedEdge(
                raw.source,
                raw.target,
                raw.relation,
                self.layer,
                raw.provenance,
            )
            for raw in overlay.edges
        )
        return SourceGraph(
            self.layer,
            nodes,
            edges,
            self.read_only,
            (repo / "score-context").exists(),
        )


class SessionSource:
    layer = "collaboration"
    read_only = False

    def load(self, repo: Path, policy: Policy) -> SourceGraph:
        log = SessionLog(repo)
        records = log.read_all()
        nodes: list[MergedNode] = []
        for record in records:
            if isinstance(record, TaskClassRecord):
                continue
            if isinstance(record, SessionRecord):
                label = record.goal
                record_type = "session"
            elif isinstance(record, TaskRecord):
                label = record.text
                record_type = "task"
            elif isinstance(record, ReasoningRecord):
                label = record.text
                record_type = "reasoning"
            elif isinstance(record, RetrievalRecord):
                label = record.query
                record_type = "retrieval"
            elif isinstance(record, AttentionRecord):
                label = record.query
                record_type = "attention"
            else:
                label = record.verdict
                record_type = "outcome"
            nodes.append(MergedNode(record.id, label, record_type, self.layer))
        return SourceGraph(
            self.layer,
            tuple(nodes),
            _session_edges(records),
            self.read_only,
            (repo / ".score-local" / "sessions.jsonl").exists(),
        )


class ProcessSource:
    layer = "process"
    read_only = True

    def _path(self, repo: Path, policy: Policy) -> Path | None:
        if not policy.process.enabled:
            return None
        configured = os.environ.get("SCORE_PROCESS_GRAPH")
        if configured:
            path = Path(configured)
            return path if path.is_absolute() else repo / path
        if policy.process.path:
            configured_path = Path(policy.process.path)
            return (
                configured_path
                if configured_path.is_absolute()
                else repo / configured_path
            )
        installed = (
            Path(__file__).resolve().parents[2]
            / "metamodel-flow"
            / "model"
            / "process_graph.json"
        )
        if installed.exists():
            return installed
        return repo / "score-context" / "process_graph.json"

    def load(self, repo: Path, policy: Policy) -> SourceGraph:
        path = self._path(repo, policy)
        if path is None or not path.exists():
            return SourceGraph(self.layer, (), (), self.read_only, False)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if (
                type(raw) is not dict
                or type(raw.get("schema_version")) is not int
                or raw.get("schema_version") != 1
            ):
                raise ValueError("invalid process graph schema")
            source = raw.get("source")
            nodes_raw = raw.get("nodes")
            edges_raw = raw.get("edges")
            if type(source) is not dict:
                raise ValueError("invalid process graph source")
            required_source = ("repo", "commit", "digest", "generated_at")
            if any(type(source.get(key)) is not str for key in required_source):
                raise ValueError("invalid process graph source fields")
            if type(nodes_raw) is not list or type(edges_raw) is not list:
                raise ValueError("invalid process graph arrays")
            limits = policy.overlay
            if len(nodes_raw) > limits.max_nodes or len(edges_raw) > limits.max_edges:
                raise ValueError("process graph exceeds policy limits")
            provenance = Provenance(
                repo=source["repo"],
                adapter="process_description",
                confidence=1.0,
                observed_at=source["generated_at"],
                sha=source["digest"],
            )
            nodes: list[MergedNode] = []
            node_ids: set[str] = set()
            for raw_node in nodes_raw:
                if type(raw_node) is not dict:
                    raise ValueError("invalid process graph node")
                node_id = raw_node.get("id")
                node_type = raw_node.get("type")
                title = raw_node.get("title")
                attributes = raw_node.get("attributes", {})
                if not all(type(value) is str for value in (node_id, node_type, title)):
                    raise ValueError("invalid process graph node fields")
                if (
                    len(title) > limits.max_title_chars
                    or type(attributes) is not dict
                    or len(attributes) > limits.max_attributes
                    or any(
                        type(key) is not str or type(value) is not str
                        for key, value in attributes.items()
                    )
                    or any(
                        len(value) > limits.max_attribute_chars
                        for value in attributes.values()
                    )
                ):
                    raise ValueError("invalid process graph attributes")
                if node_id in node_ids:
                    raise ValueError("duplicate process graph node")
                node_ids.add(node_id)
                nodes.append(
                    MergedNode(
                        node_id,
                        title,
                        node_type,
                        self.layer,
                        provenance=provenance,
                    )
                )
            edges: list[MergedEdge] = []
            for raw_edge in edges_raw:
                if type(raw_edge) is not dict:
                    raise ValueError("invalid process graph edge")
                edge_source = raw_edge.get("source")
                edge_target = raw_edge.get("target")
                relation = raw_edge.get("relation")
                if not all(
                    type(value) is str for value in (edge_source, edge_target, relation)
                ):
                    raise ValueError("invalid process graph edge fields")
                if edge_source not in node_ids or edge_target not in node_ids:
                    continue
                edges.append(
                    MergedEdge(
                        edge_source,
                        edge_target,
                        relation,
                        self.layer,
                        provenance,
                    )
                )
            return SourceGraph(
                self.layer,
                tuple(nodes),
                tuple(edges),
                self.read_only,
                True,
            )
        except (OSError, UnicodeError, TypeError, ValueError):
            return SourceGraph(self.layer, (), (), self.read_only, False)


DEFAULT_SOURCES = (
    CodeGraphSource(),
    OverlaySource(),
    ProcessSource(),
    SessionSource(),
)
