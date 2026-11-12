<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# apm-setup

Central setup MCP package for the Eclipse S-CORE APM package tree.

## Tools

- `verify_setup(repo_path)` checks local setup state, including whether the Fabro CLI is on `PATH` and its `--version` output.
- `setup_graphify(repo_path)` installs Graphify when requested and generates the code graph.
- `setup_context_discipline(repo_path)` creates local working-memory storage.
- `setup_fabro(install_fabro=false)` checks the Fabro CLI used to run generated SDLC workflows. With `install_fabro=true` it runs `brew install fabro-sh/tap/fabro-nightly` when Fabro is missing and Homebrew is available. It never pipes a remote install script. The nightly build is unpinned: `s-core_sw_fabric` has not selected a Fabro runtime (its `upstream.lock.yaml` marks Fabro as unresolved).

Setup remains enabled through MCP tools and is keyed by the consumer repository.
Graphs are generated in `$XDG_DATA_HOME/score-agent/<repo>-<path-hash>/`, falling back to `~/.local/share/score-agent/`.
Context storage uses `$XDG_STATE_HOME/score-agent/<repo>-<path-hash>/`, falling back to `~/.local/state/score-agent/`.
Both match their runtime storage paths, and neither setup operation edits consumer `.gitignore` files.
Use the `graph_path` and `local_store` returned by `verify_setup` and setup tools instead of assuming checkout-local paths.
Graph setup delegates to `graphify-codegraph --prepare-only --repo-path <repo>` using the runtime's prebuilt-first policy.
It downloads the matching revision or nightly `main`, keeps the published provenance, and does not immediately overwrite a downloaded graph with local extraction.
Published caches are rechecked daily; registry failures retain a usable cache, and local extraction is the last fallback when no graph exists.
Pass `force_local=true` to `setup_graphify` for an explicit current-checkout rebuild, or use `graphify-codegraph --prepare-only --repo-path <repo> --force-local` directly.
The launcher must support `--prepare-only`; update the pinned launcher release along with this setup package when deploying these changes.
Installing or compiling an APM package does not execute setup commands automatically.

## APM installation

Install this package. This installs the instructions, skill files, and its
self-defined stdio MCP server:

```bash
apm install /path/to/mcp-servers/packages/apm-setup --target copilot
```

The MCP launcher resolves the installed package location under `apm_modules`
at runtime, including APM's hashed local-dependency paths.

To relocate APM-generated outputs with supported CLI versions, use `apm install --root <absolute-cache-dir>` and `apm compile --root <absolute-cache-dir>` with the same repository-keyed root.
Source manifests still resolve from the current directory, and positional installs can edit the source manifest.
For supported harnesses, user-scoped `apm install --global` and `apm compile --global` avoid deploying into the consumer checkout.
Ensure harnesses discover the relocated outputs; an arbitrary cache root alone does not activate instructions or register MCP servers.

After installation, call `verify_setup`, then call `setup_graphify` and/or
`setup_context_discipline` with the target repository path. Do not run a
repository setup script; setup is performed by the MCP tools.

### VS Code Remote troubleshooting

Run the install command inside the remote workspace where the MCP server runs:

```bash
cd /workspaces/your-project
apm install apm-setup@eclipse-score-apm-marketplace --target copilot
```

If VS Code reports that the setup server cannot be found, the MCP
configuration exists but the package files are missing or stale in that
workspace. Re-run the install there and restart the `apm-setup` MCP server.
