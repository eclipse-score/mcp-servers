---
name: query-context
description: Query the deterministic context-attention layer and read selected graph nodes.
---

# Query context

Use the repository harness request envelope with `operation: "run"` and a task
spec containing `seed_node_ids`, `expected_node_ids`, and `top_n`. The
candidate seam is:

```text
AssuranceHarness.get_context(task_spec) -> str
```

Read the generated `.stage/ISSUE-<n>/harness/run.json` artifact. The candidate
section contains the rendered selected nodes and a Lane A gate verdict. The
baseline section is intentionally empty and should fail when expected node IDs
are required. Treat node IDs as stable natural keys and use the graph node
type/title to interpret the selected context.
