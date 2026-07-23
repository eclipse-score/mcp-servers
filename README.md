# Eclipse S-CORE MCP Servers

This repository is the home of the Agent Context Attention Layer for Eclipse
S-CORE. It is a Python/uv monorepo with three intentionally separate areas:

- `packages/score-context` is the MCP-free engine library. Phase 0 defines the
  typed context graph schema and normalized `ContextDelta` data model.
- `servers/` contains MCP server implementations. They are added in later
  phases; the placeholder currently documents the planned context server.
- `apm-packages/` contains authored APM packages and generated, task-scoped
  context bundles. Generated bundles must remain distinct from authored
  packages.

Phase 0 deliberately contains no adapters, graph composition, ranking, APM
generation, or MCP server logic. Future adapters will emit `ContextDelta`
instances, which are vendor-neutral and serialize cleanly as JSON/JSON-LD.

## Development

```shell
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```
Repository for MCP servers
