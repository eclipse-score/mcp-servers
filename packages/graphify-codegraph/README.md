<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# graphify-codegraph

**Guidance and MCP integration for [Graphify Labs graphify](https://github.com/Graphify-Labs/graphify)** — understand your codebase structure without LLMs, embeddings, or network calls.

## The Problem

When working on unfamiliar code, you need to understand:
- **What classes/functions exist?**
- **How are they connected?**
- **Where should I make changes?**
- **What will break if I change this?**

AI agents typically ask embeddings (slow, cloud) or LLMs (hallucinate). Graphify uses **deterministic AST parsing** instead—100% local, fully accurate.

## What This Package Does

We wrap the external [Graphify Labs graphify](https://github.com/Graphify-Labs/graphify) tool and provide:

1. **MCP Server** — Query interface for agents (reads pre-generated graph)
2. **Behavioral Guidance** — How to use graphs effectively 
3. **Skills** — VSCode workflow integrations
4. **Context Integration** — Plugs into context-discipline working memory

## Architecture

Two-phase system:

**Phase 1: Setup (one-time)**
```
You run: graphify .
    ↓
External tool parses code with tree-sitter
    ↓
Generates: graphify-out/
  ├── graph.json (your code structure)
  ├── graph.html (visual explorer)
  └── GRAPH_REPORT.md
```

**Phase 2: Queries (during coding)**
```
Agent: context-discipline.query_graph("auth functions")
    ↓
graphify-codegraph MCP (this package)
    ↓
Reads existing graph.json
    ↓
Returns: matching nodes from your code structure
```

**Key point:** The MCP queries a **pre-generated graph**. You generate it once per repo, then agents query it repeatedly without re-parsing.

## Quick Start

### Setup (One-time per repo)

```bash
# Step 1: Install packages
apm install context-discipline
apm compile -t copilot

# Step 2: Run the setup wizard from your project root
cd /your/project
./do setup-graphify
```

**The wizard will:**
- ✓ Install graphify CLI (if needed)
- ✓ Generate code graph in your repo
- ✓ Verify MCP setup
- ✓ Show completion status

Done. You don't regenerate this unless your code changes significantly.

The `do` wrapper dispatches the executable `scripts/setup-graphify` command. If
your project has no `./do`, copy the `scripts` directory from the package source
checkout and run `./scripts/setup-graphify` directly.

### Usage (During coding)

Now your agent can query the graph:

```python
# From your working memory session
auth_structure = wm.query_graph("Where is authentication logic?")
# ↓ Calls graphify-codegraph MCP
# ↓ Reads graphify-out/graph.json
# ↓ Returns: Files, classes, functions related to auth
```

Or explore manually:

```bash
graphify explain "User"        # What is the User class?
graphify path "Request" "Auth" # How are they connected?
graphify query "validation"    # Find related code
```

## What You Get

When you run `graphify .` once:

| File | Purpose |
|------|---------|
| **graph.html** | Interactive browser view—search, filter, click nodes |
| **graph.json** | Complete graph structure; reused by MCP without re-parsing |
| **GRAPH_REPORT.md** | Highlights: key classes, communities, suggested queries |

Your agent queries `graph.json` via MCP repeatedly without regenerating it.

## Key Principles

- **100% Local** — No cloud, no LLM, no embeddings. Pure code structure.
- **Deterministic** — Same input always produces same graph.
- **Explains Connections** — Every edge is labeled: "imports", "calls", "extends", etc.
- **No Reimplementation** — Uses proven external tool (Graphify Labs).
- **Works Offline** — Parse your code without network.

## Integration with context-discipline

When you call `query_graph()` in a working memory session, you're using **graphify-codegraph MCP**, not the CLI:

```python
# Agent session
wm.query_graph("Find all database connections")
```

**Behind the scenes:**
1. context-discipline MCP → calls graphify-codegraph MCP
2. graphify-codegraph MCP → reads graphify-out/graph.json
3. Returns matching nodes

You don't call the CLI repeatedly—that's the whole point of generating the graph once and querying it many times.

## Files in This Package

- [README.md](README.md) — This file
- [apm.yml](apm.yml) — Package metadata, dependencies
- [mcp.yml](mcp.yml) — MCP server configuration
- [src/serve.py](src/serve.py) — MCP server launcher
- [.apm/instructions/](./apm/instructions/) — How to use graphs in projects
- [.apm/skills/](./apm/skills/) — VSCode workflow integrations

## Troubleshooting

**Q: Command not found: graphify**
```bash
uv tool install graphifyy
# Verify: which graphify
```

**Q: graph.json not created**
```bash
cd /path/to/repo
graphify .  # Must run from repo root
ls graphify-out/  # Check output
```

**Q: Graph is outdated after code changes**
```bash
rm -rf graphify-out/
graphify .  # Regenerate
```

**Q: Agent can't find graph (MCP error)**
```
Make sure you:
1. Ran graphify . in the repo
2. Installed context-discipline via apm
3. graph.json exists at graphify-out/graph.json
```

## More Information

- **External Tool:** [Graphify Labs graphify](https://github.com/Graphify-Labs/graphify)
- **About Deterministic Graphs:** See [.apm/instructions/repository-graph-navigation.instructions.md](./apm/instructions/repository-graph-navigation.instructions.md)
- **VSCode Integration:** See [.apm/skills/map-repository-graph/SKILL.md](./apm/skills/map-repository-graph/SKILL.md)
- **Context-Discipline:** How working memory uses graphs

## License

This guidance package: Apache License 2.0  
External graphify tool: [Graphify Labs License](https://github.com/Graphify-Labs/graphify/blob/main/LICENSE)
