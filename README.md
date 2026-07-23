# Eclipse S-CORE Agent Context Attention Layer

This is a Python/uv monorepo using Microsoft's APM
**monorepo-hybrid** shape:

- `libs/score-context` is the shared, MCP-free Python engine and Phase 0 schema.
- `packages/context` is the attention layer's APM package.
- `packages/_template` is a copy-to-add-a-package skeleton.
- The root `apm.yml` is the marketplace manifest and points to local packages.

APM primitives live under each package's `.apm/<type>/` tree. To add a package,
copy `packages/_template`, edit its `apm.yml`, and add primitives under
`.apm/<type>/`.

MCP servers are declared in a package's `apm.yml` under
`dependencies.mcp:`; they are not a separate directory. The `get_context` MCP
server is planned for a later phase.

Phase 0 contains no adapters, graph composition, ranking, APM generation, or
MCP server implementation.

```shell
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```
