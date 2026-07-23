# Phase 1 harness

The harness wraps one stable seam:

```text
AssuranceHarness.get_context(task_spec) -> str
```

`BaselineHarness` returns no context. `ContextHarness` composes the committed
graph fragment and calls the MCP-free attention engine. Lane A is a
deterministic natural-key gate: every `expected_node_ids` value must appear in
the rendered candidate context.

Run the adapter from the repository root:

```shell
uv run python -m score_context.harness harness/spec/request_run.json
```

The adapter implements the pinned `validate`, `run`, and `report` envelope and
writes issue-scoped results below `.stage/ISSUE-<n>/`.
