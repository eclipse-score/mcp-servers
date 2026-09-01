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
import shutil
import subprocess
from pathlib import Path

import pytest
from context_merge import MergedGraph
from context_overlay import OverlayEdge, OverlayNode, OverlayStore, Provenance


@pytest.mark.skipif(
    shutil.which("graphify") is None,
    reason="graphify CLI not installed",
)
def test_overlay_survives_graphify_extraction(tmp_path: Path) -> None:
    (tmp_path / "one.py").write_text("def one():\n    return 1\n", encoding="utf-8")
    (tmp_path / "two.py").write_text("from one import one\n", encoding="utf-8")
    subprocess.run(
        [
            "graphify",
            "extract",
            str(tmp_path),
            "--code-only",
            "--out",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    graph_path = tmp_path / "graphify-out" / "graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    code_nodes = [
        node
        for node in graph["nodes"]
        if str(node.get("source_file", "")).endswith("one.py")
    ]
    assert code_nodes
    code_node = code_nodes[0]["id"]

    provenance = Provenance("test", "test", 1.0, "2026-01-01T00:00:00Z")
    overlay = OverlayStore(tmp_path)
    overlay.upsert_node(OverlayNode("dec_rec__one", "dec_rec", "Decision", provenance))
    overlay.upsert_edge(OverlayEdge("dec_rec__one", code_node, "affects", provenance))
    overlay.save()
    merged = MergedGraph.build(tmp_path)
    assert merged.nodes["dec_rec__one"].layer == "domain"
    assert any(node.id == code_node for node in merged.neighbors("dec_rec__one"))

    (tmp_path / "one.py").write_text(
        "def one():\n    return 2\n\ndef extra():\n    return 3\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "graphify",
            "extract",
            str(tmp_path),
            "--code-only",
            "--out",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    merged = MergedGraph.build(tmp_path)
    assert merged.has_node("dec_rec__one")
    assert merged.has_node(code_node)

    # the equivalent node injected into `graph.json` is pruned here
    (tmp_path / "one.py").unlink()
    subprocess.run(
        [
            "graphify",
            "extract",
            str(tmp_path),
            "--code-only",
            "--out",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    merged = MergedGraph.build(tmp_path)
    assert merged.has_node("dec_rec__one")
    assert not merged.has_node(code_node)
    assert any(
        edge.source == "dec_rec__one" and edge.target == code_node
        for edge in merged.dangling_edges
    )
