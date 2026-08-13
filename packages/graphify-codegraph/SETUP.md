<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# graphify-codegraph Setup Guide

This guide explains the two phases of using graphify: **Setup** and **Runtime**.

## Quick Setup (Recommended)

Install the central setup package. Its declared MCP server is registered by
the same install operation:

```bash
apm install /path/to/mcp-servers/packages/apm-setup --target copilot
```

Then call `verify_setup` and `setup_graphify` through the `apm-setup` MCP
server, passing the absolute path of your repository.

The MCP tool installs Graphify when needed and generates the local code graph.

---

## Manual Setup (If Preferred)

### What happens

### What happens

The external Graphify Labs `graphify` CLI parses your code and generates a queryable graph structure. This happens once per repository.

### Step 1: Install External Tool

Install the `graphify` command-line tool (once per machine):

```bash
uv tool install graphifyy
# or: pip install graphifyy
# or: pipx install graphifyy

# Verify installation
which graphify
```

### Step 2: Generate Repository Graph

In your repository, run graphify to analyze your code:

```bash
cd /path/to/your/repo
graphify extract . --code-only
```

**Output:** Creates `graphify-out/` directory:
```
graphify-out/
├── graph.json       ← Machine-readable code graph (used by MCP)
├── graph.html       ← Interactive visual explorer
└── GRAPH_REPORT.md  ← Human-readable summary
```

### Step 3: Verify Graph Exists

```bash
# Must exist before proceeding
ls graphify-out/graph.json
echo $?  # Should be 0
```

### That's It for Setup

You've now prepared your repository for agent queries. **Do this once per repo, not per session.**

---

## Phase 2: Runtime (Agent Usage)

### What happens

Your agent runs in a working memory session. When it needs to understand code structure, it queries the **pre-generated graph** via the graphify-codegraph MCP server.

### Example: Agent Workflow

```python
# 1. Initialize session
session_id = wm.initialize_session(
    goal="Refactor authentication module",
    subgoals=["Understand current flow", "Identify dependencies"]
)

# 2. Query code structure (uses graph.json)
auth_results = wm.query_graph("Show me all functions in auth.py")
#
# Behind the scenes:
#   agent → context-discipline.query_graph()
#     → graphify-codegraph MCP server
#       → reads graphify-out/graph.json
#         → returns matching nodes/relationships

# 3. Use results to guide file reads
for result in auth_results:
    print(f"Found: {result['symbol']} at {result['file']}:{result['line']}")
    
# 4. Record findings and decisions
wm.record_finding("PasswordHasher class handles hashing")
wm.record_decision("Reuse existing PasswordHasher, don't reimplement")

# 5. At the end, record outcome
wm.record_outcome(
    task="Understand auth flow",
    verdict="pass",
    coverage=0.85,
    surfaced_nodes=["User", "Token", "PasswordHasher"],
    missing_nodes=["MFA", "OAuth"]
)
```

### MCP Server Handles This

The MCP server (`graphify-codegraph`) is already running when you start the agent. It:
1. Reads the pre-generated `graphify-out/graph.json`
2. Answers queries about code structure
3. Returns results without re-parsing your code

### No CLI Calls During Runtime

The agent **never calls `graphify` command directly** at runtime. It uses the MCP interface, which reads the cached graph.

---

## Graph Freshness

### When to Regenerate

**You should regenerate the graph when:**
- Major refactoring or code reorganization
- New modules added to the codebase
- If agent reports "function not found" but you know it exists
- Regular intervals (e.g., weekly during active development)

### How to Regenerate

```bash
cd /path/to/repo

# Option 1: Fresh regeneration
rm -rf graphify-out/
graphify extract . --code-only

# Option 2: Overwrite existing
graphify extract . --code-only  # Same effect if graph already exists
```

Takes only a few seconds.

### No MCP Restart Needed

After regeneration, the MCP server automatically reads the new `graph.json` on the next query. No restart required.

---

## Diagram: Setup vs Runtime

```
┌─────────────────────────────────────────────────────────────┐
│ SETUP PHASE (One-Time)                                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. uv tool install graphifyy                               │
│     ↓                                                         │
│     [graphify CLI installed]                                │
│                                                              │
│  2. Call setup_graphify(repo_path) through MCP                 │
│     ↓                                                         │
│     [parse code with tree-sitter AST]                       │
│     ↓                                                         │
│     [generates graphify-out/graph.json]                     │
│                                                              │
│  ✓ Repository is ready for queries                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ RUNTIME PHASE (Every Session)                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. apm install context-discipline                          │
│     ↓                                                         │
│     [installs packages + configures MCP]                    │
│                                                              │
│  2. Agent starts session                                    │
│     ↓                                                         │
│     wm.initialize_session(goal="...")                       │
│                                                              │
│  3. Agent queries code                                      │
│     ↓                                                         │
│     wm.query_graph("auth functions")                        │
│     ↓                                                         │
│     [graphify-codegraph MCP]                                │
│     ↓                                                         │
│     [reads graphify-out/graph.json (NOT CLI)]               │
│     ↓                                                         │
│     [returns: files, symbols, relationships]                │
│                                                              │
│  4. Agent explores code + makes decisions                   │
│     ↓                                                         │
│     wm.record_finding(...) + wm.record_decision(...)       │
│                                                              │
│  5. At end: record outcome                                  │
│     ↓                                                         │
│     wm.record_outcome(verdict, coverage, nodes...)         │
│     ↓                                                         │
│     [appends to .score-local/observations.jsonl]            │
│                                                              │
│  ✓ Session complete, observations recorded                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Points

| Aspect | Setup Phase | Runtime Phase |
|--------|-------------|---------------|
| **Who** | You (human) | Agent |
| **When** | Once per repo | Every session |
| **Command** | `setup_graphify(repo_path)` (MCP) | `wm.query_graph()` (MCP) |
| **Tool** | External graphify CLI | graphify-codegraph MCP server |
| **Output** | graphify-out/graph.json | Query results |
| **Re-run** | Only if code changes | Never (uses cached graph) |

---

## Troubleshooting

**Q: `graphify` command not found**
```bash
uv tool install graphifyy
which graphify  # Should show the path
```

**Q: `graph.json` not created after running `setup_graphify`**
```bash
# Make sure you're in the repo root
cd /path/to/repo
graphify extract . --code-only
ls graphify-out/  # Check what was created
```

**Q: Agent can't find code that I know exists**
```bash
# Regenerate the graph
rm -rf graphify-out/
graphify extract . --code-only
# Agent will find it on next query
```

**Q: Do I need to restart MCP after regenerating the graph?**
```
No. The MCP server automatically reads the new graph.json
on the next query. No restart needed.
```

---

## Next Steps

1. ✅ Complete Setup Phase (graphify install + graph generation)
2. ✅ Install APM packages (`apm install context-discipline`)
3. ✅ Start using agent in working memory sessions
4. ✅ Refresh graph as needed during development
