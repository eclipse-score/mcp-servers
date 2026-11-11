<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# agent-context devcontainer feature

Installs the pinned `graphify-codegraph` MCP server and registers it for the coding
agents found in the container (VS Code Copilot Chat, Claude Code, OpenCode, Codex).
The repository needs no change; the graph is built or downloaded on first use, see
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

## APM and VS Code Copilot

Container creation installs the pinned APM CLI (`0.35.0`) and the
`graphify-codegraph` and `apm-setup` packages for the user-level `agent-skills`
target. Their shared skills are stored in `~/.agents/skills/`; APM state stays
under `~/.apm/`. No APM manifest, lockfile, or generated instructions are
written into the consumer checkout.

APM 0.35.0 requires Git 2.26 or newer for its Git URL-rewrite safety check.
The feature reports a clear error rather than proceeding if the existing Git is
older.

The MCP servers are registered in the VS Code user-profile `mcp.json`, normally
`~/.vscode-server/data/User/mcp.json`. Existing servers and other configuration
are preserved. Set `VSCODE_AGENT_FOLDER` when the remote server uses a
non-default location. Existing profile-specific MCP files are updated as well.

Here, Copilot means **VS Code Copilot Chat**. APM's global `--target copilot`
path is partial and writes Copilot CLI configuration; it is not the VS Code
Chat user-profile MCP config. The feature uses APM's cross-tool skills target
and separately registers the MCP servers using VS Code's supported user-profile
configuration. It does not infer that Copilot CLI is installed from a `copilot`
command on `PATH`.

The APM package source defaults to the repository's `main` ref. Set
`AGENT_CONTEXT_APM_REF` to a branch, tag, or commit to use another revision.

## Consumer Repository Files

Automatic graph preparation stores downloaded or built graphs under `~/.local/share/score-agent/` by default, outside the consumer repository.
Published graphs take precedence over existing local graphs and are served without immediate local regeneration, even when the nightly revision differs from checkout HEAD.
The resolver rechecks the registry daily, keeps usable cached graphs when offline, and builds locally only when no graph is available or `force_local` is explicitly requested.
Installing this feature deploys APM skills to user scope; it does not create
APM instructions, skills, hooks, or manifests in the consumer repository.

Graph/context setup remains available; generated outputs stay outside the
consumer checkout rather than disabling these workflows.
Context-discipline sessions, observations, and agent salts default to repository-keyed user state under `$XDG_STATE_HOME/score-agent/` or `~/.local/state/score-agent/`; `.score-local/` requires an explicit runtime storage override.
The setup MCP generates graphs in the same user cache as the graph runtime and prepares the same user state as the context runtime without modifying consumer ignore rules.
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
The consumer test also verifies the pinned APM CLI, user-scoped skills, VS Code
user MCP registration, preservation of existing MCP config, and a clean
consumer checkout.
