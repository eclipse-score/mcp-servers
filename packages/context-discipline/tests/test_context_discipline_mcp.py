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

import json
from pathlib import Path

from context_discipline_mcp import (
    ContextDisciplineMCP,
    SessionRecord,
    call_tool,
)


def test_initialize_session_writes_one_session_record(tmp_path: Path) -> None:
    manager = ContextDisciplineMCP(str(tmp_path))
    session_id = manager.initialize_session("Goal", ["Subgoal"], agent="agent")

    records = manager.session_log.read_all()
    sessions = [record for record in records if isinstance(record, SessionRecord)]
    assert session_id == manager.session_id
    assert len(sessions) == 1
    assert sessions[0].goal == "Goal"


def test_add_overlay_node_uses_repo_slug_and_wire_names(tmp_path: Path) -> None:
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text(
        json.dumps({"nodes": [{"id": "code__one", "label": "Code"}]}),
        encoding="utf-8",
    )
    manager = ContextDisciplineMCP(str(tmp_path))

    result = call_tool(
        manager,
        "add_overlay_node",
        {
            "id": "dec__one",
            "type": "dec_rec",
            "title": "Decision",
            "relation": "affects",
            "target": "code__one",
            "confidence": 0.9,
        },
    )

    assert result["node"]["id"] == "dec__one"
    assert result["node"]["provenance"]["repo"] == tmp_path.name
    assert result["edge"]["source"] == "dec__one"
