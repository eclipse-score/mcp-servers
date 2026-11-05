<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# agent-context devcontainer feature

Installs the pinned `graphify-codegraph` MCP server and registers it for the coding
agents found in the container (Claude Code, Copilot CLI, opencode, Codex). The
repository needs no change; the graph is built or downloaded on first use, see
[graphify-codegraph](../../../packages/graphify-codegraph/README.md).

The feature also exposes the pinned Graphify CLI on `PATH`. Run  `graphify --help` to get available commands like `graphify benchmark`.
Pass the cached graph path explicitly to commands that otherwise default to checkout-local `graphify-out/graph.json`.

Enable it once for every devcontainer in your VS Code user settings:

```json
"dev.containers.defaultFeatures": {
    "ghcr.io/eclipse-score/mcp-servers/agent-context:0": {}
}
```

On Debian/Ubuntu images, the feature installs missing Python, Git, curl, and
`uv` automatically. The server and its Python 3.12 environment are installed in
a shared system location so non-root remote users can run it. The feature is
published by the `Release` workflow together with each release.

## Consumer Repository Files

Automatic graph preparation stores downloaded or built graphs under `~/.local/share/score-agent/` by default, outside the consumer repository.
Published graphs take precedence over existing local graphs and are served without immediate local regeneration, even when the nightly revision differs from checkout HEAD.
The resolver rechecks the registry daily, keeps usable cached graphs when offline, and builds locally only when no graph is available or `force_local` is explicitly requested.
Installing this feature alone does not deploy APM instructions, skills, hooks, or project manifests.

APM installation and graph/context setup remain available; their generated outputs should be placed outside the consumer checkout rather than disabling these workflows.
Context-discipline sessions, observations, and agent salts default to repository-keyed user state under `$XDG_STATE_HOME/score-agent/` or `~/.local/state/score-agent/`; `.score-local/` requires an explicit runtime storage override.
The setup MCP generates graphs in the same user cache as the graph runtime and prepares the same user state as the context runtime without modifying consumer ignore rules.
APM supports `install --root DIR` and `compile --root DIR` for redirected output, or `install --global` and `compile --global` for supported user-scoped harness deployment.
Keep relocated instructions, skills, hooks, and MCP configuration discoverable through supported harness configuration; writing them into a cache alone does not register them.
See [APM's installation destinations](https://microsoft.github.io/apm/consumer/install-packages/#where-files-land).
This README is documentation, not an instruction automatically loaded by coding agents; reusable agent guidance is shipped through the APM packages.
Existing consumer artifacts are not automatically deleted or migrated by this change.

## Testing

From the repository root, with Docker running:

```bash
npx --yes @devcontainers/cli@0.88.0 features test --project-folder features -f agent-context
```

CI tests AMD64 and ARM64 installations and a non-root consumer devcontainer.
The tests require a successful MCP initialization and tool listing, not just
the presence of an executable.
