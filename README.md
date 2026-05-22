# mcp-servers

MCP (Model Context Protocol) servers for [Eclipse S-CORE](https://github.com/eclipse-score).

<!-- mcp-name: io.github.eclipse-score/mcp-servers -->

## What This Is

AI coding agents (Copilot, Claude Code, Cursor, Devin, Codex, Windsurf) work better when they can call build and test tools directly instead of guessing shell commands. This repo provides MCP servers that wrap S-CORE's Bazel-based build system and expose it as structured tool calls.

## Quick start

```sh
# Install
uv sync --all-groups

# Run the server
uv run score-mcp-server

# Run tests
uv run pytest

# Lint + type check
uv run ruff check src/ tests/
uv run basedpyright src/
```

## Available Tools

| Tool | Description |
|------|-------------|
| bazel_build | Build a Bazel target |
| bazel_test | Run tests for a Bazel target |
| bazel_query | Query the dependency graph |
| bazel_coverage | Run tests with coverage |
| lint_check | Run linter on source files |
| lint_format | Run formatter on source files |
| project_manifest | Read a repo's repo-manifest.json |
| project_discover | List available S-CORE repos and their manifests |
| server_health | Report runtime and command availability in current environment |

## Connecting an Agent

### Claude Code / Cursor / Windsurf (MCP config)

```json
{
	"mcpServers": {
		"score": {
			"command": "uv",
			"args": ["run", "score-mcp-server"],
			"cwd": "/path/to/score-mcp-server"
		}
	}
}
```

### Devin

Add to your Devin session's MCP configuration or blueprint.

### Copilot

Copilot supports MCP servers natively - configure via VS Code settings.

## Architecture

- One server, multiple tool groups. Single process, tools grouped by function (bazel, lint, project).
- Manifest-driven. Tools read repo-manifest.json from target repos - no hardcoded commands.
- Stateless. Each tool call is independent.
- Python 3.11+ / async. MCP protocol is async; all handlers are async.

## Contributing

See [AGENTS.md](AGENTS.md) for coding standards, commands, and project structure.
See [AI_CONTRIBUTION_POLICY.md](AI_CONTRIBUTION_POLICY.md) for AI disclosure rules.

## MCP Registry

This repository includes registry metadata in [server.json](server.json) and is prepared for publication to the MCP Registry.

High-level publish flow:

1. Publish the Python package to PyPI.
2. Ensure the README published on PyPI contains the mcp-name marker above.
3. Install mcp-publisher and authenticate.
4. Publish server metadata from this repository.

Example commands:

```sh
uv build
uv publish

mcp-publisher login github
mcp-publisher publish
```

## License

[Apache License 2.0](LICENSE) - Eclipse Foundation project.
