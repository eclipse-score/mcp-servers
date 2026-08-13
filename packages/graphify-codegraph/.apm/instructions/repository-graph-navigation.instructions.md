# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

---
name: repository-graph-navigation
description: Guidelines for navigating code repositories as queryable graphs
applyTo: "**"
---

# Repository Graph Navigation Guidelines

## Setup (One-Time)

Before you can query a repository graph, it must be generated. If this
repository has the `mbot-rules`/package setup wrapper, run:

```bash
./do setup-graphify
```

The `do` command dispatches `scripts/setup-graphify`; it installs the external
`graphify` CLI, generates `graphify-out/graph.json`, adds the generated
directory to `.gitignore`, and verifies the MCP setup. Check the current state
without changing anything:

```bash
./do setup-graphify --verify
```

If `./do` is unavailable, copy the setup scripts from the package source
checkout and run the script directly:

```bash
cp -r /path/to/mcp-servers/scripts ./scripts
./scripts/setup-graphify
```

Run setup before the first graph query when `graphify-out/graph.json` is
missing. Run it again after major refactoring or when the graph no longer
reflects the repository. Installing or compiling the APM package does not run
the setup command automatically.

As a manual fallback, install and run the external tool directly:

```bash
uv tool install graphifyy
cd /path/to/repo
graphify .
```

This creates `graphify-out/graph.json` — a machine-readable map of your codebase.

**When to regenerate:**
- After major code changes or refactoring
- If you suspect the graph is stale
- Regularly during active development

Regeneration takes seconds; the graph is not included in git.

## Runtime (Agent Usage)

Once the graph exists, treat your repository as a queryable knowledge graph. Query the graph structure before loading individual files.

## Decision Flow

1. **Query the graph** — What symbols, files, and relationships exist?
2. **Identify relevant nodes** — Which files/symbols are related to the task?
3. **Trace dependencies** — How do these nodes connect?
4. **Plan file reads** — Only load source code you've determined is relevant
5. **Execute targeted reads** — Open specific files, specific line ranges

## Do NOT:

- Open files randomly hoping to find things
- Read entire large files when you only need one function
- Use grep without understanding what you're looking for first
- Assume you know where something is without checking the graph

## Examples

### ✅ Good: Query graph first
- "Show me all files that import `utils.auth_handler`"
- "What are the dependency relationships in the `api/` directory?"
- "Where is the `UserService` class defined and what calls it?"
- "Map all functions that modify the `database` global state"

### ❌ Bad: Blind exploration
- Opening `src/main.py` to "understand the codebase"
- Grepping for "auth" without understanding what you're looking for
- Reading all files in a directory to find one function
- Assuming file structure based on naming patterns

## Graph Query Layers

1. **Structure** — Files, directories, modules
2. **Symbols** — Functions, classes, interfaces, variables
3. **Dependencies** — Import relationships, function calls, inheritance
4. **Ownership** — CODEOWNERS, responsibility matrices, author history
5. **Metrics** — Size, complexity, change frequency (if available)

Query from top down. Stop when you have enough information.

## Pattern: "Before I Read"

Always ask the graph before reading source:

> "Before reading `handlers.py`, show me:
> - All functions it exports
> - What it imports from other modules
> - What calls functions from this file"

Then read only the functions you determined are relevant.
