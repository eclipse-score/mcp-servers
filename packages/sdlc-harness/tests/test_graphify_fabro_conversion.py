# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
"""Tests for graphify ↔ fabro conversion."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from graphify_fabro_conversion import (
    FABRO_SHAPE_HANDLER,
    FabroEdge,
    FabroNode,
    FabroWorkflow,
    GraphifyEdge,
    GraphifyGraph,
    GraphifyNode,
    _escape_dot,
    _parse_dot_attributes,
    _safe_id,
    convert_fabro_dot_to_graphify,
    convert_graphify_to_fabro_dot,
    convert_process_graph_to_fabro_dot,
    convert_sdlc_to_fabro_dot,
    dot_to_fabro_workflow,
    fabro_to_dot,
    fabro_to_graphify,
    graphify_to_fabro,
    process_graph_to_fabro,
    process_graph_to_graphify,
    sdlc_to_fabro,
)


# ---------------------------------------------------------------------------
# GraphifyGraph serialization
# ---------------------------------------------------------------------------


class TestGraphifyGraph:
    def test_to_dict_roundtrip(self) -> None:
        graph = GraphifyGraph(
            nodes=[
                GraphifyNode(id="n1", name="foo", kind="function", path="a.py", line=10),
                GraphifyNode(id="n2", name="bar", kind="class", path="b.py"),
            ],
            edges=[GraphifyEdge(source="n1", target="n2", kind="calls")],
            metadata={"goal": "test"},
        )
        data = graph.to_dict()
        restored = GraphifyGraph.from_dict(data)

        assert len(restored.nodes) == 2
        assert restored.nodes[0].name == "foo"
        assert len(restored.edges) == 1
        assert restored.edges[0].kind == "calls"

    def test_from_file(self, tmp_path: Path) -> None:
        graph_data = {
            "nodes": [
                {"id": "m1", "name": "main", "kind": "module", "path": "main.py"},
            ],
            "edges": [],
            "metadata": {},
        }
        graph_file = tmp_path / "graph.json"
        graph_file.write_text(json.dumps(graph_data), encoding="utf-8")

        graph = GraphifyGraph.from_file(graph_file)
        assert len(graph.nodes) == 1
        assert graph.nodes[0].name == "main"


# ---------------------------------------------------------------------------
# Graphify → Fabro conversion
# ---------------------------------------------------------------------------


class TestGraphifyToFabro:
    def test_creates_start_and_exit(self) -> None:
        graph = GraphifyGraph(
            nodes=[GraphifyNode(id="n1", name="foo", kind="function")],
            edges=[],
        )
        wf = graphify_to_fabro(graph, "Test")
        ids = {n.id for n in wf.nodes}
        assert "start" in ids
        assert "exit" in ids

    def test_creates_nodes_from_graph(self) -> None:
        graph = GraphifyGraph(
            nodes=[
                GraphifyNode(id="n1", name="foo", kind="function"),
                GraphifyNode(id="n2", name="Bar", kind="class"),
            ],
            edges=[GraphifyEdge(source="n1", target="n2", kind="calls")],
        )
        wf = graphify_to_fabro(graph, "Test")
        # start + 2 code nodes + exit = 4
        assert len(wf.nodes) == 4

    def test_structural_nodes_get_box_shape(self) -> None:
        graph = GraphifyGraph(
            nodes=[GraphifyNode(id="m", name="mymod", kind="module")],
            edges=[],
        )
        wf = graphify_to_fabro(graph, "Test")
        mod_node = next(n for n in wf.nodes if n.id == "m")
        assert mod_node.shape == "box"

    def test_function_nodes_get_tab_shape(self) -> None:
        graph = GraphifyGraph(
            nodes=[GraphifyNode(id="f", name="func", kind="function")],
            edges=[],
        )
        wf = graphify_to_fabro(graph, "Test")
        func_node = next(n for n in wf.nodes if n.id == "f")
        assert func_node.shape == "tab"

    def test_preserves_edges(self) -> None:
        graph = GraphifyGraph(
            nodes=[
                GraphifyNode(id="n1", name="foo", kind="function"),
                GraphifyNode(id="n2", name="bar", kind="function"),
            ],
            edges=[GraphifyEdge(source="n1", target="n2", kind="calls")],
        )
        wf = graphify_to_fabro(graph, "Test")
        pairs = wf.edge_pairs
        assert ("n1", "n2") in pairs

    def test_uses_metadata_goal(self) -> None:
        graph = GraphifyGraph(
            nodes=[GraphifyNode(id="n1", name="foo", kind="function")],
            edges=[],
            metadata={"goal": "Analyze auth module"},
        )
        wf = graphify_to_fabro(graph, "Auth")
        assert wf.graph_attributes["goal"] == "Analyze auth module"

    def test_empty_graph(self) -> None:
        graph = GraphifyGraph()
        wf = graphify_to_fabro(graph, "Empty")
        ids = {n.id for n in wf.nodes}
        assert "start" in ids
        assert "exit" in ids


# ---------------------------------------------------------------------------
# Fabro → Graphify conversion
# ---------------------------------------------------------------------------


class TestFabroToGraphify:
    def test_basic(self) -> None:
        wf = FabroWorkflow(
            name="Test",
            nodes=[
                FabroNode(id="start", label="Start", shape="Mdiamond"),
                FabroNode(id="do", label="Do", shape="box", prompt="Do it"),
                FabroNode(id="exit", label="Exit", shape="Msquare"),
            ],
            edges=[
                FabroEdge(source="start", target="do"),
                FabroEdge(source="do", target="exit"),
            ],
        )
        g = fabro_to_graphify(wf)
        assert len(g.nodes) == 3
        assert len(g.edges) == 2

    def test_shape_to_kind_mapping(self) -> None:
        wf = FabroWorkflow(
            name="Test",
            nodes=[
                FabroNode(id="s", shape="Mdiamond"),
                FabroNode(id="e", shape="Msquare"),
                FabroNode(id="cmd", shape="parallelogram"),
                FabroNode(id="human", shape="hexagon"),
                FabroNode(id="cond", shape="diamond"),
            ],
            edges=[],
        )
        g = fabro_to_graphify(wf)
        kinds = {n.id: n.kind for n in g.nodes}
        assert kinds["s"] == "entry_point"
        assert kinds["e"] == "exit_point"
        assert kinds["cmd"] == "command"
        assert kinds["human"] == "decision"
        assert kinds["cond"] == "conditional"

    def test_preserves_prompt(self) -> None:
        wf = FabroWorkflow(
            name="Test",
            nodes=[FabroNode(id="n", label="Task", prompt="Analyze code")],
            edges=[],
        )
        g = fabro_to_graphify(wf)
        assert g.nodes[0].properties["prompt"] == "Analyze code"

    def test_preserves_fabro_attributes(self) -> None:
        wf = FabroWorkflow(
            name="Test",
            nodes=[
                FabroNode(
                    id="n", fidelity="full", thread_id="impl",
                    goal_gate=True, max_visits=3,
                ),
            ],
            edges=[],
        )
        g = fabro_to_graphify(wf)
        props = g.nodes[0].properties
        assert props["fidelity"] == "full"
        assert props["thread_id"] == "impl"
        assert props["goal_gate"] is True
        assert props["max_visits"] == 3

    def test_handler_property(self) -> None:
        assert FabroNode(id="a", shape="box").handler == "agent"
        assert FabroNode(id="b", shape="tab").handler == "prompt"
        assert FabroNode(id="c", script="echo hi").handler == "command"
        assert FabroNode(id="d", type="human").handler == "human"
        assert FabroNode(id="e").handler == "agent"  # default


# ---------------------------------------------------------------------------
# DOT serialization
# ---------------------------------------------------------------------------


class TestFabroToDot:
    def test_digraph_header(self) -> None:
        wf = FabroWorkflow(name="MyWf", nodes=[])
        dot = fabro_to_dot(wf)
        assert dot.startswith("digraph MyWf {")

    def test_graph_attributes(self) -> None:
        wf = FabroWorkflow(
            name="Test",
            graph_attributes={"goal": "Build it", "rankdir": "LR"},
        )
        dot = fabro_to_dot(wf)
        assert 'goal="Build it"' in dot
        assert 'rankdir="LR"' in dot

    def test_node_serialization(self) -> None:
        wf = FabroWorkflow(
            name="Test",
            nodes=[
                FabroNode(id="start", label="Start", shape="Mdiamond"),
                FabroNode(
                    id="do", label="Do", shape="box",
                    prompt="Do analysis", goal_gate=True,
                ),
            ],
        )
        dot = fabro_to_dot(wf)
        assert "start [" in dot
        assert "shape=Mdiamond" in dot
        assert 'prompt="Do analysis"' in dot
        assert "goal_gate=true" in dot

    def test_edge_serialization(self) -> None:
        wf = FabroWorkflow(
            name="Test",
            edges=[
                FabroEdge(
                    source="a", target="b",
                    label="Go", condition="outcome=succeeded",
                ),
            ],
        )
        dot = fabro_to_dot(wf)
        assert "a -> b" in dot
        assert 'label="Go"' in dot
        assert 'condition="outcome=succeeded"' in dot

    def test_escapes_quotes(self) -> None:
        wf = FabroWorkflow(
            name="Test",
            nodes=[FabroNode(id="n", label='Say "hello"')],
        )
        dot = fabro_to_dot(wf)
        assert 'Say \\"hello\\"' in dot

    def test_roundtrip(self) -> None:
        wf = FabroWorkflow(
            name="TestWf",
            nodes=[
                FabroNode(id="start", label="Start", shape="Mdiamond"),
                FabroNode(id="do", label="Do", shape="box", prompt="Do it"),
                FabroNode(id="exit", label="Exit", shape="Msquare"),
            ],
            edges=[
                FabroEdge(source="start", target="do", label="Go"),
                FabroEdge(source="do", target="exit"),
            ],
            graph_attributes={"goal": "Test round-trip"},
        )
        dot = fabro_to_dot(wf)
        restored = dot_to_fabro_workflow(dot)
        assert restored.name == "TestWf"
        assert len(restored.nodes) == 3
        assert len(restored.edges) == 2
        assert restored.nodes[1].prompt == "Do it"
        assert restored.graph_attributes["goal"] == "Test round-trip"


# ---------------------------------------------------------------------------
# DOT parsing
# ---------------------------------------------------------------------------


class TestDotParsing:
    def test_rejects_undirected(self) -> None:
        with pytest.raises(ValueError, match="Not a valid Fabro digraph"):
            dot_to_fabro_workflow("graph foo { }")

    def test_graph_block_attributes(self) -> None:
        dot = 'digraph X {\n    graph [goal="Build", rankdir="LR"]\n    start [shape=Mdiamond]\n}'
        wf = dot_to_fabro_workflow(dot)
        assert wf.graph_attributes["goal"] == "Build"
        assert wf.graph_attributes["rankdir"] == "LR"

    def test_bare_graph_attributes(self) -> None:
        dot = 'digraph X {\n    rankdir=LR\n    start [shape=Mdiamond]\n}'
        wf = dot_to_fabro_workflow(dot)
        assert wf.graph_attributes["rankdir"] == "LR"

    def test_chained_edges(self) -> None:
        dot = "digraph X {\n    a [shape=box]\n    b [shape=box]\n    c [shape=box]\n    a -> b -> c\n}"
        wf = dot_to_fabro_workflow(dot)
        pairs = wf.edge_pairs
        assert ("a", "b") in pairs
        assert ("b", "c") in pairs

    def test_chained_edges_with_attrs(self) -> None:
        dot = 'digraph X {\n    a [shape=box]\n    b [shape=box]\n    c [shape=box]\n    a -> b -> c [label="Flow"]\n}'
        wf = dot_to_fabro_workflow(dot)
        assert all(e.label == "Flow" for e in wf.edges)

    def test_comments_stripped(self) -> None:
        dot = """digraph X {
    // This is a comment
    /* Block
       comment */
    start [shape=Mdiamond, label="Start"]
    # Hash comment
    exit [shape=Msquare]
    start -> exit
}"""
        wf = dot_to_fabro_workflow(dot)
        assert len(wf.nodes) == 2
        assert len(wf.edges) == 1

    def test_node_defaults(self) -> None:
        dot = 'digraph X {\n    node [shape=box]\n    a [label="A"]\n    b [label="B"]\n}'
        wf = dot_to_fabro_workflow(dot)
        assert wf.nodes[0].shape == "box"
        assert wf.nodes[1].shape == "box"

    def test_node_overrides_defaults(self) -> None:
        dot = 'digraph X {\n    node [shape=box]\n    a [label="A", shape=tab]\n}'
        wf = dot_to_fabro_workflow(dot)
        assert wf.nodes[0].shape == "tab"

    def test_fabro_attributes(self) -> None:
        dot = """digraph X {
    do [label="Do", shape=box, prompt="Analyze code", fidelity="full", thread_id="impl", goal_gate=true, max_visits=3]
}"""
        wf = dot_to_fabro_workflow(dot)
        n = wf.nodes[0]
        assert n.prompt == "Analyze code"
        assert n.fidelity == "full"
        assert n.thread_id == "impl"
        assert n.goal_gate is True
        assert n.max_visits == 3

    def test_edge_conditions(self) -> None:
        dot = 'digraph X {\n    a [shape=diamond]\n    b [shape=box]\n    a -> b [condition="outcome=succeeded", label="Pass"]\n}'
        wf = dot_to_fabro_workflow(dot)
        assert wf.edges[0].condition == "outcome=succeeded"
        assert wf.edges[0].label == "Pass"

    def test_subgraph_nodes_flattened(self) -> None:
        dot = """digraph X {
    subgraph cluster_impl {
        a [label="A"]
        b [label="B"]
    }
    a -> b
}"""
        wf = dot_to_fabro_workflow(dot)
        ids = {n.id for n in wf.nodes}
        assert "a" in ids
        assert "b" in ids


# ---------------------------------------------------------------------------
# SDLC → Fabro workflow
# ---------------------------------------------------------------------------


class TestSdlcToFabro:
    def test_creates_sdlc_stages(self) -> None:
        wf = sdlc_to_fabro("ISSUE-42", "Add auth")
        ids = {n.id for n in wf.nodes}
        assert "start" in ids
        assert "bootstrap" in ids
        assert "fill_drafts" in ids
        assert "assess" in ids
        assert "implement" in ids
        assert "record_evidence" in ids
        assert "assess_progress" in ids
        assert "check_complete" in ids
        assert "review_gate" in ids
        assert "exit" in ids

    def test_has_loopback_nodes(self) -> None:
        wf = sdlc_to_fabro("ISSUE-42")
        ids = {n.id for n in wf.nodes}
        assert "loopback_gate" in ids
        assert "record_loopback" in ids

    def test_goal_gates(self) -> None:
        wf = sdlc_to_fabro("ISSUE-42")
        gated = [n.id for n in wf.nodes if n.goal_gate]
        assert "assess" in gated
        assert "check_complete" in gated

    def test_workflow_name(self) -> None:
        wf = sdlc_to_fabro("ISSUE-42")
        assert wf.name == "SDLC_ISSUE_42"

    def test_goal_includes_requirement(self) -> None:
        wf = sdlc_to_fabro("X", "Add OAuth2 support")
        assert "Add OAuth2 support" in wf.graph_attributes["goal"]

    def test_model_stylesheet(self) -> None:
        wf = sdlc_to_fabro("X", model="claude-sonnet-4-5")
        assert "model_stylesheet" in wf.graph_attributes
        assert "claude-sonnet-4-5" in wf.graph_attributes["model_stylesheet"]

    def test_human_review_gate(self) -> None:
        wf = sdlc_to_fabro("ISSUE-42")
        review = next(n for n in wf.nodes if n.id == "review_gate")
        assert review.shape == "hexagon"
        # Should have approve and revise edges.
        review_edges = [e for e in wf.edges if e.source == "review_gate"]
        labels = {e.label for e in review_edges}
        assert "[A] Approve" in labels
        assert "[R] Revise" in labels

    def test_loopback_returns_to_fill_drafts(self) -> None:
        wf = sdlc_to_fabro("ISSUE-42")
        loopback_edge = next(
            e for e in wf.edges if e.source == "record_loopback"
        )
        assert loopback_edge.target == "fill_drafts"

    def test_renders_valid_dot(self) -> None:
        dot = convert_sdlc_to_fabro_dot("ISSUE-42", "Add auth")
        assert dot.startswith("digraph SDLC_ISSUE_42 {")
        assert "bootstrap" in dot
        assert "fill_drafts" in dot
        assert "review_gate" in dot

    def test_sdlc_dot_roundtrip(self) -> None:
        dot = convert_sdlc_to_fabro_dot("ISSUE-99")
        wf = dot_to_fabro_workflow(dot)
        assert wf.name == "SDLC_ISSUE_99"
        assert len(wf.nodes) >= 10
        assert any(e.condition for e in wf.edges)


# ---------------------------------------------------------------------------
# Full round-trips
# ---------------------------------------------------------------------------


class TestRoundTrips:
    def test_graphify_to_fabro_to_graphify(self) -> None:
        original = GraphifyGraph(
            nodes=[
                GraphifyNode(id="n1", name="foo", kind="function", path="a.py"),
                GraphifyNode(id="n2", name="Bar", kind="class"),
            ],
            edges=[GraphifyEdge(source="n1", target="n2", kind="calls")],
            metadata={"goal": "test"},
        )
        wf = graphify_to_fabro(original, "Test")
        restored = fabro_to_graphify(wf)
        assert len(restored.nodes) == len(wf.nodes)
        assert len(restored.edges) == len(wf.edges)

    def test_fabro_dot_roundtrip(self) -> None:
        original = FabroWorkflow(
            name="TestWf",
            nodes=[
                FabroNode(id="start", label="Start", shape="Mdiamond"),
                FabroNode(
                    id="do", label="Do", shape="box",
                    prompt="Do analysis", fidelity="full",
                    thread_id="impl", goal_gate=True,
                ),
                FabroNode(id="exit", label="Exit", shape="Msquare"),
            ],
            edges=[
                FabroEdge(source="start", target="do"),
                FabroEdge(
                    source="do", target="exit",
                    condition="outcome=succeeded",
                ),
            ],
            graph_attributes={"goal": "Test"},
        )
        dot = fabro_to_dot(original)
        restored = dot_to_fabro_workflow(dot)
        assert restored.name == original.name
        assert len(restored.nodes) == len(original.nodes)
        assert restored.nodes[1].fidelity == "full"
        assert restored.nodes[1].thread_id == "impl"
        assert restored.nodes[1].goal_gate is True


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    def test_convert_graphify_to_fabro_dot(self, tmp_path: Path) -> None:
        data = {
            "nodes": [{"id": "n1", "name": "foo", "kind": "function"}],
            "edges": [],
            "metadata": {},
        }
        p = tmp_path / "graph.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        dot = convert_graphify_to_fabro_dot(p, "Test")
        assert "digraph Test" in dot

    def test_convert_fabro_dot_to_graphify(self) -> None:
        dot = """digraph X {
    start [shape=Mdiamond, label="Start"]
    do [shape=box, prompt="Analyze"]
    exit [shape=Msquare, label="Exit"]
    start -> do -> exit
}"""
        g = convert_fabro_dot_to_graphify(dot)
        assert len(g.nodes) == 3
        assert g.nodes[1].properties["prompt"] == "Analyze"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_safe_id(self) -> None:
        assert _safe_id("valid_id") == "valid_id"
        assert _safe_id("module:func") == "module_func"
        assert _safe_id("123num") == "n_123num"
        assert _safe_id("") == "unnamed"
        assert _safe_id("a.b-c") == "a_b_c"

    def test_escape_dot(self) -> None:
        assert _escape_dot('say "hi"') == 'say \\"hi\\"'
        assert _escape_dot("back\\slash") == "back\\\\slash"
        assert _escape_dot("line1\nline2") == "line1\\nline2"

    def test_parse_dot_attributes_empty(self) -> None:
        assert _parse_dot_attributes("") == {}
        assert _parse_dot_attributes("   ") == {}

    def test_parse_dot_attributes_simple(self) -> None:
        attrs = _parse_dot_attributes('label="Hello", shape=box')
        assert attrs["label"] == "Hello"
        assert attrs["shape"] == "box"

    def test_parse_dot_attributes_escaped_quotes(self) -> None:
        attrs = _parse_dot_attributes('prompt="He said \\"hi\\""')
        assert attrs["prompt"] == 'He said "hi"'

    def test_parse_dot_attributes_boolean_and_int(self) -> None:
        attrs = _parse_dot_attributes("goal_gate=true, max_visits=3")
        assert attrs["goal_gate"] == "true"
        assert attrs["max_visits"] == "3"

    def test_parse_dot_attributes_semicolons(self) -> None:
        attrs = _parse_dot_attributes('label="A"; shape=box')
        assert attrs["label"] == "A"
        assert attrs["shape"] == "box"


# ---------------------------------------------------------------------------
# Edge cases and scalability
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_large_graph(self) -> None:
        nodes = [
            GraphifyNode(id=f"n{i}", name=f"f{i}", kind="function")
            for i in range(50)
        ]
        edges = [
            GraphifyEdge(source=f"n{i}", target=f"n{i+1}", kind="calls")
            for i in range(49)
        ]
        graph = GraphifyGraph(nodes=nodes, edges=edges)
        wf = graphify_to_fabro(graph, "Big")
        # 50 code nodes + start + exit = 52
        assert len(wf.nodes) == 52
        assert len(wf.edges) >= 49

    def test_dot_with_multiline_prompt(self) -> None:
        wf = FabroWorkflow(
            name="Test",
            nodes=[
                FabroNode(id="n", prompt="Line 1\nLine 2\nLine 3"),
            ],
        )
        dot = fabro_to_dot(wf)
        assert "\\n" in dot
        restored = dot_to_fabro_workflow(dot)
        assert restored.nodes[0].prompt == "Line 1\nLine 2\nLine 3"

    def test_handler_shapes_complete(self) -> None:
        """Every Fabro shape maps to a known handler."""
        for shape, handler in FABRO_SHAPE_HANDLER.items():
            assert handler, f"Shape {shape} has no handler"


# ---------------------------------------------------------------------------
# Process graph → Fabro / Graphify conversion
# ---------------------------------------------------------------------------

# Minimal process_graph.json fixture with ISO 26262 semantics.
_PROCESS_GRAPH_FIXTURE: dict = {
    "schema_version": 1,
    "source": {
        "repo": "eclipse-score/process_description",
        "commit": "abc123",
        "digest": "sha256:deadbeef",
    },
    "nodes": [
        {"id": "wf__req_feat_req", "type": "workflow",
         "title": "Create/Maintain Feature requirements",
         "attributes": {"status": "valid", "tags": "requirements_engineering"}},
        {"id": "wf__cr_mt_featarch", "type": "workflow",
         "title": "Create/Maintain Feature architecture",
         "attributes": {"status": "valid", "tags": "architecture_design"}},
        {"id": "wf__verification_feat_int_test", "type": "workflow",
         "title": "Create/Maintain Feature Integration Test",
         "attributes": {"status": "valid", "tags": "verification"}},
        {"id": "wp__feat_req", "type": "workproduct",
         "title": "Feature Requirements",
         "attributes": {"status": "valid", "tags": "requirements_engineering"}},
        {"id": "wp__feat_arch", "type": "workproduct",
         "title": "Feature Architecture",
         "attributes": {"status": "valid", "tags": "architecture_design"}},
        {"id": "rl__contributor", "type": "role",
         "title": "Contributor",
         "attributes": {"status": "valid", "tags": "development"}},
        {"id": "rl__arch_community", "type": "role",
         "title": "Architecture Community Member",
         "attributes": {"status": "valid", "tags": "architecture_design"}},
        {"id": "rl__safety_mgr", "type": "role",
         "title": "Safety Manager",
         "attributes": {"status": "valid", "tags": "safety_management"}},
        {"id": "gd_req__req_attr", "type": "gd_req",
         "title": "Requirement attribute: description",
         "attributes": {"status": "valid", "tags": "requirements_engineering"}},
        {"id": "gd_temp__feat_req", "type": "gd_temp",
         "title": "Feature Requirements Template",
         "attributes": {"status": "valid", "tags": "requirements_engineering"}},
        {"id": "std_req__aspice_swe1", "type": "std_req",
         "title": "SWE.1.BP1: Elicit requirements",
         "attributes": {"status": "valid", "tags": "aspice40_swe1"}},
    ],
    "edges": [
        # requirements → outputs Feature Requirements
        {"source": "wf__req_feat_req", "relation": "output", "target": "wp__feat_req"},
        # architecture inputs Feature Requirements, outputs Feature Architecture
        {"source": "wf__cr_mt_featarch", "relation": "input", "target": "wp__feat_req"},
        {"source": "wf__cr_mt_featarch", "relation": "output", "target": "wp__feat_arch"},
        # verification inputs Feature Architecture
        {"source": "wf__verification_feat_int_test", "relation": "input", "target": "wp__feat_arch"},
        # roles
        {"source": "wf__req_feat_req", "relation": "responsible", "target": "rl__contributor"},
        {"source": "wf__req_feat_req", "relation": "approved_by", "target": "rl__arch_community"},
        {"source": "wf__req_feat_req", "relation": "supported_by", "target": "rl__safety_mgr"},
        {"source": "wf__cr_mt_featarch", "relation": "responsible", "target": "rl__contributor"},
        # contains
        {"source": "wf__req_feat_req", "relation": "contains", "target": "gd_temp__feat_req"},
        # satisfies + complies chain
        {"source": "gd_req__req_attr", "relation": "satisfies", "target": "wf__req_feat_req"},
        {"source": "gd_req__req_attr", "relation": "complies", "target": "std_req__aspice_swe1"},
    ],
}


class TestProcessGraphToGraphify:
    def test_adapts_schema(self) -> None:
        g = process_graph_to_graphify(_PROCESS_GRAPH_FIXTURE)
        assert len(g.nodes) == 11
        assert len(g.edges) == 11
        wf = next(n for n in g.nodes if n.id == "wf__req_feat_req")
        assert wf.kind == "workflow"
        assert wf.name == "Create/Maintain Feature requirements"

    def test_preserves_metadata(self) -> None:
        g = process_graph_to_graphify(_PROCESS_GRAPH_FIXTURE)
        assert g.metadata["source_repo"] == "eclipse-score/process_description"
        assert g.metadata["source_commit"] == "abc123"


class TestProcessGraphToFabro:
    def test_creates_workflow_nodes(self) -> None:
        wf = process_graph_to_fabro(_PROCESS_GRAPH_FIXTURE)
        ids = {n.id for n in wf.nodes}
        assert "wf__req_feat_req" in ids
        assert "wf__cr_mt_featarch" in ids
        assert "wf__verification_feat_int_test" in ids

    def test_derives_workproduct_sequencing(self) -> None:
        """req → outputs Feature Requirements → inputs architecture."""
        wf = process_graph_to_fabro(_PROCESS_GRAPH_FIXTURE)
        pairs = wf.edge_pairs
        # req workflow (or its approval gate) → arch workflow via Feature Requirements
        req_out_id = next(
            (n.id for n in wf.nodes if "approve" in n.id and "req_feat_req" in n.id),
            "wf__req_feat_req",
        )
        assert (req_out_id, "wf__cr_mt_featarch") in pairs

    def test_inserts_approval_gates(self) -> None:
        """req workflow has approved_by → should get a hexagon gate."""
        wf = process_graph_to_fabro(_PROCESS_GRAPH_FIXTURE)
        gates = [n for n in wf.nodes if n.shape == "hexagon"]
        assert len(gates) >= 1
        gate = next(g for g in gates if "req_feat_req" in g.id)
        assert "Approve" in gate.label

    def test_prompt_includes_workproducts(self) -> None:
        wf = process_graph_to_fabro(_PROCESS_GRAPH_FIXTURE)
        req_node = next(n for n in wf.nodes if n.id == "wf__req_feat_req")
        assert "Feature Requirements" in req_node.prompt

    def test_prompt_includes_roles(self) -> None:
        wf = process_graph_to_fabro(_PROCESS_GRAPH_FIXTURE)
        req_node = next(n for n in wf.nodes if n.id == "wf__req_feat_req")
        assert "Contributor" in req_node.prompt
        assert "Safety Manager" in req_node.prompt

    def test_prompt_includes_templates(self) -> None:
        wf = process_graph_to_fabro(_PROCESS_GRAPH_FIXTURE)
        req_node = next(n for n in wf.nodes if n.id == "wf__req_feat_req")
        assert "Feature Requirements Template" in req_node.prompt

    def test_prompt_includes_compliance(self) -> None:
        wf = process_graph_to_fabro(_PROCESS_GRAPH_FIXTURE)
        req_node = next(n for n in wf.nodes if n.id == "wf__req_feat_req")
        assert "SWE.1.BP1" in req_node.prompt

    def test_filter_by_domain_tag(self) -> None:
        wf = process_graph_to_fabro(
            _PROCESS_GRAPH_FIXTURE,
            workflow_filter="requirements_engineering",
        )
        wf_nodes = [n for n in wf.nodes if n.shape == "box"]
        assert len(wf_nodes) == 1
        assert wf_nodes[0].id == "wf__req_feat_req"

    def test_filter_by_id_prefix(self) -> None:
        wf = process_graph_to_fabro(
            _PROCESS_GRAPH_FIXTURE,
            workflow_filter="verification",
        )
        wf_nodes = [n for n in wf.nodes if n.shape == "box"]
        assert len(wf_nodes) == 1
        assert "verification" in wf_nodes[0].id

    def test_renders_valid_dot(self) -> None:
        wf = process_graph_to_fabro(_PROCESS_GRAPH_FIXTURE)
        dot = fabro_to_dot(wf)
        assert dot.startswith("digraph Process")

    def test_dot_roundtrip(self) -> None:
        wf = process_graph_to_fabro(_PROCESS_GRAPH_FIXTURE)
        dot = fabro_to_dot(wf)
        restored = dot_to_fabro_workflow(dot)
        assert len(restored.nodes) == len(wf.nodes)
        assert len(restored.edges) == len(wf.edges)

    def test_v_model_chain(self) -> None:
        """Full V-model: req → arch → verification via work products."""
        wf = process_graph_to_fabro(_PROCESS_GRAPH_FIXTURE)
        pairs = wf.edge_pairs
        # arch (or its gate) → verification via Feature Architecture
        arch_out = next(
            (n.id for n in wf.nodes
             if ("approve" in n.id or n.id == "wf__cr_mt_featarch")
             and any(e.source == n.id and e.target == "wf__verification_feat_int_test" for e in wf.edges)),
            None,
        )
        assert arch_out is not None, (
            f"No edge from arch to verification. Pairs: {pairs}"
        )


class TestProcessGraphWithRealData:
    """Test with the actual committed process_graph.json if available."""

    @pytest.fixture
    def real_process_graph(self) -> dict | None:
        p = Path(__file__).resolve().parents[2] / "metamodel-flow" / "model" / "process_graph.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return None

    def test_full_graph_converts(self, real_process_graph: dict | None) -> None:
        if real_process_graph is None:
            pytest.skip("process_graph.json not available")
        wf = process_graph_to_fabro(real_process_graph)
        assert len(wf.nodes) > 80  # 79 workflows + start + exit + approval gates
        assert len(wf.edges) > 100

    def test_full_graph_roundtrips(self, real_process_graph: dict | None) -> None:
        if real_process_graph is None:
            pytest.skip("process_graph.json not available")
        wf = process_graph_to_fabro(real_process_graph)
        dot = fabro_to_dot(wf)
        restored = dot_to_fabro_workflow(dot)
        assert len(restored.nodes) == len(wf.nodes)
        assert len(restored.edges) == len(wf.edges)

    def test_domain_filter_reduces_scope(self, real_process_graph: dict | None) -> None:
        if real_process_graph is None:
            pytest.skip("process_graph.json not available")
        full = process_graph_to_fabro(real_process_graph)
        req_only = process_graph_to_fabro(
            real_process_graph, workflow_filter="requirements_engineering",
        )
        assert len(req_only.nodes) < len(full.nodes)

    def test_every_workflow_has_prompt(self, real_process_graph: dict | None) -> None:
        if real_process_graph is None:
            pytest.skip("process_graph.json not available")
        wf = process_graph_to_fabro(real_process_graph)
        for node in wf.nodes:
            if node.shape == "box":
                assert node.prompt, f"Workflow node {node.id} has no prompt"

    def test_approval_gates_have_approvers(self, real_process_graph: dict | None) -> None:
        if real_process_graph is None:
            pytest.skip("process_graph.json not available")
        wf = process_graph_to_fabro(real_process_graph)
        for node in wf.nodes:
            if node.id.endswith("__approve"):
                assert "Approve" in node.label, f"Gate {node.id} missing Approve label"

    def test_graphify_adapter(self, real_process_graph: dict | None) -> None:
        if real_process_graph is None:
            pytest.skip("process_graph.json not available")
        g = process_graph_to_graphify(real_process_graph)
        assert len(g.nodes) == 1160
        assert len(g.edges) == 2999
        wf_nodes = [n for n in g.nodes if n.kind == "workflow"]
        assert len(wf_nodes) == 79


# ---------------------------------------------------------------------------
# Native Fabro validation (runs only when the fabro CLI is on PATH)
# ---------------------------------------------------------------------------

requires_fabro = pytest.mark.skipif(
    shutil.which("fabro") is None, reason="fabro CLI not installed"
)


def _fabro_validate(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["fabro", "validate", str(path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


@requires_fabro
def test_sdlc_workflow_passes_fabro_validate(tmp_path: Path) -> None:
    path = tmp_path / "sdlc.fabro"
    path.write_text(convert_sdlc_to_fabro_dot("ISSUE-42", "Add auth"), encoding="utf-8")
    result = _fabro_validate(path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "warning:" not in result.stdout + result.stderr


@requires_fabro
def test_requirements_workflow_passes_fabro_validate(tmp_path: Path) -> None:
    data = json.loads(
        (Path(__file__).resolve().parents[2] / "metamodel-flow" / "model" / "process_graph.json")
        .read_text(encoding="utf-8")
    )
    path = tmp_path / "req.fabro"
    path.write_text(
        fabro_to_dot(process_graph_to_fabro(data, workflow_filter="requirements_engineering")),
        encoding="utf-8",
    )
    result = _fabro_validate(path)
    assert result.returncode == 0, result.stdout + result.stderr
