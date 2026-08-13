<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# apm-setup

Central setup MCP package for the Eclipse S-CORE APM package tree.

## Tools

- `verify_setup(repo_path)` checks local setup state.
- `setup_graphify(repo_path)` installs Graphify when requested and generates the code graph.
- `setup_context_discipline(repo_path)` creates local working-memory storage.

Setup is explicit and repository-local. Installing or compiling an APM package
does not execute setup commands automatically.

## APM installation

Install this package. This installs the instructions, skill files, and its
self-defined stdio MCP server:

```bash
apm install /path/to/mcp-servers/packages/apm-setup --target copilot
```

For a published package, use the installed package path reported by APM in
place of `apm_modules/_local/apm-setup`.

After installation, call `verify_setup`, then call `setup_graphify` and/or
`setup_context_discipline` with the target repository path. Do not run a
repository setup script; setup is performed by the MCP tools.
