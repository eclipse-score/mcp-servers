# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
"""Convert between Graphify code graphs and Fabro workflow DOT files.

Graphify produces ``graph.json`` with nodes (code symbols) and edges
(relationships between them).  Graphviz DOT is the standard format for
describing directed graphs.  Fabro uses a subset of DOT with extensions
for agent orchestration (nodes with ``prompt``, ``script``, ``type``,
``model``, ``timeout``, edge ``condition``, etc.).

This module provides bidirectional conversion:

* **Graphify → Fabro**: Convert a code graph into a Fabro workflow where
  code-analysis tasks become agent/command nodes.
* **Fabro → Graphify**: Convert a Fabro workflow back into a code graph
  representation suitable for graphify's ``graph.json`` format.
* **SDLC → Fabro**: Generate a Fabro ``.fabro`` workflow from the SDLC
  harness stage definitions in ``sdlc-lifecycle-stages``.

The DOT parser handles the Fabro dialect: ``digraph`` only, subgraphs,
chained edges (``A -> B -> C``), ``graph/node/edge`` defaults, ``//``
and ``/* */`` comments, and all Fabro-specific attributes.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Data model for a Graphify graph.json
# ---------------------------------------------------------------------------


@dataclass
class GraphifyNode:
    """A single node from a Graphify code graph."""

    id: str
    name: str
    kind: str  # e.g. "function", "class", "module"
    path: str = ""
    line: int = 0
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphifyEdge:
    """A single edge from a Graphify code graph."""

    source: str
    target: str
    kind: str  # e.g. "calls", "inherits", "imports"
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphifyGraph:
    """A complete Graphify code graph."""

    nodes: list[GraphifyNode] = field(default_factory=list)
    edges: list[GraphifyEdge] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> GraphifyGraph:
        """Load a Graphify graph from a ``graph.json`` file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphifyGraph:
        """Build a GraphifyGraph from a parsed JSON dict."""
        return cls(
            nodes=[GraphifyNode(**n) for n in data.get("nodes", [])],
            edges=[GraphifyEdge(**e) for e in data.get("edges", [])],
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the graphify graph.json format."""
        return {
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [asdict(e) for e in self.edges],
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Data model for a Fabro workflow
# ---------------------------------------------------------------------------

# Fabro shape → handler type mapping (from Fabro docs).
FABRO_SHAPE_HANDLER: dict[str, str] = {
    "Mdiamond": "start",
    "Msquare": "exit",
    "box": "agent",
    "tab": "prompt",
    "parallelogram": "command",
    "hexagon": "human",
    "diamond": "conditional",
    "component": "parallel",
    "tripleoctagon": "parallel.fan_in",
    "insulator": "wait",
    "house": "stack.manager_loop",
}

# Reverse: handler → canonical shape.
FABRO_HANDLER_SHAPE: dict[str, str] = {v: k for k, v in FABRO_SHAPE_HANDLER.items()}

# Handler → Graphify kind for round-tripping.
HANDLER_TO_GRAPHIFY_KIND: dict[str, str] = {
    "start": "entry_point",
    "exit": "exit_point",
    "agent": "component",
    "prompt": "analysis",
    "command": "command",
    "human": "decision",
    "conditional": "conditional",
    "parallel": "module",
    "parallel.fan_in": "parallel",
    "wait": "wait",
    "stack.manager_loop": "workflow",
}


@dataclass
class FabroNode:
    """A single node in a Fabro workflow."""

    id: str
    label: str = ""
    shape: str = ""
    type: str = ""
    prompt: str = ""
    script: str = ""
    model: str = ""
    timeout: str = ""
    max_retries: int = 0
    on_failure: str = ""
    fidelity: str = ""
    thread_id: str = ""
    goal_gate: bool = False
    max_visits: int = 0
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def handler(self) -> str:
        """Resolve the effective Fabro handler type."""
        if self.type:
            return self.type
        if self.shape in FABRO_SHAPE_HANDLER:
            return FABRO_SHAPE_HANDLER[self.shape]
        if self.script and not self.shape:
            return "command"
        return "agent"


@dataclass
class FabroEdge:
    """A single edge in a Fabro workflow."""

    source: str
    target: str
    label: str = ""
    condition: str = ""
    weight: int = 0
    fidelity: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class FabroWorkflow:
    """A complete Fabro workflow (digraph)."""

    name: str
    nodes: list[FabroNode] = field(default_factory=list)
    edges: list[FabroEdge] = field(default_factory=list)
    graph_attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}

    @property
    def edge_pairs(self) -> list[tuple[str, str]]:
        return [(e.source, e.target) for e in self.edges]


# ---------------------------------------------------------------------------
# Graphify → Fabro conversion
# ---------------------------------------------------------------------------


def graphify_to_fabro(
    graph: GraphifyGraph,
    workflow_name: str = "CodeAnalysis",
    root_path: str = "",
) -> FabroWorkflow:
    """Convert a Graphify code graph into a Fabro workflow.

    The conversion maps each Graphify node to a Fabro node whose handler
    type is chosen by the node's ``kind``:

    - ``module``, ``class`` → ``agent`` (box) — multi-turn analysis
    - ``function``, ``variable``, ``import`` → ``prompt`` (tab) — single LLM call
    - other → ``agent`` (box)

    A ``start`` and ``exit`` node bracket the workflow.  Graphify edges
    become Fabro edges with their ``kind`` as the label.
    """
    nodes: list[FabroNode] = []
    edges: list[FabroEdge] = []

    nodes.append(
        FabroNode(
            id="start",
            label="Start",
            shape="Mdiamond",
        )
    )

    node_id_map: dict[str, str] = {}
    for gn in graph.nodes:
        fid = _safe_id(gn.id)
        node_id_map[gn.id] = fid
        is_structural = gn.kind in ("module", "class")
        nodes.append(
            FabroNode(
                id=fid,
                label=gn.name,
                shape="box" if is_structural else "tab",
                prompt=_build_node_prompt(gn, graph),
                model=graph.metadata.get("model", ""),
            )
        )

    for ge in graph.edges:
        src = node_id_map.get(ge.source)
        tgt = node_id_map.get(ge.target)
        if src and tgt:
            edges.append(
                FabroEdge(
                    source=src,
                    target=tgt,
                    label=ge.kind.capitalize(),
                )
            )

    # Wire start → first node(s) and last node(s) → exit.
    fabro_ids = [n.id for n in nodes if n.id != "start"]
    targets_of = {e.target for e in edges}
    sources_of = {e.source for e in edges}
    entry_ids = [nid for nid in fabro_ids if nid not in targets_of]
    exit_ids = [nid for nid in fabro_ids if nid not in sources_of]

    for eid in entry_ids:
        edges.append(FabroEdge(source="start", target=eid, label="Explore"))
    nodes.append(FabroNode(id="exit", label="Exit", shape="Msquare"))
    for xid in exit_ids:
        edges.append(FabroEdge(source=xid, target="exit", label="Complete"))

    return FabroWorkflow(
        name=workflow_name,
        nodes=nodes,
        edges=edges,
        graph_attributes={
            "goal": graph.metadata.get(
                "goal",
                f"Analyze code structure of {root_path or 'the repository'}",
            ),
            "rankdir": "LR",
        },
    )


def _build_node_prompt(node: GraphifyNode, graph: GraphifyGraph) -> str:
    """Build a Fabro prompt describing a single graphify node."""
    lines: list[str] = [f"Analyze the {node.kind} **{node.name}**."]
    if node.path:
        lines.append(
            f"File: `{node.path}`" + (f" line {node.line}" if node.line else "")
        )

    incoming = [e for e in graph.edges if e.target == node.id]
    outgoing = [e for e in graph.edges if e.source == node.id]

    if incoming:
        items = ", ".join(f"{e.kind}←{e.source}" for e in incoming[:8])
        lines.append(f"Incoming: {items}")
    if outgoing:
        items = ", ".join(f"{e.kind}→{e.target}" for e in outgoing[:8])
        lines.append(f"Outgoing: {items}")

    return "\\n".join(lines)


# ---------------------------------------------------------------------------
# Fabro → Graphify conversion
# ---------------------------------------------------------------------------


def fabro_to_graphify(workflow: FabroWorkflow) -> GraphifyGraph:
    """Convert a Fabro workflow into a Graphify code graph.

    Each Fabro node becomes a Graphify node.  The handler type (resolved
    from ``type`` or ``shape``) maps to the Graphify ``kind``.  Fabro-
    specific attributes (``prompt``, ``script``, ``model``, …) are stored
    in ``properties`` so a round-trip back to Fabro can restore them.
    """
    nodes: list[GraphifyNode] = []
    edges: list[GraphifyEdge] = []

    for fn in workflow.nodes:
        kind = HANDLER_TO_GRAPHIFY_KIND.get(fn.handler, "other")
        props: dict[str, Any] = {}
        if fn.prompt:
            props["prompt"] = fn.prompt
        if fn.script:
            props["script"] = fn.script
        if fn.model:
            props["model"] = fn.model
        if fn.timeout:
            props["timeout"] = fn.timeout
        if fn.max_retries:
            props["max_retries"] = fn.max_retries
        if fn.on_failure:
            props["on_failure"] = fn.on_failure
        if fn.fidelity:
            props["fidelity"] = fn.fidelity
        if fn.thread_id:
            props["thread_id"] = fn.thread_id
        if fn.goal_gate:
            props["goal_gate"] = True
        if fn.max_visits:
            props["max_visits"] = fn.max_visits
        props.update(fn.attributes)

        nodes.append(
            GraphifyNode(
                id=fn.id,
                name=fn.label or fn.id,
                kind=kind,
                properties=props,
            )
        )

    for fe in workflow.edges:
        props: dict[str, Any] = {}
        if fe.label:
            props["label"] = fe.label
        if fe.condition:
            props["condition"] = fe.condition
        if fe.weight:
            props["weight"] = fe.weight
        if fe.fidelity:
            props["fidelity"] = fe.fidelity
        props.update(fe.attributes)

        edges.append(
            GraphifyEdge(
                source=fe.source,
                target=fe.target,
                kind=fe.label or "references",
                properties=props,
            )
        )

    return GraphifyGraph(
        nodes=nodes,
        edges=edges,
        metadata={
            "workflow_name": workflow.name,
            **workflow.graph_attributes,
        },
    )


# ---------------------------------------------------------------------------
# SDLC → Fabro workflow generation
# ---------------------------------------------------------------------------


def sdlc_to_fabro(
    issue_id: str,
    requirement: str = "",
    *,
    model: str = "",
    stage_dir: str = ".stage",
) -> FabroWorkflow:
    """Generate a Fabro workflow from the SDLC lifecycle stages.

    This creates an executable ``.fabro`` workflow that encodes the full
    SDLC pipeline defined in ``sdlc-lifecycle-stages.instructions.md``:

    1. bootstrap_sdlc_issue
    2. Fill draft artifacts with evidence
    3. assess_sdlc_issue (gate: all findings resolved)
    4. Implement changes
    5. record_implementation_evidence
    6. assess_implementation_progress
    7. check_stage_completeness

    The workflow includes a human review gate and a loopback loop for
    specification gaps discovered during implementation.
    """
    goal = f"Complete SDLC lifecycle for {issue_id}" + (
        f": {requirement}" if requirement else ""
    )
    model_line = f"model: {model};" if model else ""

    nodes: list[FabroNode] = [
        FabroNode(id="start", label="Start", shape="Mdiamond"),
        # Step 1: Bootstrap
        FabroNode(
            id="bootstrap",
            label="Bootstrap Issue",
            shape="box",
            prompt=(
                f"Check if `{stage_dir}/{issue_id}/` exists. "
                f"If not, call bootstrap_sdlc_issue with issue_id={issue_id}"
                + (f', requirement="{requirement}"' if requirement else "")
                + ". If the directory exists, resume work there."
            ),
        ),
        # Step 2: Fill drafts with evidence
        FabroNode(
            id="fill_drafts",
            label="Fill Draft Artifacts",
            shape="box",
            prompt=(
                f"Inspect the repository using query_graph and resolve_requirements. "
                f"Replace every [DRAFT] section in {stage_dir}/{issue_id}/ with "
                f"evidence-based content. Fill 02-specification.md, "
                f"03-architecture.md, 04-plan.yaml, and 05-tasks/."
            ),
            fidelity="full",
            thread_id="sdlc",
            max_visits=5,
        ),
        # Step 3: Assess (gate)
        FabroNode(
            id="assess",
            label="Assess Issue",
            shape="box",
            prompt=(
                f"Call assess_sdlc_issue for {issue_id}. "
                f"Check for unresolved [DRAFT] markers, missing dependency "
                f"analysis, and missing repository evidence sections."
            ),
            goal_gate=True,
            max_visits=5,
            attributes={"retry_target": "fill_drafts"},
        ),
        # Assessment gate
        FabroNode(
            id="assess_gate",
            label="All findings resolved?",
            shape="diamond",
            max_visits=5,
        ),
        # Step 4: Implement
        FabroNode(
            id="implement",
            label="Implement Changes",
            shape="box",
            prompt=(
                f"Read the plan in {stage_dir}/{issue_id}/04-plan.yaml and tasks "
                f"in 05-tasks/. Implement each task in order. Run tests after each "
                f"change. If implementation reveals a specification gap, stop and "
                f"record a loopback."
            ),
            fidelity="full",
            thread_id="sdlc",
            max_visits=5,
        ),
        # Loopback detection
        FabroNode(
            id="loopback_gate",
            label="Specification gap?",
            shape="diamond",
            max_visits=5,
        ),
        FabroNode(
            id="record_loopback",
            label="Record Loopback",
            shape="box",
            prompt=(
                f"Call record_loopback for {issue_id} with the trigger, "
                f"the earliest invalidated stage, and the affected artifact. "
                f"Update the artifact, then return to draft filling."
            ),
        ),
        # Step 5: Record evidence
        FabroNode(
            id="record_evidence",
            label="Record Evidence",
            shape="box",
            prompt=(
                "For each completed task, call record_implementation_evidence "
                "with the task filename, requirement IDs, changed source files, "
                "test commands, test statuses, and task status. "
                "Do not mark tasks as completed if tests fail."
            ),
        ),
        # Step 6: Assess progress
        FabroNode(
            id="assess_progress",
            label="Assess Progress",
            shape="box",
            prompt=(
                f"Call assess_implementation_progress for {issue_id}. "
                f"Call write_progress_report to publish an RST report."
            ),
        ),
        # Step 7: Check completeness
        FabroNode(
            id="check_complete",
            label="Check Completeness",
            shape="box",
            prompt=(
                f"Call check_stage_completeness for {issue_id} at the "
                f"'review' stage. Verify all prerequisites are met."
            ),
            goal_gate=True,
            attributes={"retry_target": "implement"},
        ),
        # Human review gate
        FabroNode(
            id="review_gate",
            label="Review",
            shape="hexagon",
        ),
        FabroNode(id="exit", label="Exit", shape="Msquare"),
    ]

    edges: list[FabroEdge] = [
        FabroEdge(source="start", target="bootstrap"),
        FabroEdge(source="bootstrap", target="fill_drafts"),
        FabroEdge(source="fill_drafts", target="assess"),
        FabroEdge(source="assess", target="assess_gate"),
        FabroEdge(
            source="assess_gate",
            target="implement",
            label="Pass",
            condition="outcome=succeeded",
        ),
        FabroEdge(
            source="assess_gate",
            target="fill_drafts",
            label="Fix drafts",
        ),
        FabroEdge(source="implement", target="loopback_gate"),
        FabroEdge(
            source="loopback_gate",
            target="record_loopback",
            label="Gap found",
            condition="context.loopback_needed=true",
        ),
        FabroEdge(
            source="loopback_gate",
            target="record_evidence",
            label="No gap",
        ),
        FabroEdge(source="record_loopback", target="fill_drafts"),
        FabroEdge(source="record_evidence", target="assess_progress"),
        FabroEdge(source="assess_progress", target="check_complete"),
        FabroEdge(source="check_complete", target="review_gate"),
        FabroEdge(
            source="review_gate",
            target="exit",
            label="[A] Approve",
        ),
        FabroEdge(
            source="review_gate",
            target="implement",
            label="[R] Revise",
        ),
    ]

    graph_attrs: dict[str, Any] = {
        "goal": goal,
        "rankdir": "TB",
        "max_node_visits": 5,
    }
    if model:
        graph_attrs["model_stylesheet"] = f"* {{ {model_line} }}"

    return FabroWorkflow(
        name=f"SDLC_{_safe_id(issue_id)}",
        nodes=nodes,
        edges=edges,
        graph_attributes=graph_attrs,
    )


# ---------------------------------------------------------------------------
# Process graph → Fabro workflow conversion
# ---------------------------------------------------------------------------

# ISO 26262 / ASPICE process domains derived from Sphinx-Needs tags.
_PROCESS_DOMAINS: dict[str, str] = {
    "requirements_engineering": "Requirements",
    "architecture_design": "Architecture",
    "implementation": "Implementation",
    "verification": "Verification",
    "safety_analysis": "Safety Analysis",
    "safety_management": "Safety Management",
    "security_analysis": "Security Analysis",
    "security_management": "Security Management",
    "change_management": "Change Management",
    "problem_resolution": "Problem Resolution",
    "quality_management": "Quality Management",
    "process_management": "Process Management",
    "release_management": "Release Management",
    "platform_management": "Platform Management",
    "tool_management": "Tool Management",
}


def process_graph_to_graphify(data: dict[str, Any]) -> GraphifyGraph:
    """Adapt a S-CORE process_graph.json to the GraphifyGraph schema.

    The S-CORE process graph (exported from ``eclipse-score/process_description``
    via Sphinx-Needs) uses ``id/type/title/attributes`` for nodes and
    ``source/relation/target`` for edges.  This function maps them to the
    Graphify ``id/name/kind/properties`` and ``source/target/kind``
    conventions so that downstream graph queries work unchanged.
    """
    nodes = [
        GraphifyNode(
            id=n["id"],
            name=n.get("title", n["id"]),
            kind=n.get("type", "other"),
            properties=n.get("attributes", {}),
        )
        for n in data.get("nodes", [])
    ]
    edges = [
        GraphifyEdge(
            source=e["source"],
            target=e["target"],
            kind=e.get("relation", "references"),
        )
        for e in data.get("edges", [])
    ]
    source = data.get("source", {})
    return GraphifyGraph(
        nodes=nodes,
        edges=edges,
        metadata={
            "schema_version": data.get("schema_version"),
            "source_repo": source.get("repo", ""),
            "source_commit": source.get("commit", ""),
            "source_digest": source.get("digest", ""),
        },
    )


def process_graph_to_fabro(
    data: dict[str, Any],
    *,
    workflow_filter: str = "",
) -> FabroWorkflow:
    """Convert a S-CORE ISO 26262 process graph into a Fabro workflow.

    The process graph is an export of ``eclipse-score/process_description``
    built with Sphinx-Needs.  It encodes ISO 26262 / ASPICE process
    activities, their work products, responsible roles, guidance documents,
    and compliance links to standard requirements.

    Conversion strategy
    -------------------

    **Workflow nodes** (Sphinx-Needs type ``workflow``) become Fabro agent
    nodes.  Each prompt lists the activity's input/output work products,
    applicable guidelines/templates/checklists, and responsible roles.

    **Workproduct-based sequencing**: If workflow A *outputs* a work
    product that workflow B *inputs*, a Fabro edge A → B is created with
    the work product name as label.  This reconstructs the V-model data
    flow that Sphinx-Needs encodes as separate ``input``/``output`` link
    types.

    **Role-based approval gates**: Workflows with an ``approved_by`` role
    get a Fabro human gate (``hexagon``) inserted after the agent node.
    The gate pauses for the approver (e.g. Safety Manager, Project Lead).

    **Compliance context**: ``satisfies`` edges from ``gd_req`` (guidance
    requirements) and ``complies`` edges to ``std_req`` (standard
    requirements like ASPICE SWE-2-BP4 or ISO 26262 clauses) are
    summarized in each workflow node's prompt so the agent knows what
    the activity must achieve.

    **Domain grouping**: Workflows are tagged by ISO 26262 process
    domain (e.g. ``requirements_engineering``, ``safety_analysis``).
    The workflow name and goal reflect the selected domain when a
    filter is applied.

    Parameters
    ----------
    data:
        Parsed ``process_graph.json`` content.
    workflow_filter:
        Optional domain tag filter (e.g. ``"requirements_engineering"``
        or ID prefix like ``"req"``) to include only workflows from
        that domain.  Empty string includes all 79 workflows.
    """
    node_map: dict[str, dict[str, Any]] = {n["id"]: n for n in data.get("nodes", [])}
    all_wf_nodes = [n for n in data["nodes"] if n["type"] == "workflow"]

    # Apply filter by tag domain or by ID prefix.
    if workflow_filter:
        wf_nodes = [
            n
            for n in all_wf_nodes
            if (
                workflow_filter in n.get("attributes", {}).get("tags", "")
                or n["id"].split("__", 1)[-1].startswith(workflow_filter)
            )
        ]
    else:
        wf_nodes = all_wf_nodes

    wf_ids = {n["id"] for n in wf_nodes}

    # Collect relationship maps.
    wf_roles: dict[str, dict[str, set[str]]] = {}
    wf_inputs: dict[str, set[str]] = {}
    wf_outputs: dict[str, set[str]] = {}
    wf_contains: dict[str, set[str]] = {}
    wf_satisfied_by: dict[str, set[str]] = {}

    for e in data.get("edges", []):
        src, rel, tgt = e["source"], e.get("relation", ""), e["target"]

        if src in wf_ids:
            if rel in ("responsible", "approved_by", "supported_by"):
                wf_roles.setdefault(src, {}).setdefault(rel, set()).add(
                    node_map.get(tgt, {}).get("title", tgt)
                )
            elif rel == "input":
                wf_inputs.setdefault(src, set()).add(tgt)
            elif rel == "output":
                wf_outputs.setdefault(src, set()).add(tgt)
            elif rel == "contains":
                wf_contains.setdefault(src, set()).add(tgt)

        if tgt in wf_ids and rel == "satisfies":
            wf_satisfied_by.setdefault(tgt, set()).add(src)

    # Build compliance summary per workflow.
    wf_complies: dict[str, set[str]] = {}
    for wf_id in wf_ids:
        gd_reqs = wf_satisfied_by.get(wf_id, set())
        std_set: set[str] = set()
        for gd_id in gd_reqs:
            for e in data.get("edges", []):
                if e["source"] == gd_id and e.get("relation") == "complies":
                    std = node_map.get(e["target"], {})
                    if std.get("type") in ("std_req", "std_wp"):
                        std_set.add(std.get("title", e["target"]))
        if std_set:
            wf_complies[wf_id] = std_set

    # Derive sequencing via shared workproducts.
    seq_edges: list[tuple[str, str, list[str]]] = []
    for wf_a, outputs_a in wf_outputs.items():
        if wf_a not in wf_ids:
            continue
        for wf_b, inputs_b in wf_inputs.items():
            if wf_b not in wf_ids or wf_a == wf_b:
                continue
            shared = outputs_a & inputs_b
            if shared:
                wp_names = [
                    node_map[wp]["title"] for wp in sorted(shared)[:4] if wp in node_map
                ]
                seq_edges.append((wf_a, wf_b, wp_names))

    # --- Build Fabro nodes ---
    fabro_nodes: list[FabroNode] = [
        FabroNode(id="start", label="Start", shape="Mdiamond"),
    ]
    approval_gates: dict[str, str] = {}

    for wf in wf_nodes:
        fid = _safe_id(wf["id"])
        roles = wf_roles.get(wf["id"], {})
        inputs = wf_inputs.get(wf["id"], set())
        outputs = wf_outputs.get(wf["id"], set())
        contains = wf_contains.get(wf["id"], set())
        compliance = wf_complies.get(wf["id"], set())

        prompt_parts: list[str] = [
            f"Execute the ISO 26262 process activity: {wf['title']}.",
        ]
        if inputs:
            names = sorted(node_map[i]["title"] for i in inputs if i in node_map)
            prompt_parts.append(f"Input work products: {', '.join(names[:10])}")
        if outputs:
            names = sorted(node_map[o]["title"] for o in outputs if o in node_map)
            prompt_parts.append(f"Output work products: {', '.join(names[:10])}")
        if contains:
            guidl = sorted(
                node_map[c]["title"]
                for c in contains
                if c in node_map and node_map[c]["type"] == "gd_guidl"
            )
            temps = sorted(
                node_map[c]["title"]
                for c in contains
                if c in node_map and node_map[c]["type"] == "gd_temp"
            )
            chklst = sorted(
                node_map[c]["title"]
                for c in contains
                if c in node_map and node_map[c]["type"] == "gd_chklst"
            )
            if guidl:
                prompt_parts.append(f"Guidelines: {', '.join(guidl[:6])}")
            if temps:
                prompt_parts.append(f"Templates: {', '.join(temps[:6])}")
            if chklst:
                prompt_parts.append(f"Checklists: {', '.join(chklst[:6])}")
        if roles.get("responsible"):
            prompt_parts.append(
                f"Responsible: {', '.join(sorted(roles['responsible']))}"
            )
        if roles.get("supported_by"):
            prompt_parts.append(
                f"Supported by: {', '.join(sorted(roles['supported_by']))}"
            )
        if compliance:
            std_sample = sorted(compliance)[:6]
            prompt_parts.append(f"Complies with: {', '.join(std_sample)}")

        fabro_nodes.append(
            FabroNode(
                id=fid,
                label=wf["title"][:50],
                shape="box",
                prompt="\\n".join(prompt_parts),
            )
        )

        approvers = roles.get("approved_by", set())
        if approvers:
            gate_id = f"{fid}__approve"
            approval_gates[wf["id"]] = gate_id
            fabro_nodes.append(
                FabroNode(
                    id=gate_id,
                    label=f"Approve: {wf['title'][:30]}",
                    shape="hexagon",
                )
            )

    fabro_nodes.append(
        FabroNode(
            id="select_activity",
            label="Select process activity",
            shape="hexagon",
        )
    )
    fabro_nodes.append(FabroNode(id="exit", label="Exit", shape="Msquare"))

    # --- Build Fabro edges ---
    fabro_edges: list[FabroEdge] = []
    all_ids = {n.id for n in fabro_nodes}

    def _out_id(wf_id: str) -> str:
        gate = approval_gates.get(wf_id)
        return gate if gate and gate in all_ids else _safe_id(wf_id)

    for wf_id, gate_id in approval_gates.items():
        fid = _safe_id(wf_id)
        approvers = wf_roles.get(wf_id, {}).get("approved_by", set())
        fabro_edges.append(FabroEdge(source=fid, target=gate_id))
        fabro_edges.append(
            FabroEdge(
                source=gate_id,
                target=fid,
                label=f"[R] Revise ({', '.join(sorted(approvers)[:2])})",
            )
        )

    for wf_a, wf_b, wp_names in seq_edges:
        src = _out_id(wf_a)
        tgt = _safe_id(wf_b)
        if src in all_ids and tgt in all_ids:
            fabro_edges.append(
                FabroEdge(
                    source=src,
                    target=tgt,
                    label=", ".join(wp_names)[:60],
                )
            )

    fabro_edges.append(FabroEdge(source="start", target="select_activity"))
    for wf in wf_nodes:
        fabro_edges.append(
            FabroEdge(
                source="select_activity",
                target=_safe_id(wf["id"]),
                label=wf["title"][:50],
            )
        )

    all_sources = {e.source for e in fabro_edges}
    for wf in wf_nodes:
        out = _out_id(wf["id"])
        if out not in all_sources:
            fabro_edges.append(FabroEdge(source=out, target="exit"))

    for wf_id, gate_id in approval_gates.items():
        gate_has_seq = any(
            e.source == gate_id and e.target != _safe_id(wf_id) for e in fabro_edges
        )
        if not gate_has_seq:
            fabro_edges.append(
                FabroEdge(
                    source=gate_id,
                    target="exit",
                    label="[A] Approved",
                )
            )

    domain_label = ""
    if workflow_filter and workflow_filter in _PROCESS_DOMAINS:
        domain_label = _PROCESS_DOMAINS[workflow_filter]
    elif workflow_filter:
        domain_label = workflow_filter

    wf_name = (
        f"Process_{_safe_id(domain_label)}" if domain_label else "ProcessWorkflows"
    )
    goal = (
        f"S-CORE ISO 26262 process: {domain_label}"
        if domain_label
        else "S-CORE ISO 26262 process description workflows"
    )

    return FabroWorkflow(
        name=wf_name,
        nodes=fabro_nodes,
        edges=fabro_edges,
        graph_attributes={
            "goal": goal,
            "rankdir": "TB",
            "max_node_visits": 5,
        },
    )


def convert_process_graph_to_fabro_dot(
    graph_path: Path,
    *,
    workflow_filter: str = "",
) -> str:
    """Load a process_graph.json and return a Fabro DOT string."""
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    workflow = process_graph_to_fabro(data, workflow_filter=workflow_filter)
    return fabro_to_dot(workflow)


# ---------------------------------------------------------------------------
# DOT serialization
# ---------------------------------------------------------------------------

# Node attributes that are serialized as bare identifiers (no quotes).
_BARE_ATTRS = {"shape", "rankdir"}

# Node attributes that are booleans.
_BOOL_ATTRS = {"goal_gate"}

# Node attributes that are integers.
_INT_ATTRS = {"max_retries", "max_visits", "weight", "max_parallel"}


def fabro_to_dot(workflow: FabroWorkflow) -> str:
    """Render a Fabro workflow as a Graphviz DOT string.

    Produces a ``digraph`` compatible with both Graphviz and Fabro.
    """
    lines: list[str] = [f"digraph {workflow.name} {{"]

    # Graph attributes as a block.
    if workflow.graph_attributes:
        ga_parts: list[str] = []
        for key, value in workflow.graph_attributes.items():
            if isinstance(value, str):
                ga_parts.append(f'{key}="{_escape_dot(value)}"')
            else:
                ga_parts.append(f"{key}={json.dumps(value)}")
        lines.append(f"    graph [{', '.join(ga_parts)}]")

    lines.append("")

    for node in workflow.nodes:
        attrs = _node_to_dot_attrs(node)
        attr_str = f" [{', '.join(attrs)}]" if attrs else ""
        lines.append(f"    {node.id}{attr_str}")

    if workflow.edges:
        lines.append("")

    for edge in workflow.edges:
        attrs = _edge_to_dot_attrs(edge)
        attr_str = f" [{', '.join(attrs)}]" if attrs else ""
        lines.append(f"    {edge.source} -> {edge.target}{attr_str}")

    lines.append("}")
    return "\n".join(lines)


def _node_to_dot_attrs(node: FabroNode) -> list[str]:
    """Serialize a FabroNode's non-default fields as DOT attribute pairs."""
    attrs: list[str] = []
    if node.label:
        attrs.append(f'label="{_escape_dot(node.label)}"')
    if node.shape:
        attrs.append(f"shape={node.shape}")
    if node.type:
        attrs.append(f'type="{node.type}"')
    if node.prompt:
        attrs.append(f'prompt="{_escape_dot(node.prompt)}"')
    if node.script:
        attrs.append(f'script="{_escape_dot(node.script)}"')
    if node.model:
        attrs.append(f'model="{node.model}"')
    if node.timeout:
        attrs.append(f'timeout="{node.timeout}"')
    if node.max_retries:
        attrs.append(f"max_retries={node.max_retries}")
    if node.on_failure:
        attrs.append(f'on_failure="{node.on_failure}"')
    if node.fidelity:
        attrs.append(f'fidelity="{node.fidelity}"')
    if node.thread_id:
        attrs.append(f'thread_id="{node.thread_id}"')
    if node.goal_gate:
        attrs.append("goal_gate=true")
    if node.max_visits:
        attrs.append(f"max_visits={node.max_visits}")
    for key, value in node.attributes.items():
        if isinstance(value, bool):
            attrs.append(f"{key}={'true' if value else 'false'}")
        elif isinstance(value, int):
            attrs.append(f"{key}={value}")
        elif isinstance(value, str):
            if key in _BARE_ATTRS:
                attrs.append(f"{key}={value}")
            else:
                attrs.append(f'{key}="{_escape_dot(value)}"')
        else:
            attrs.append(f"{key}={json.dumps(value)}")
    return attrs


def _edge_to_dot_attrs(edge: FabroEdge) -> list[str]:
    """Serialize a FabroEdge's non-default fields as DOT attribute pairs."""
    attrs: list[str] = []
    if edge.label:
        attrs.append(f'label="{_escape_dot(edge.label)}"')
    if edge.condition:
        attrs.append(f'condition="{_escape_dot(edge.condition)}"')
    if edge.weight:
        attrs.append(f"weight={edge.weight}")
    if edge.fidelity:
        attrs.append(f'fidelity="{edge.fidelity}"')
    for key, value in edge.attributes.items():
        if isinstance(value, bool):
            attrs.append(f"{key}={'true' if value else 'false'}")
        elif isinstance(value, int):
            attrs.append(f"{key}={value}")
        elif isinstance(value, str):
            attrs.append(f'{key}="{_escape_dot(value)}"')
        else:
            attrs.append(f"{key}={json.dumps(value)}")
    return attrs


# ---------------------------------------------------------------------------
# DOT parsing
# ---------------------------------------------------------------------------


def dot_to_fabro_workflow(dot_text: str) -> FabroWorkflow:
    """Parse a Fabro DOT string into a ``FabroWorkflow``.

    Handles the Fabro DOT dialect:
    - ``digraph Name { … }``
    - ``graph [key="value", …]`` block attributes
    - ``node [defaults]`` and ``edge [defaults]`` (applied to later decls)
    - Node declarations: ``id [attrs]``
    - Edge declarations including chains: ``A -> B -> C [attrs]``
    - ``subgraph cluster_name { … }`` (nodes are collected, nesting tracked)
    - ``//`` line comments and ``/* … */`` block comments
    - Bare ``key=value`` graph attribute statements
    """
    text = _strip_comments(dot_text)
    lines = text.strip().splitlines()

    name_match = re.match(r"^\s*digraph\s+(\w+)\s*\{", lines[0] if lines else "")
    if not name_match:
        raise ValueError("Not a valid Fabro digraph")
    name = name_match.group(1)

    nodes: list[FabroNode] = []
    edges: list[FabroEdge] = []
    graph_attrs: dict[str, Any] = {}
    node_defaults: dict[str, str] = {}
    edge_defaults: dict[str, str] = {}
    seen_node_ids: set[str] = set()

    body = "\n".join(lines[1:])
    # Remove outermost closing brace.
    body = re.sub(r"\}\s*$", "", body)

    for stmt in _split_statements(body):
        stmt = stmt.strip()
        if not stmt:
            continue

        # Skip subgraph open/close (we flatten structure).
        if re.match(r"^(subgraph\s+\w+\s*\{|\})", stmt):
            continue

        # graph [...] block attributes.
        m = re.match(r"^graph\s*\[\s*(.*?)\s*\]$", stmt, re.DOTALL)
        if m:
            graph_attrs.update(_parse_dot_attributes(m.group(1)))
            continue

        # node [...] defaults.
        m = re.match(r"^node\s*\[\s*(.*?)\s*\]$", stmt, re.DOTALL)
        if m:
            node_defaults.update(_parse_dot_attributes(m.group(1)))
            continue

        # edge [...] defaults.
        m = re.match(r"^edge\s*\[\s*(.*?)\s*\]$", stmt, re.DOTALL)
        if m:
            edge_defaults.update(_parse_dot_attributes(m.group(1)))
            continue

        # Edge statement (may be chained: A -> B -> C [attrs]).
        if "->" in stmt:
            parts = re.split(r"\s*->\s*", stmt)
            # The last part may have [attrs] appended.
            edge_attrs_str = ""
            last = parts[-1]
            bracket = _find_top_level_bracket(last)
            if bracket is not None:
                edge_attrs_str = (
                    last[bracket + 1 : -1].strip() if last.endswith("]") else ""
                )
                parts[-1] = last[:bracket].strip()

            parsed_edge_attrs = {
                **edge_defaults,
                **_parse_dot_attributes(edge_attrs_str),
            }
            for i in range(len(parts) - 1):
                src = parts[i].strip()
                tgt = parts[i + 1].strip()
                ea = _attrs_to_fabro_edge(src, tgt, parsed_edge_attrs)
                edges.append(ea)
            continue

        # Node statement: id [attrs] or id.
        m = re.match(r"^(\w+)\s*(?:\[\s*(.*?)\s*\])?\s*$", stmt, re.DOTALL)
        if m:
            node_id = m.group(1)
            # Skip DOT keywords that aren't actually node IDs.
            if node_id in ("graph", "node", "edge", "subgraph", "digraph"):
                # Bare graph attribute: key=value
                if "=" in stmt and node_id == stmt.split("=")[0].strip():
                    pass  # handled below
                continue
            attr_str = m.group(2) or ""
            merged = {**node_defaults, **_parse_dot_attributes(attr_str)}
            fn = _attrs_to_fabro_node(node_id, merged)
            if node_id not in seen_node_ids:
                nodes.append(fn)
                seen_node_ids.add(node_id)
            continue

        # Bare key=value graph attribute.
        if "=" in stmt and "->" not in stmt and "[" not in stmt:
            key, _, value = stmt.partition("=")
            graph_attrs[key.strip()] = _unquote(value.strip())

    return FabroWorkflow(
        name=name,
        nodes=nodes,
        edges=edges,
        graph_attributes=graph_attrs,
    )


# ---------------------------------------------------------------------------
# DOT parsing helpers
# ---------------------------------------------------------------------------


def _strip_comments(text: str) -> str:
    """Remove ``//`` line comments and ``/* … */`` block comments."""
    # Block comments first.
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Line comments.
    text = re.sub(r"//[^\n]*", "", text)
    # Hash comments.
    text = re.sub(r"#[^\n]*", "", text)
    return text


def _split_statements(body: str) -> list[str]:
    """Split a DOT body into individual statements.

    Statements are separated by ``;`` or newlines, but we must not split
    inside quoted strings or ``[…]`` attribute blocks.
    """
    stmts: list[str] = []
    current: list[str] = []
    in_quotes = False
    bracket_depth = 0
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == '"' and (i == 0 or body[i - 1] != "\\"):
            in_quotes = not in_quotes
            current.append(ch)
        elif not in_quotes and ch == "[":
            bracket_depth += 1
            current.append(ch)
        elif not in_quotes and ch == "]":
            bracket_depth = max(0, bracket_depth - 1)
            current.append(ch)
        elif not in_quotes and bracket_depth == 0 and ch in (";\n"):
            s = "".join(current).strip()
            if s:
                stmts.append(s)
            current = []
        else:
            current.append(ch)
        i += 1
    s = "".join(current).strip()
    if s:
        stmts.append(s)
    return stmts


def _find_top_level_bracket(text: str) -> int | None:
    """Find the index of the first ``[`` that is not inside quotes."""
    in_quotes = False
    for i, ch in enumerate(text):
        if ch == '"' and (i == 0 or text[i - 1] != "\\"):
            in_quotes = not in_quotes
        elif ch == "[" and not in_quotes:
            return i
    return None


def _attrs_to_fabro_node(node_id: str, attrs: dict[str, str]) -> FabroNode:
    """Build a FabroNode from parsed DOT attributes."""
    return FabroNode(
        id=node_id,
        label=attrs.pop("label", ""),
        shape=attrs.pop("shape", ""),
        type=attrs.pop("type", ""),
        prompt=attrs.pop("prompt", ""),
        script=attrs.pop("script", ""),
        model=attrs.pop("model", ""),
        timeout=attrs.pop("timeout", ""),
        max_retries=int(attrs.pop("max_retries", "0")),
        on_failure=attrs.pop("on_failure", ""),
        fidelity=attrs.pop("fidelity", ""),
        thread_id=attrs.pop("thread_id", ""),
        goal_gate=attrs.pop("goal_gate", "false").lower() == "true",
        max_visits=int(attrs.pop("max_visits", "0")),
        attributes=attrs,
    )


def _attrs_to_fabro_edge(source: str, target: str, attrs: dict[str, str]) -> FabroEdge:
    """Build a FabroEdge from parsed DOT attributes."""
    return FabroEdge(
        source=source,
        target=target,
        label=attrs.get("label", ""),
        condition=attrs.get("condition", ""),
        weight=int(attrs.get("weight", "0")),
        fidelity=attrs.get("fidelity", ""),
        attributes={
            k: v
            for k, v in attrs.items()
            if k not in ("label", "condition", "weight", "fidelity")
        },
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _safe_id(raw_id: str) -> str:
    """Convert an arbitrary string to a valid DOT/Fabro node identifier."""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", raw_id)
    if safe and not safe[0].isalpha() and safe[0] != "_":
        safe = "n_" + safe
    return safe if safe else "unnamed"


def _escape_dot(text: str) -> str:
    """Escape a string for inclusion in a DOT quoted attribute value."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _unquote(value: str) -> str:
    """Remove surrounding double quotes if present."""
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return value


def _parse_dot_attributes(attr_str: str) -> dict[str, str]:
    """Parse a DOT attribute string like ``key="value", key2=value2``.

    Handles:
    - Quoted values with escaped quotes: ``prompt="He said \\"hi\\""``
    - Bare values: ``shape=box``, ``max_retries=3``, ``goal_gate=true``
    - Comma and semicolon separators
    """
    attrs: dict[str, str] = {}
    if not attr_str or not attr_str.strip():
        return attrs

    i = 0
    n = len(attr_str)
    while i < n:
        # Skip whitespace and separators.
        while i < n and attr_str[i] in (" ", "\t", "\n", "\r", ",", ";"):
            i += 1
        if i >= n:
            break

        # Read key.
        key_start = i
        while i < n and attr_str[i] not in ("=", " ", "\t", ",", ";", "]"):
            i += 1
        key = attr_str[key_start:i].strip()
        if not key:
            break

        # Skip whitespace around '='.
        while i < n and attr_str[i] in (" ", "\t"):
            i += 1
        if i >= n or attr_str[i] != "=":
            # Bare key with no value — skip.
            continue
        i += 1  # skip '='
        while i < n and attr_str[i] in (" ", "\t"):
            i += 1

        # Read value.
        if i < n and attr_str[i] == '"':
            # Quoted value.
            i += 1  # skip opening quote
            val_chars: list[str] = []
            while i < n:
                if attr_str[i] == "\\" and i + 1 < n:
                    next_ch = attr_str[i + 1]
                    if next_ch == '"':
                        val_chars.append('"')
                        i += 2
                    elif next_ch == "\\":
                        val_chars.append("\\")
                        i += 2
                    elif next_ch == "n":
                        val_chars.append("\n")
                        i += 2
                    elif next_ch == "t":
                        val_chars.append("\t")
                        i += 2
                    else:
                        val_chars.append(attr_str[i])
                        i += 1
                elif attr_str[i] == '"':
                    i += 1  # skip closing quote
                    break
                else:
                    val_chars.append(attr_str[i])
                    i += 1
            attrs[key] = "".join(val_chars)
        else:
            # Bare value (identifier, number, boolean).
            val_start = i
            while i < n and attr_str[i] not in (",", ";", " ", "\t", "\n", "]"):
                i += 1
            attrs[key] = attr_str[val_start:i].strip()

    return attrs


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def convert_graphify_to_fabro_dot(
    graph_path: Path,
    workflow_name: str = "CodeAnalysis",
) -> str:
    """Load a Graphify ``graph.json`` and return a Fabro DOT string."""
    graph = GraphifyGraph.from_file(graph_path)
    workflow = graphify_to_fabro(graph, workflow_name)
    return fabro_to_dot(workflow)


def convert_fabro_dot_to_graphify(dot_text: str) -> GraphifyGraph:
    """Parse a Fabro DOT string and return a Graphify graph."""
    workflow = dot_to_fabro_workflow(dot_text)
    return fabro_to_graphify(workflow)


def convert_sdlc_to_fabro_dot(
    issue_id: str,
    requirement: str = "",
    *,
    model: str = "",
    stage_dir: str = ".stage",
) -> str:
    """Generate a Fabro DOT workflow for the SDLC lifecycle."""
    workflow = sdlc_to_fabro(
        issue_id,
        requirement,
        model=model,
        stage_dir=stage_dir,
    )
    return fabro_to_dot(workflow)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """CLI entry point for graphify ↔ fabro conversion."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Convert between Graphify code graphs, Fabro workflows, and SDLC stages."
        )
    )
    sub = parser.add_subparsers(dest="command")

    # graphify → fabro
    p_to_fabro = sub.add_parser(
        "to-fabro", help="Convert graphify graph.json → Fabro DOT"
    )
    p_to_fabro.add_argument("input", help="Path to graph.json")
    p_to_fabro.add_argument("--name", default="CodeAnalysis", help="Workflow name")
    p_to_fabro.add_argument("-o", "--output", help="Output file (default: stdout)")

    # fabro → graphify
    p_to_graph = sub.add_parser(
        "to-graphify", help="Convert Fabro DOT → graphify graph.json"
    )
    p_to_graph.add_argument("input", help="Path to .fabro/.dot file")
    p_to_graph.add_argument("-o", "--output", help="Output file (default: stdout)")

    # sdlc → fabro
    p_sdlc = sub.add_parser("sdlc", help="Generate SDLC lifecycle Fabro workflow")
    p_sdlc.add_argument("issue_id", help="Issue identifier (e.g. ISSUE-42)")
    p_sdlc.add_argument("--requirement", default="", help="Requirement text")
    p_sdlc.add_argument("--model", default="", help="LLM model identifier")
    p_sdlc.add_argument("--stage-dir", default=".stage", help="Stage directory")
    p_sdlc.add_argument("-o", "--output", help="Output file (default: stdout)")

    # process graph → fabro
    p_proc = sub.add_parser(
        "process", help="Convert ISO 26262 process graph → Fabro workflow"
    )
    p_proc.add_argument("input", help="Path to process_graph.json")
    p_proc.add_argument(
        "--filter",
        default="",
        dest="workflow_filter",
        help="Domain tag or ID prefix filter (e.g. requirements_engineering)",
    )
    p_proc.add_argument("-o", "--output", help="Output file (default: stdout)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    if args.command == "to-fabro":
        output = convert_graphify_to_fabro_dot(Path(args.input), args.name)
    elif args.command == "to-graphify":
        text = Path(args.input).read_text(encoding="utf-8")
        graph = convert_fabro_dot_to_graphify(text)
        output = json.dumps(graph.to_dict(), indent=2)
    elif args.command == "sdlc":
        output = convert_sdlc_to_fabro_dot(
            args.issue_id,
            args.requirement,
            model=args.model,
            stage_dir=args.stage_dir,
        )
    elif args.command == "process":
        output = convert_process_graph_to_fabro_dot(
            Path(args.input),
            workflow_filter=args.workflow_filter,
        )
    else:
        parser.print_help()
        return 1

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Written to {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
