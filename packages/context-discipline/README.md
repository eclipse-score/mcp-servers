<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# context-discipline

**MCP Server for working memory management, context overlays, and local learning**

Maintains an explicit working memory session for complex coding tasks. Tracks goals, assumptions, decisions, and outcomes, then stores collaboration records and durable S-CORE context locally.

## The Problem

When doing complex work (refactoring, debugging, architecture), AI agents lose track of:
- **What are we trying to do?** (goal + subgoals)
- **What did we assume?** (verify before acting)
- **What did we discover?** (findings accumulate)
- **What did we decide?** (and why?)
- **What went wrong?** (missed nodes for next time)

Working memory solves this by making reasoning explicit.

## What It Does

Provides an MCP server with these tools:

| Tool | Purpose |
|------|----------|
| `initialize_session` | Start with goal, subgoals, assumptions |
| `query_graph` | Ask the merged code, domain, and collaboration graph |
| `record_decision` | Track a decision + reasoning |
| `record_outcome` | Record pass/fail + coverage for learning |
| `get_working_memory` | View all session entries |
| `get_unverified_assumptions` | See what still needs checking |
| `get_prior_context` | Retrieve relevant reasoning from other sessions |
| `add_overlay_node` | Add a durable S-CORE node and graph relation |

## Quick Start

### Install

```bash
apm install context-discipline --trust-transitive-mcp
# Auto-installs graphify-codegraph
```

### Use from Your Agent

```python
# Agent initializes a session
wm.initialize_session(
    goal="Refactor auth module",
    subgoals=["Understand current flow", "Identify dependencies"],
    assumptions={"Password hashing uses bcrypt": "high", "No 2FA": "low"},
)

# Agent explores code
auth_structure = wm.query_graph("Show me auth.py structure")

# Agent records findings
wm.record_decision(
    decision="Use existing auth module",
    reason=["Reduces complexity", "Proven in production"],
)

# At the end: record what worked
wm.record_outcome(
    task="Refactor auth module",
    verdict="pass",
    coverage=0.85,
    surfaced_nodes=["PasswordHasher", "TokenManager", "User"],
    missing_nodes=["MFAService", "SessionCache"],
)
```

### View Results

**Working memory** is available through the `get_working_memory` MCP tool.
Sessions are persisted in `.score-local/sessions.jsonl`. Durable domain nodes and
edges are persisted as individually reviewable shards in `score-context/`.

The overlay layout is:

```text
score-context/
├── policy.toml
├── meta.json
├── nodes/<node-id>.json
└── edges/<sha256-prefix>.json
```

Each node and edge has its own file, so independent changes touch disjoint
files and avoid a single Git merge-conflict hotspot. Node IDs used as
filenames must match `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. Edge filenames are
hashes because Graphify endpoint IDs may contain path separators.

`policy.toml` is the versioned single source of attention, privacy, and
overlay thresholds. Validate an overlay locally with:

```bash
uv run python scripts/validate_overlay.py
```

**Local session records** (append-only JSONL):
```bash
cat .score-local/sessions.jsonl | jq
```

## Local Learning Loop

```
Session 1: Refactor auth
  ↓ record_decision() → .score-local/sessions.jsonl
  {"record_type": "reasoning", "kind": "decision", ...}

Session 2: Refactor payments
  ↓ Agent sees: similar modules
  ↓ Can query: "Previous coverage on similar task?"

Session N: Pattern emerges
  ↓ Local optimizations accumulate
  ↓ Reduce token usage, time to solution
```

## Storage

**Session records** stored in `.score-local/sessions.jsonl`:

```json
{
  "record_type": "reasoning",
  "id": "reasoning__a1b2c3d4",
  "session_id": "session__12345678",
  "task_id": "task__12345678",
  "text": "Use the existing auth module",
  "kind": "decision",
  "grounded_nodes": ["PasswordHasher", "TokenManager"],
  "timestamp": "2026-08-13T10:23:45.123456+00:00"
}
```

**Add to `.gitignore`:**
```
.score-local/            # Local session records (ephemeral)
```

## Integration

**With graphify-codegraph:**
Call `query_graph()` to search the generated local Graphify code graph.

## Files in This Package

- [src/context_discipline_mcp.py](src/context_discipline_mcp.py) — MCP server implementation
- [mcp.yml](mcp.yml) — MCP server configuration
- [apm.yml](apm.yml) — Package dependencies
- [.apm/instructions/](.apm/instructions/) — Behavioral patterns
- [.apm/skills/](.apm/skills/) — VSCode workflows

## Intersession Context

The `get_prior_context` tool scores reasoning from other sessions using lexical
similarity, shared grounded nodes, and the owning task outcome. It excludes the
current session and returns deterministic top-ranked results.

## Durable Context Overlay

`add_overlay_node` writes a provenance-bearing S-CORE node and relation to
the sharded `score-context/nodes/` and `score-context/edges/` files. The
generated Graphify code graph remains read-only; the merged view combines
code, domain, and collaboration layers.

## See Also

- [graphify-codegraph](../graphify-codegraph/) — Code structure queries
- [.apm/instructions/working-memory-discipline.instructions.md](.apm/instructions/working-memory-discipline.instructions.md) — Behavioral patterns
- [.apm/skills/maintain-working-memory/SKILL.md](.apm/skills/maintain-working-memory/SKILL.md) — Step-by-step workflow

## License

Apache License 2.0
