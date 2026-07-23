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
from typing import cast

from score_context.context import ContextEngine, get_context
from score_context.graph import compose_fragments


def test_compose_and_get_context_select_expected_nodes() -> None:
    root = Path(__file__).parents[3]
    graph = compose_fragments([root / "harness/spec/graph_fragment.json"])
    task: dict[str, object] = {
        "id": "task_001_contract_change",
        "seed_node_ids": ["pr__mcp_servers__42"],
        "expected_node_ids": [
            "pr__mcp_servers__42",
            "contract__score_context__v1",
            "dec_rec__strat__agent_context_attention_layer",
        ],
        "top_n": 5,
    }
    selection = get_context(graph, task, "mcp-servers", "developer", 5)
    engine_selection = ContextEngine(graph).get_context(
        task, "mcp-servers", "developer", 5
    )
    selected_ids = {node.id for node in selection.selected}
    assert engine_selection.model_dump() == selection.model_dump()
    expected = cast(list[str], task["expected_node_ids"])
    assert set(expected) <= selected_ids
    assert selection.decisions[0].id == "dec_rec__strat__agent_context_attention_layer"
    assert selection.contracts[0].id == "contract__score_context__v1"
