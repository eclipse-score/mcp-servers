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

Requires `uv` in the image (the S-CORE devcontainer has it). The feature is
published by the `Release` workflow together with each release.
