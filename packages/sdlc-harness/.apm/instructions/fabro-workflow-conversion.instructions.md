---
description: "Use when: converting between Graphify code graphs and Fabro workflows, or generating SDLC lifecycle workflows."
applyTo: "**/*.fabro,**/*.dot,**/graph.json"
---

<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# Fabro Workflow Conversion

## Graphify ↔ Fabro Bidirectional Conversion

The sdlc-harness package provides three MCP tools for workflow conversion:

| Tool | Direction | Use Case |
|------|-----------|----------|
| `generate_sdlc_workflow` | SDLC stages → Fabro DOT | Generate a runnable Fabro workflow for an SDLC issue |
| `graphify_to_fabro_workflow` | graph.json → Fabro DOT | Convert code structure into analysis workflow |
| `fabro_to_graphify_graph` | Fabro DOT → graph.json | Import workflow structure for graph queries |

## Fabro DOT Dialect

Fabro workflows are Graphviz `digraph` files with extensions:

- **Node shapes** determine handler types: `box`=agent, `tab`=prompt, `parallelogram`=command, `hexagon`=human gate, `diamond`=conditional, `Mdiamond`=start, `Msquare`=exit
- **Node attributes**: `prompt`, `script`, `model`, `fidelity`, `thread_id`, `goal_gate`, `max_visits`, `timeout`, `max_retries`, `on_failure`
- **Edge attributes**: `condition` (boolean expression), `label`, `weight`, `fidelity`
- **Graph attributes**: `goal`, `rankdir`, `model_stylesheet`, `on_failure`, `default_max_retries`

## SDLC Workflow Structure

The generated SDLC workflow follows the lifecycle defined in `sdlc-lifecycle-stages.instructions.md`:

```
start → bootstrap → fill_drafts → assess → [gate] → implement → [loopback?]
                                      ↑                              ↓
                                      └── record_loopback ←── loopback_gate
                                                                     ↓ (no gap)
                                                            record_evidence
                                                                     ↓
                                                            assess_progress
                                                                     ↓
                                                            check_complete
                                                                     ↓
                                                            review_gate → exit
                                                                ↓ (revise)
                                                            implement
```

- `assess` and `check_complete` are goal gates — the workflow fails if they do not succeed.
- `review_gate` is a human gate with Approve/Revise options.
- The loopback loop returns to `fill_drafts` when implementation reveals specification gaps.
