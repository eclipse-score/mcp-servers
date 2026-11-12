<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# Generate Fabro Workflow

## When to Use

When a user wants to execute the SDLC lifecycle as a Fabro workflow, or
when converting between Graphify code graphs and Fabro `.fabro` files.

## SDLC Workflow Generation

1. Call `generate_sdlc_workflow` with the `issue_id` and optional
   `requirement` text. The tool returns a complete Fabro DOT string.
2. Save the DOT string to a `.fabro` file in the repository (e.g.
   `workflows/ISSUE-42.fabro`).
3. The workflow encodes the full SDLC pipeline: bootstrap → fill drafts →
   assess (gate) → implement → record evidence → assess progress →
   check completeness → human review.
4. Run with `fabro run workflows/ISSUE-42.fabro`.

## Code Graph → Fabro Conversion

1. Call `graphify_to_fabro_workflow` with the path to a `graph.json` file.
2. Each code element (module, class, function) becomes an analysis node.
3. The resulting workflow can be executed in Fabro to systematically
   analyze the codebase structure.

## Fabro → Code Graph Conversion

1. Call `fabro_to_graphify_graph` with the DOT text of a `.fabro` file.
2. The result is a Graphify `graph.json` structure that can be queried
   with `query_graph`.
3. Useful for importing external Fabro workflows into the code graph for
   traceability and impact analysis.

## Notes

- The MCP tools return DOT text and graph JSON. They do not write files
  or invoke Fabro directly.
- The SDLC workflow includes goal gates on the assess and completeness
  checks — Fabro will fail the workflow if those stages do not succeed.
- The human review gate pauses for approval before completing.
