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

Install this package first:

```bash
apm install /path/to/mcp-servers/packages/apm-setup --target copilot
```

Register the installed stdio server through APM:

```bash
apm install --mcp apm-setup --target copilot -- \
	python3 apm_modules/_local/apm-setup/src/apm_setup/serve.py
```

For a published package, use the installed package path reported by APM in
place of `apm_modules/_local/apm-setup`.
