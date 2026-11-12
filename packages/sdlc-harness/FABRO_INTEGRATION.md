# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

# Fabro Integration Sketch for sdlc-harness

## Status quo

```
sdlc-harness/
├── src/
│   ├── artifact_writer.py          # bootstrap, write_stage_artifact, assess, check_completeness
│   ├── implementation_tracking.py  # record_evidence, assess_progress, write_progress_report
│   ├── loopback.py                 # record_loopback
│   ├── graphify_fabro_conversion.py # NEW: 4 conversion directions, DOT parser
│   └── serve.py                    # MCP stdio server, 12 tools
├── .apm/
│   ├── instructions/
│   │   ├── sdlc-lifecycle-stages.instructions.md    # "call tools in this order"
│   │   ├── loopback-detection.instructions.md
│   │   └── fabro-workflow-conversion.instructions.md # NEW
│   └── skills/
│       ├── bootstrap-sdlc-issue/
│       ├── write-stage-artifact/
│       ├── track-implementation-progress/
│       ├── detect-loopback/
│       └── generate-fabro-workflow/                  # NEW
```

The agent-driven workflow today is **instructions telling the agent what order to
call tools**.  The agent reads `sdlc-lifecycle-stages.instructions.md` and
follows the 7-step checklist.  There is no formal workflow graph — the agent is
trusted to follow the sequence.

The Fabro conversion we just built can **export** that sequence as a `.fabro`
file, and can also convert the ISO 26262 process graph from
`process_description` into Fabro.  But the two worlds are not yet connected:
the `.fabro` files reference tool calls in their prompts, but Fabro doesn't
actually call the MCP tools.

## The integration idea

Fabro has a concept of **ACP backends** (`backend="acp"`) where an agent node
runs an Agent Client Protocol stdio agent.  Our sdlc-harness is already a stdio
MCP server.  The connection point is:

```
Fabro agent node  →  runs with tools  →  MCP server (sdlc-harness)
```

When Fabro runs a workflow, each agent node gets a prompt and access to tools.
If the Fabro runtime is configured with our MCP servers as tool providers, the
prompts in the generated `.fabro` files will naturally call `bootstrap_sdlc_issue`,
`assess_sdlc_issue`, etc.

### What this means for the package

We don't need to change the MCP tools themselves. Instead, we need to:

1. **Make the generated `.fabro` files reference real tool invocations** (they
   already do — the prompts say "call bootstrap_sdlc_issue").
2. **Provide a Fabro run configuration** that wires up our MCP servers.
3. **Connect the process graph to the SDLC lifecycle** so that when a process
   activity (e.g., "Create/Maintain Feature requirements") is executed, the
   SDLC harness tools are used for evidence and artifact tracking.

## Concrete integration points

### A. `.fabro` workflow templates in the package

Add pre-built `.fabro` files to the package:

```
sdlc-harness/
├── workflows/
│   ├── sdlc-lifecycle.fabro          # The 7-step SDLC pipeline
│   ├── process-requirements.fabro     # Requirements engineering domain
│   ├── process-verification.fabro     # Verification domain
│   └── process-full.fabro            # Full ISO 26262 process
```

These are **generated once** from the conversion module and checked in.
They serve as starting points that users can customize.

The `sdlc-lifecycle.fabro` replaces the need for agents to read and follow
`sdlc-lifecycle-stages.instructions.md` — Fabro enforces the sequence.

### B. Connect existing tools as Fabro command nodes

The key insight: several existing tools are **deterministic checks** that map
naturally to Fabro `command` nodes (parallelogram) rather than agent nodes.
This means Fabro itself can run them without an LLM:

| Existing tool | Fabro node type | Why |
|---|---|---|
| `check_stage_completeness` | command | Pure file-presence check, no LLM needed |
| `assess_sdlc_issue` | command | Deterministic [DRAFT] marker detection |
| `assess_implementation_progress` | command | Counts tasks, no reasoning |
| `write_progress_report` | command | Deterministic RST generation |

The MCP call could be scripted in a Fabro command node:

```dot
check [shape=parallelogram, script="echo '{\"issue_id\":\"ISSUE-42\",\"stage\":\"review\"}' | sdlc-harness-cli check-stage-completeness"]
```

Or, better: add a thin CLI wrapper to the package that can invoke individual
tools from the command line, so Fabro command nodes can call them directly.

### C. Process graph → SDLC issue mapping

The process graph workflows map 1:1 to SDLC issues:

| Process activity | SDLC stage | Artifact |
|---|---|---|
| Create/Maintain Feature requirements | requirement + specification | 01-requirement.md, 02-specification.md |
| Create/Maintain Feature architecture | architecture | 03-architecture.md |
| Create/Maintain Implementation | plan + implementation | 04-plan.yaml, 05-tasks/ |
| Verify Implementation | review | harness/implementation-evidence.json |

When `process_graph_to_fabro` generates the Fabro workflow, each workflow
agent node's prompt should reference the **specific SDLC tool calls** for
that stage.  E.g., the architecture workflow node should say:

```
"Call write_stage_artifact with artifact_type='architecture'.
 Then call check_stage_completeness with stage='architecture'."
```

This connects the ISO 26262 process model to the concrete file-based artifacts.

### D. Workproduct → artifact path mapping

Add a mapping from process graph workproduct IDs to `.stage/` paths:

```python
WORKPRODUCT_ARTIFACTS = {
    "wp__feat_req": "01-requirement.md",
    "wp__feat_arch": "03-architecture.md",
    "wp__comp_req": "01-requirement.md",  # component-level
    "wp__comp_arch": "03-architecture.md",
    ...
}
```

This lets the Fabro command nodes validate that the expected output
artifacts actually exist after an agent node completes.

### E. Enhanced `bootstrap_sdlc_issue` with process context

When bootstrapping an SDLC issue, optionally pass a `process_workflow_id`
that links the issue to a specific process graph workflow.  The bootstrap
then populates the drafts with:

- The workflow's input/output workproducts in the specification
- The workflow's guidelines/templates in the architecture
- The workflow's compliance requirements in the plan
- The workflow's responsible/approved_by roles in the review checklist

### F. Evidence binding to process graph (issue #73 step 3)

`record_implementation_evidence` should optionally accept:

```python
def record_implementation_evidence(
    ...,
    baseline_commit: str = "",      # git commit SHA
    source_digests: dict = {},      # file → sha256
    process_workflow_id: str = "",  # links to process graph
)
```

This connects evidence records to exact baselines and the process model.

### G. Change impact via workproduct chains (issue #73 step 4)

The workproduct-based sequencing we already derive in `process_graph_to_fabro`
**is** the change impact graph.  If "Feature Requirements" changes, every
downstream workflow that inputs it is affected.  Add:

```python
def change_impact(
    changed_workproduct_id: str,
    process_graph_path: Path,
) -> list[dict]:
    """Return workflows affected by a workproduct change."""
```

This is the Fabro workflow graph traversal we already have — just expose it
as an MCP tool.

## Implementation plan (ordered by value)

### Phase 1: Wire what we have (low effort, high value)

1. ☐ Add `.fabro` workflow templates to the package (generate + check in)
2. ☐ Add a CLI entry point for individual tool calls (for Fabro command nodes)
3. ☐ Update instructions to reference the `.fabro` workflows as the
     canonical sequence (Fabro enforces, instructions explain)

### Phase 2: Process graph → SDLC artifact mapping (medium effort)

4. ☐ Add `WORKPRODUCT_ARTIFACTS` mapping
5. ☐ Enhance `bootstrap_sdlc_issue` with `process_workflow_id`
6. ☐ Add `change_impact` MCP tool
7. ☐ Add command nodes for deterministic checks in generated workflows

### Phase 3: Full Fabro integration (higher effort)

8. ☐ Subgraph clusters for ISO 26262 domains
9. ☐ model_stylesheet per domain
10. ☐ Parallel fan-out for independent domains
11. ☐ output_schema validation against metamodel-schema.json
12. ☐ Baseline binding in evidence records (issue #73 step 3)

### Phase 4: Runtime integration

13. ☐ Fabro run configuration TOML that wires up MCP servers
14. ☐ End-to-end test: `fabro run sdlc-lifecycle.fabro` drives the full pipeline
15. ☐ Integration with s-core_sw_fabric's Fabro runtime
