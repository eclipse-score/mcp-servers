<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# agent-context devcontainer feature

Installs the pinned `graphify-codegraph` MCP server and registers it for the coding
agents found in the container (Claude Code, Copilot CLI, opencode, Codex). The
repository needs no change; the graph is built or downloaded on first use, see
[graphify-codegraph](../../../packages/graphify-codegraph/README.md).

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

## Testing

From the repository root, with Docker running:

```bash
npx --yes @devcontainers/cli@0.88.0 features test --project-folder features -f agent-context
```

CI tests AMD64 and ARM64 installations and a non-root consumer devcontainer.
The tests require a successful MCP initialization and tool listing, not just
the presence of an executable.
