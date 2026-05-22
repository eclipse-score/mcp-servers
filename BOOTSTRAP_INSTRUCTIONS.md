# Bootstrap Instructions: score-mcp-server

You are bootstrapping the `eclipse-score/mcp-servers` repository from scratch. The repo is currently empty. Follow these steps in order. Do NOT skip steps. Commit after each major phase.

## Context

- **Repo:** `https://github.com/eclipse-score/mcp-servers`
- **Purpose:** MCP (Model Context Protocol) servers that expose Eclipse S-CORE Bazel build/test/lint tooling to AI coding agents
- **Language:** Python 3.11+
- **Package manager:** uv
- **License:** Apache 2.0 (Eclipse Foundation project)
- **This is developer tooling, NOT safety-critical code.** No ISO 26262, MISRA, or AUTOSAR AP rules apply.

---

## Phase 1: Repository Skeleton

Clone the repo and create the basic project structure.

### 1.1 — pyproject.toml

Create `pyproject.toml`:

```toml
[project]
name = "score-mcp-server"
version = "0.1.0"
description = "MCP servers for Eclipse S-CORE — exposes Bazel build/test/lint tooling to AI coding agents"
readme = "README.md"
license = {text = "Apache-2.0"}
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
]

[project.scripts]
score-mcp-server = "score_mcp_server.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "A", "SIM", "TCH"]

[tool.basedpyright]
pythonVersion = "3.11"
typeCheckingMode = "standard"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
    "basedpyright>=1.10",
]
```

### 1.2 — .gitignore

Create `.gitignore`:

```
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
.env
.pytest_cache/
.ruff_cache/
.mypy_cache/
htmlcov/
.coverage
*.lcov
```

### 1.3 — LICENSE

Create `LICENSE` with the full Apache License 2.0 text. You can fetch it from:
https://www.apache.org/licenses/LICENSE-2.0.txt

### 1.4 — Directory structure

Create these empty directories and `__init__.py` files:

```
mkdir -p src/score_mcp_server/tools
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p .github/workflows
mkdir -p .github/score
mkdir -p .github/instructions
mkdir -p .github/references

touch src/score_mcp_server/__init__.py
touch src/score_mcp_server/tools/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
```

### 1.5 — First commit

```
git add -A
git commit -m "chore: initial project skeleton

pyproject.toml, directory structure, .gitignore, LICENSE.

Assisted-by: <your-tool> <noreply@vendor.com>"
```

---

## Phase 2: Governance and Documentation Files

### 2.1 — AGENTS.md

Create `AGENTS.md` at repo root with this exact content:

```markdown
# AGENTS.md — score-mcp-server

Canonical assistant policy for this repository. Read by Codex, Claude Code (via CLAUDE.md), Copilot, Cursor, Devin, Windsurf, and other coding agents.

## What This Repo Is

`score-mcp-server` provides [Model Context Protocol (MCP)](https://modelcontextprotocol.io) servers that expose Eclipse S-CORE build, test, and project tooling to AI coding agents. Instead of agents guessing how to build or test S-CORE repos, they connect to these MCP servers and call tools directly.

**This repo is NOT safety-critical code.** It is developer tooling. Safety rules (ISO 26262, MISRA, AUTOSAR AP) do not apply here — they apply to the repos these MCP servers wrap.

### Context

- Eclipse S-CORE is a multi-company automotive onboard platform (C++/Rust/Bazel).
- Multiple companies contribute using different AI tools (Copilot, Devin, Claude Code, Cursor, etc.).
- Eclipse Foundation governance: Apache 2.0 license, Eclipse DCO, IP review for contributions >1000 lines.
- MCP is the industry-standard protocol for agent-to-tool integration.

## Prerequisites

- Python 3.11+ (primary implementation language)
- [uv](https://docs.astral.sh/uv/) (package manager)
- Git
- For integration tests: Bazel (to test against real S-CORE repos)

## Commands

```sh
# Install dependencies
uv sync --all-groups

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_bazel_server.py -xvs

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Type check
uv run basedpyright src/

# Run the MCP server locally (for development)
uv run score-mcp-server
```

## Repository Structure

```
score-mcp-server/
├── src/
│   └── score_mcp_server/
│       ├── __init__.py
│       ├── server.py            — MCP server entry point and lifecycle
│       ├── tools/               — Tool implementations (one file per tool group)
│       │   ├── __init__.py
│       │   ├── bazel.py         — build, test, query, coverage tools
│       │   ├── lint.py          — lint and format tools
│       │   └── project.py       — repo discovery, manifest reading
│       ├── config.py            — Server configuration and defaults
│       └── manifest.py          — repo-manifest.json parser
├── tests/
│   ├── unit/                    — Unit tests (mocked, no Bazel required)
│   └── integration/             — Integration tests (require Bazel + real repo)
├── .github/
│   ├── instructions/            — SCORE coding standards (from governance overlay)
│   ├── references/              — Schemas (repo-manifest, agent-card)
│   ├── score/                   — repo-manifest.json for THIS repo
│   └── workflows/               — CI/CD
├── pyproject.toml               — Project metadata and dependencies
├── AGENTS.md                    — This file
├── CLAUDE.md                    — Claude Code import → AGENTS.md
├── AI_CONTRIBUTION_POLICY.md    — AI disclosure and accountability rules
└── README.md                    — User-facing documentation
```

## MCP Server Architecture

### Design Principles

1. **One server, multiple tool groups.** A single `score-mcp-server` process exposes all tools. Tool groups (bazel, lint, project) are logical groupings, not separate servers.
2. **Manifest-driven.** Tools read `.github/score/repo-manifest.json` from the target repo to discover build/test/lint commands. Do not hardcode commands.
3. **Stateless.** Each tool call is independent. No session state between calls.
4. **Safe by default.** Tools that modify state (build, test) must operate in the caller's working directory. Never write outside the repo root.

### Tool Naming Convention

Tool names follow `<group>_<action>` pattern:

```
bazel_build       — Build a Bazel target
bazel_test        — Run tests for a Bazel target
bazel_query       — Query the dependency graph
bazel_coverage    — Run tests with coverage
lint_check        — Run linter
lint_format       — Run formatter
project_manifest  — Read and return the repo-manifest.json
project_discover  — List available repos and their manifests
```

### Adding a New Tool

1. Create or edit the appropriate file in `src/score_mcp_server/tools/`
2. Implement the tool function with MCP tool decorator
3. Add unit tests in `tests/unit/`
4. Add integration test if the tool calls external programs
5. Update this AGENTS.md if adding a new tool group

## Coding Standards

### Python

- Python 3.11+ — use modern syntax (match/case, `X | Y` union types, etc.)
- Format with `ruff format`, lint with `ruff check`
- Type annotations on all public functions and methods
- Type check with `basedpyright` — zero errors
- No `Any` types unless wrapping genuinely untyped external APIs (document why)
- Async by default for MCP handlers (MCP protocol is async)

### General

- Instruction files in `.github/instructions/` apply (coding style, security, testing, git workflow)
- 80% test coverage minimum
- No hardcoded secrets — use environment variables
- All public APIs documented with docstrings

## AI Disclosure

All AI-assisted commits MUST include an `Assisted-by:` trailer:

```
feat: add bazel_coverage tool

Implement coverage collection via bazel coverage command
with lcov output parsing.

Assisted-by: GitHub Copilot <noreply@github.com>
```

Standard trailers:

| Tool | Trailer |
|------|---------|
| GitHub Copilot | `Assisted-by: GitHub Copilot <noreply@github.com>` |
| Claude Code | `Assisted-by: Claude Code <noreply@anthropic.com>` |
| Cursor | `Assisted-by: Cursor <noreply@cursor.com>` |
| Devin | `Assisted-by: Devin <noreply@cognition.ai>` |
| Codex | `Assisted-by: Codex <noreply@openai.com>` |
| Windsurf | `Assisted-by: Windsurf <noreply@codeium.com>` |

See `AI_CONTRIBUTION_POLICY.md` for full disclosure rules, scope, and legal details.

### Commit Format

```
<type>: <summary>

<optional body>

Assisted-by: <tool> <email>   ← only if AI-assisted
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

## PR Conventions

- Reference an issue: `Fixes #<number>` or `Relates to #<number>`
- Check the AI disclosure box in the PR template if AI tools were used
- All CI must pass before review
- One approval required

## SCORE Governance

- `.github/score/repo-manifest.json` — machine-readable build/test/lint for this repo
- `.github/references/repo-manifest.schema.json` — schema for repo manifests
- `.github/references/agent-card.schema.json` — schema for work/handoff artifacts (not A2A AgentCard)
- Keep this repo focused on MCP server implementation — no prompt catalogs or agent frameworks
```

### 2.2 — AI_CONTRIBUTION_POLICY.md

Create `AI_CONTRIBUTION_POLICY.md` at repo root with this exact content:

```markdown
# AI Contribution Policy — score-mcp-server

**Scope:** This repository (`eclipse-score/mcp-servers`)
**Status:** Draft

## AI Tools Are Welcome

This is developer tooling, not safety-critical vehicle software. AI-assisted contributions are encouraged — MCP server code is an ideal use case for AI coding tools.

## Disclosure

### When Required

Disclose when AI generated code, tests, documentation, or design approaches you included.

### When Not Required

No disclosure needed for: IDE autocomplete (single-line), Q&A/learning, spell/grammar fixes, AI-assisted code review (reading).

**When in doubt, disclose.**

### How

**Commit trailers** (mandatory for AI-assisted commits):

```
Assisted-by: GitHub Copilot <noreply@github.com>
```

**PR template checkbox** (supplementary — catches forgotten trailers):

```
- [x] This PR contains AI-assisted code
- Tool(s) used: Copilot, Claude Code
```

## Human Accountability

- AI tools cannot be authors or co-authors
- `Signed-off-by` (DCO) comes from humans only
- You must read, understand, and verify all AI-generated code
- The human submitter bears full legal responsibility

## Quality

AI-assisted code is held to the same standard:

- Must pass CI (build, test, lint, type check)
- Must follow coding standards (`.github/instructions/`)
- Must include tests
- Low-effort unreviewed AI output may be rejected without detailed feedback

## Licensing

- All contributions licensed under Apache 2.0
- Eclipse Foundation IP review applies for contributions >1000 lines
- Ensure AI-generated code doesn't include incompatibly licensed content

## References

- [KubeVirt AI Policy](https://github.com/kubevirt/community/blob/main/ai-contribution-policy.md)
- [Linux Kernel AI Policy](https://lore.kernel.org/all/) (April 2026)
- [Eclipse Foundation Contribution Guidelines](https://www.eclipse.org/legal/ECA.php)
```

### 2.3 — CLAUDE.md

Create `CLAUDE.md` at repo root:

```markdown
@AGENTS.md

## Claude Code notes

- Keep Claude-specific additions in this file below the AGENTS import.
- Prefer .claude/rules/ for path-specific rules when repository complexity grows.
- Keep this file short; put shared project behavior in AGENTS.md.
```

### 2.4 — README.md

Create `README.md` at repo root with this exact content:

```markdown
# score-mcp-server

MCP (Model Context Protocol) servers for [Eclipse S-CORE](https://github.com/eclipse-score).

## What This Is

AI coding agents (Copilot, Claude Code, Cursor, Devin, Codex, Windsurf) work better when they can call build and test tools directly instead of guessing shell commands. This repo provides MCP servers that wrap S-CORE's Bazel-based build system and expose it as structured tool calls.

## Quick Start

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
| `bazel_build` | Build a Bazel target |
| `bazel_test` | Run tests for a Bazel target |
| `bazel_query` | Query the dependency graph |
| `bazel_coverage` | Run tests with coverage |
| `lint_check` | Run linter on source files |
| `lint_format` | Run formatter on source files |
| `project_manifest` | Read a repo's `repo-manifest.json` |
| `project_discover` | List available S-CORE repos and their manifests |

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

Copilot supports MCP servers natively — configure via VS Code settings.

## Architecture

- **One server, multiple tool groups.** Single process, tools grouped by function (bazel, lint, project).
- **Manifest-driven.** Tools read `repo-manifest.json` from target repos — no hardcoded commands.
- **Stateless.** Each tool call is independent.
- **Python 3.11+ / async.** MCP protocol is async; all handlers are async.

## Contributing

See [AGENTS.md](AGENTS.md) for coding standards, commands, and project structure.
See [AI_CONTRIBUTION_POLICY.md](AI_CONTRIBUTION_POLICY.md) for AI disclosure rules.

## License

[Apache License 2.0](LICENSE) — Eclipse Foundation project.
```

### 2.5 — .github/PULL_REQUEST_TEMPLATE.md

Create `.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
## Description

<!-- What does this PR do? Reference the issue. -->

Fixes #

## Changes

<!-- Brief list of changes -->

-

## Testing

<!-- How was this tested? -->

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated (if tool calls external programs)
- [ ] All tests pass: `uv run pytest`
- [ ] Lint passes: `uv run ruff check src/ tests/`
- [ ] Type check passes: `uv run basedpyright src/`

## AI Disclosure

- [ ] This PR contains AI-assisted code or documentation

<!-- If checked: -->
**Tool(s) used:**
<!-- e.g., GitHub Copilot, Claude Code, Devin, Cursor -->

**Verification:**
- [ ] I have reviewed and understand all AI-generated code
- [ ] All AI-assisted commits include an `Assisted-by:` trailer
```

### 2.6 — .github/workflows/ai-disclosure-check.yml

Create `.github/workflows/ai-disclosure-check.yml`:

```yaml
# Checks consistency between PR template AI disclosure checkbox
# and Assisted-by: commit trailers. Warns but does not block.

name: AI Disclosure Check

on:
  pull_request:
    types: [opened, synchronize, edited]

jobs:
  check-ai-disclosure:
    runs-on: ubuntu-latest
    steps:
      - name: Check AI disclosure consistency
        uses: actions/github-script@v7
        with:
          script: |
            const pr = context.payload.pull_request;
            const body = pr.body || '';

            const aiDisclosureChecked = body.includes('[x] This PR contains AI-assisted code');

            if (!aiDisclosureChecked) {
              console.log('No AI disclosure indicated. Skipping trailer check.');
              return;
            }

            const commits = await github.rest.pulls.listCommits({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: pr.number,
            });

            const hasTrailer = commits.data.some(c =>
              c.commit.message.toLowerCase().includes('assisted-by:')
            );

            if (!hasTrailer) {
              core.warning(
                'AI disclosure is checked but no commits have Assisted-by: trailers. ' +
                'Please add trailers to AI-assisted commits. ' +
                'See AI_CONTRIBUTION_POLICY.md for details.'
              );
            } else {
              console.log('AI disclosure and trailers are consistent.');
            }
```

### 2.7 — .github/score/repo-manifest.json

Create `.github/score/repo-manifest.json`:

```json
{
  "$schema": "../references/repo-manifest.schema.json",
  "version": 1,
  "repository": {
    "name": "score-mcp-server",
    "language": "python",
    "visibility": "public",
    "tags": [
      "mcp",
      "developer-tooling",
      "agent-infrastructure"
    ]
  },
  "bootstrap": {
    "contract_version": "v0.1.0",
    "template_version": "v0.1.0"
  },
  "execution": {
    "build": {
      "command": "uv build"
    },
    "test": {
      "command": "uv run pytest"
    },
    "lint": {
      "command": "uv run ruff check src/ tests/"
    },
    "typecheck": {
      "command": "uv run basedpyright src/"
    }
  },
  "mcp": {
    "server_name": "score-mcp-server",
    "tools": [
      "build",
      "test",
      "lint",
      "typecheck"
    ]
  }
}
```

### 2.8 — Second commit

```
git add -A
git commit -m "docs: add AGENTS.md, AI policy, README, PR template, and governance files

- AGENTS.md: full agent handbook (Airflow-quality, MCP-specific)
- AI_CONTRIBUTION_POLICY.md: disclosure rules, accountability, quality standards
- CLAUDE.md: Claude Code import
- README.md: quick start, tool catalog, agent connection examples
- PR template with AI disclosure checkbox
- AI disclosure CI check (warns on inconsistency)
- repo-manifest.json for SCORE governance

Assisted-by: <your-tool> <noreply@vendor.com>"
```

---

## Phase 3: MCP Server Implementation

### 3.1 — src/score_mcp_server/config.py

Server configuration and defaults:

```python
"""Server configuration and defaults."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ServerConfig:
    """Configuration for the SCORE MCP server."""

    server_name: str = "score-mcp-server"
    server_version: str = "0.1.0"
    manifest_filename: str = "repo-manifest.json"
    manifest_path: str = ".github/score"

    def manifest_file(self, repo_root: Path) -> Path:
        """Return the full path to repo-manifest.json for a given repo root."""
        return repo_root / self.manifest_path / self.manifest_filename


DEFAULT_CONFIG = ServerConfig()
```

### 3.2 — src/score_mcp_server/manifest.py

Manifest parser — reads repo-manifest.json:

```python
"""Parser for SCORE repo-manifest.json files."""

import json
from dataclasses import dataclass
from pathlib import Path

from score_mcp_server.config import DEFAULT_CONFIG, ServerConfig


@dataclass(frozen=True)
class ExecutionCommand:
    """A single execution command from the manifest."""

    command: str
    working_directory: str | None = None


@dataclass(frozen=True)
class RepoManifest:
    """Parsed repo-manifest.json."""

    name: str
    language: str
    visibility: str
    tags: list[str]
    build: ExecutionCommand
    test: ExecutionCommand
    lint: ExecutionCommand
    typecheck: ExecutionCommand | None = None


def parse_manifest(repo_root: Path, config: ServerConfig = DEFAULT_CONFIG) -> RepoManifest:
    """Parse a repo-manifest.json from a given repo root.

    Args:
        repo_root: Path to the repository root directory.
        config: Server configuration with manifest path settings.

    Returns:
        Parsed RepoManifest.

    Raises:
        FileNotFoundError: If the manifest file does not exist.
        json.JSONDecodeError: If the manifest file is not valid JSON.
        KeyError: If required fields are missing from the manifest.
    """
    manifest_path = config.manifest_file(repo_root)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    repo = data["repository"]
    execution = data["execution"]

    typecheck_data = execution.get("typecheck")
    typecheck = ExecutionCommand(**typecheck_data) if typecheck_data else None

    return RepoManifest(
        name=repo["name"],
        language=repo["language"],
        visibility=repo["visibility"],
        tags=repo.get("tags", []),
        build=ExecutionCommand(**execution["build"]),
        test=ExecutionCommand(**execution["test"]),
        lint=ExecutionCommand(**execution["lint"]),
        typecheck=typecheck,
    )
```

### 3.3 — src/score_mcp_server/tools/project.py

Project tools — manifest reading and repo discovery:

```python
"""Project tools — manifest reading and repo discovery."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from score_mcp_server.manifest import parse_manifest


def register_project_tools(mcp: FastMCP) -> None:
    """Register project-related tools on the MCP server."""

    @mcp.tool()
    async def project_manifest(repo_path: str) -> dict:
        """Read and return the repo-manifest.json for a SCORE repository.

        Args:
            repo_path: Absolute path to the repository root.

        Returns:
            Parsed manifest as a dictionary with repo metadata and execution commands.
        """
        repo_root = Path(repo_path)
        manifest = parse_manifest(repo_root)
        return {
            "name": manifest.name,
            "language": manifest.language,
            "visibility": manifest.visibility,
            "tags": manifest.tags,
            "build": manifest.build.command,
            "test": manifest.test.command,
            "lint": manifest.lint.command,
            "typecheck": manifest.typecheck.command if manifest.typecheck else None,
        }

    @mcp.tool()
    async def project_discover(search_root: str = ".") -> list[dict]:
        """Discover SCORE repositories by scanning for repo-manifest.json files.

        Args:
            search_root: Directory to start scanning from. Defaults to current directory.

        Returns:
            List of discovered repos with their manifest data.
        """
        root = Path(search_root).resolve()
        results: list[dict] = []

        for manifest_file in root.rglob(".github/score/repo-manifest.json"):
            repo_root = manifest_file.parent.parent.parent
            try:
                manifest = parse_manifest(repo_root)
                results.append({
                    "path": str(repo_root),
                    "name": manifest.name,
                    "language": manifest.language,
                    "tags": manifest.tags,
                })
            except (KeyError, ValueError):
                continue

        return results
```

### 3.4 — src/score_mcp_server/tools/bazel.py

Bazel tools — build, test, query, coverage:

```python
"""Bazel tools — build, test, query, coverage."""

import asyncio
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from score_mcp_server.manifest import parse_manifest


async def _run_command(command: str, cwd: Path) -> dict:
    """Run a shell command and return structured output.

    Args:
        command: Shell command to execute.
        cwd: Working directory for the command.

    Returns:
        Dictionary with stdout, stderr, and return code.
    """
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return {
        "command": command,
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
        "returncode": proc.returncode,
    }


def register_bazel_tools(mcp: FastMCP) -> None:
    """Register Bazel-related tools on the MCP server."""

    @mcp.tool()
    async def bazel_build(repo_path: str, target: str = "//...") -> dict:
        """Build a Bazel target in a SCORE repository.

        Args:
            repo_path: Absolute path to the repository root.
            target: Bazel target to build. Defaults to //... (all targets).

        Returns:
            Command output with stdout, stderr, and return code.
        """
        repo_root = Path(repo_path)
        manifest = parse_manifest(repo_root)
        command = manifest.build.command.replace("//...", target)
        return await _run_command(command, cwd=repo_root)

    @mcp.tool()
    async def bazel_test(repo_path: str, target: str = "//...") -> dict:
        """Run tests for a Bazel target in a SCORE repository.

        Args:
            repo_path: Absolute path to the repository root.
            target: Bazel target to test. Defaults to //... (all targets).

        Returns:
            Command output with stdout, stderr, and return code.
        """
        repo_root = Path(repo_path)
        manifest = parse_manifest(repo_root)
        command = manifest.test.command.replace("//...", target)
        return await _run_command(command, cwd=repo_root)

    @mcp.tool()
    async def bazel_query(repo_path: str, query: str) -> dict:
        """Query the Bazel dependency graph.

        Args:
            repo_path: Absolute path to the repository root.
            query: Bazel query expression (e.g., 'deps(//path/to:target)').

        Returns:
            Command output with query results.
        """
        repo_root = Path(repo_path)
        command = f"bazel query '{query}'"
        return await _run_command(command, cwd=repo_root)

    @mcp.tool()
    async def bazel_coverage(repo_path: str, target: str = "//...") -> dict:
        """Run tests with coverage collection.

        Args:
            repo_path: Absolute path to the repository root.
            target: Bazel target to collect coverage for.

        Returns:
            Command output with coverage data.
        """
        repo_root = Path(repo_path)
        command = f"bazel coverage {target}"
        return await _run_command(command, cwd=repo_root)
```

### 3.5 — src/score_mcp_server/tools/lint.py

Lint tools:

```python
"""Lint tools — check and format."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from score_mcp_server.manifest import parse_manifest
from score_mcp_server.tools.bazel import _run_command


def register_lint_tools(mcp: FastMCP) -> None:
    """Register lint-related tools on the MCP server."""

    @mcp.tool()
    async def lint_check(repo_path: str) -> dict:
        """Run the linter on a SCORE repository.

        Args:
            repo_path: Absolute path to the repository root.

        Returns:
            Lint output with any warnings or errors.
        """
        repo_root = Path(repo_path)
        manifest = parse_manifest(repo_root)
        return await _run_command(manifest.lint.command, cwd=repo_root)

    @mcp.tool()
    async def lint_format(repo_path: str) -> dict:
        """Run the formatter on a SCORE repository.

        Uses ruff format for Python repos, clang-format for C++ repos.

        Args:
            repo_path: Absolute path to the repository root.

        Returns:
            Formatter output.
        """
        repo_root = Path(repo_path)
        manifest = parse_manifest(repo_root)

        match manifest.language:
            case "python":
                command = manifest.lint.command.replace("check", "format")
            case "cpp" | "rust":
                command = manifest.lint.command
            case _:
                command = manifest.lint.command

        return await _run_command(command, cwd=repo_root)
```

### 3.6 — src/score_mcp_server/server.py

Main server entry point:

```python
"""SCORE MCP Server — entry point and lifecycle."""

from mcp.server.fastmcp import FastMCP

from score_mcp_server.config import DEFAULT_CONFIG
from score_mcp_server.tools.bazel import register_bazel_tools
from score_mcp_server.tools.lint import register_lint_tools
from score_mcp_server.tools.project import register_project_tools


def create_server() -> FastMCP:
    """Create and configure the SCORE MCP server.

    Returns:
        Configured FastMCP server instance with all tool groups registered.
    """
    mcp = FastMCP(
        DEFAULT_CONFIG.server_name,
        version=DEFAULT_CONFIG.server_version,
    )

    register_project_tools(mcp)
    register_bazel_tools(mcp)
    register_lint_tools(mcp)

    return mcp


def main() -> None:
    """Run the SCORE MCP server."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
```

### 3.7 — Third commit

```
git add -A
git commit -m "feat: initial MCP server implementation

- server.py: entry point with FastMCP, registers all tool groups
- config.py: server configuration dataclass
- manifest.py: repo-manifest.json parser
- tools/bazel.py: bazel_build, bazel_test, bazel_query, bazel_coverage
- tools/lint.py: lint_check, lint_format
- tools/project.py: project_manifest, project_discover

Assisted-by: <your-tool> <noreply@vendor.com>"
```

---

## Phase 4: Tests

### 4.1 — tests/unit/test_manifest.py

```python
"""Unit tests for the manifest parser."""

import json
from pathlib import Path

import pytest

from score_mcp_server.manifest import ExecutionCommand, RepoManifest, parse_manifest


@pytest.fixture()
def sample_manifest(tmp_path: Path) -> Path:
    """Create a temporary repo with a valid repo-manifest.json."""
    manifest_dir = tmp_path / ".github" / "score"
    manifest_dir.mkdir(parents=True)

    manifest_data = {
        "version": 1,
        "repository": {
            "name": "test-repo",
            "language": "python",
            "visibility": "public",
            "tags": ["test"],
        },
        "bootstrap": {"contract_version": "v0.1.0"},
        "execution": {
            "build": {"command": "uv build"},
            "test": {"command": "uv run pytest"},
            "lint": {"command": "uv run ruff check src/"},
            "typecheck": {"command": "uv run basedpyright src/"},
        },
    }

    manifest_file = manifest_dir / "repo-manifest.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
    return tmp_path


def test_parse_manifest(sample_manifest: Path) -> None:
    """Test parsing a valid manifest."""
    result = parse_manifest(sample_manifest)

    assert result.name == "test-repo"
    assert result.language == "python"
    assert result.visibility == "public"
    assert result.tags == ["test"]
    assert result.build == ExecutionCommand(command="uv build")
    assert result.test == ExecutionCommand(command="uv run pytest")
    assert result.lint == ExecutionCommand(command="uv run ruff check src/")
    assert result.typecheck == ExecutionCommand(command="uv run basedpyright src/")


def test_parse_manifest_without_typecheck(tmp_path: Path) -> None:
    """Test parsing a manifest without optional typecheck."""
    manifest_dir = tmp_path / ".github" / "score"
    manifest_dir.mkdir(parents=True)

    manifest_data = {
        "version": 1,
        "repository": {
            "name": "minimal-repo",
            "language": "cpp",
            "visibility": "public",
        },
        "bootstrap": {"contract_version": "v0.1.0"},
        "execution": {
            "build": {"command": "bazel build //..."},
            "test": {"command": "bazel test //..."},
            "lint": {"command": "bazel run //:lint"},
        },
    }

    manifest_file = manifest_dir / "repo-manifest.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    result = parse_manifest(tmp_path)

    assert result.name == "minimal-repo"
    assert result.language == "cpp"
    assert result.typecheck is None
    assert result.tags == []


def test_parse_manifest_file_not_found(tmp_path: Path) -> None:
    """Test that FileNotFoundError is raised for missing manifest."""
    with pytest.raises(FileNotFoundError):
        parse_manifest(tmp_path)


def test_parse_manifest_invalid_json(tmp_path: Path) -> None:
    """Test that JSONDecodeError is raised for invalid JSON."""
    manifest_dir = tmp_path / ".github" / "score"
    manifest_dir.mkdir(parents=True)
    manifest_file = manifest_dir / "repo-manifest.json"
    manifest_file.write_text("not valid json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        parse_manifest(tmp_path)
```

### 4.2 — tests/unit/test_server.py

```python
"""Unit tests for server creation."""

from score_mcp_server.server import create_server


def test_create_server() -> None:
    """Test that the server is created with all tool groups."""
    server = create_server()
    assert server is not None
    assert server.name == "score-mcp-server"
```

### 4.3 — Fourth commit

```
git add -A
git commit -m "test: add unit tests for manifest parser and server creation

- test_manifest.py: valid parsing, missing typecheck, missing file, invalid JSON
- test_server.py: server creation smoke test

Assisted-by: <your-tool> <noreply@vendor.com>"
```

---

## Phase 5: Verify and Push

### 5.1 — Install and verify

```sh
uv sync --all-groups
uv run pytest -xvs
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run basedpyright src/
```

Fix any issues. All four checks must pass.

### 5.2 — Push to main

```sh
git push origin main
```

Or if contributing via PR:

```sh
git checkout -b feat/initial-bootstrap
git push origin feat/initial-bootstrap
```

Then open a PR with the AI disclosure checkbox checked.

---

## Summary of Commits

| # | Commit Message | Phase |
|---|---------------|-------|
| 1 | `chore: initial project skeleton` | Skeleton |
| 2 | `docs: add AGENTS.md, AI policy, README, PR template, and governance files` | Governance |
| 3 | `feat: initial MCP server implementation` | Implementation |
| 4 | `test: add unit tests for manifest parser and server creation` | Tests |

Total: 4 commits, each self-contained and passing.
