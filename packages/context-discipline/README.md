<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# context-discipline

**MCP Server for working memory management and local learning**

Maintains an explicit working memory session for complex coding tasks. Tracks goals, assumptions, decisions, and outcomes—then records observations to `.score-local/` for local performance optimization.

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
| `query_graph` | Ask graphify-codegraph about code structure |
| `record_decision` | Track a decision + reasoning |
| `record_outcome` | Record pass/fail + coverage for learning |
| `get_working_memory` | View all session entries |
| `get_unverified_assumptions` | See what still needs checking |

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
    assumptions={"Password hashing uses bcrypt": "high", "No 2FA": "low"}
)

# Agent explores code
auth_structure = wm.query_graph("Show me auth.py structure")

# Agent records findings
wm.record_decision(
    decision="Use existing auth module",
    reason=["Reduces complexity", "Proven in production"]
)

# At the end: record what worked
wm.record_outcome(
    task="Refactor auth module",
    verdict="pass",
    coverage=0.85,
    surfaced_nodes=["PasswordHasher", "TokenManager", "User"],
    missing_nodes=["MFAService", "SessionCache"]
)
```

### View Results

**Working memory** (this session's reasoning):
```bash
cat .score-local/session_*.json
```

**Local observations** (appended for learning):
```bash
cat .score-local/observations.jsonl | jq
```

## Local Learning Loop

```
Session 1: Refactor auth
  ↓ record_outcome() → .score-local/observations.jsonl
  {"task": "auth", "verdict": "pass", "coverage": 0.85, ...}

Session 2: Refactor payments
  ↓ Agent sees: similar modules
  ↓ Can query: "Previous coverage on similar task?"

Session N: Pattern emerges
  ↓ Local optimizations accumulate
  ↓ Reduce token usage, time to solution
```

## Storage

**Observations** stored in `.score-local/observations.jsonl`:

```json
{
  "session_id": "session_a1b2c3d4",
  "task": "Refactor auth module",
  "verdict": "pass",
  "coverage": 0.85,
  "path_length": 12,
  "surfaced_nodes": ["PasswordHasher", "TokenManager"],
  "missing_nodes": ["MFAService"],
  "timestamp": "2026-08-13T10:23:45.123456"
}
```

**Add to `.gitignore`:**
```
.score-local/            # Local observations (ephemeral)
```

## Integration

**With graphify-codegraph:**  
Call `query_graph()` to ask about code structure—automatically delegates to graphify MCP.

## Files in This Package

- [src/context_discipline_mcp.py](src/context_discipline_mcp.py) — MCP server implementation
- [mcp.yml](mcp.yml) — MCP server configuration
- [apm.yml](apm.yml) — Package dependencies
- [.apm/instructions/](.apm/instructions/) — Behavioral patterns
- [.apm/skills/](.apm/skills/) — VSCode workflows

## Phase 2 Integration

Your `.score-local/observations.jsonl` is prepared for Phase 2 experience learning:
- Schema aligns with ExperienceNode
- Appends automatically with each session
- Ready to feed into `libs/score-context/`

No changes needed—local optimization is self-contained.

## See Also

- [graphify-codegraph](../graphify-codegraph/) — Code structure queries
- [.apm/instructions/working-memory-discipline.instructions.md](.apm/instructions/working-memory-discipline.instructions.md) — Behavioral patterns
- [.apm/skills/maintain-working-memory/SKILL.md](.apm/skills/maintain-working-memory/SKILL.md) — Step-by-step workflow

## License

Apache License 2.0 (SPDX-License-Identifier: Apache-2.0)
