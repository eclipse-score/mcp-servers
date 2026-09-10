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
apm init --yes --target copilot
apm install <path>/packages/context-discipline \
  --target copilot \
  --trust-transitive-mcp
apm compile -t copilot
```

### Testing a branch

Override the MCP server source in the installed package with the branch you
want to test, then refresh the dependency:

```yaml
args:
  - --from
  - git+https://github.com/eclipse-score/mcp-servers@<branch>#subdirectory=packages/context-discipline
  - context-discipline
```

Run `apm install ... --refresh` after applying the override.
Restart VS Code because MCP servers are read only at startup. `apm update` can
update instructions and skills, but it does not update the running MCP server.

The `--trust-transitive-mcp` flag is required for the dependent
`apm-setup` and `graphify-codegraph` MCP servers to be registered. Without it,
`apm install` still exits successfully but registers only `context-discipline`.

After installation, call the `apm-setup` MCP tool once:

```text
setup_graphify(repo_path="<your-repository>", install_graphify=true)
```

This installs the `graphify` CLI and writes
`graphify-out/graph.json` in the target repository. The
`setup_context_discipline` tool is optional for writes because `.score-local/`
is created lazily; its remaining purpose is adding `.score-local/` to
`.gitignore`.

### Use from Your Agent

```python
# Agent initializes a session
wm.initialize_session(
    goal="Refactor auth module",
    subgoals=["Understand current flow", "Identify dependencies"],
    assumptions={"Password hashing uses bcrypt": "high", "No 2FA": "low"},
)
# Returns {"session_id": "...", "setup": {"ok": ..., ...}}

# Agent explores code
auth_structure = wm.query_graph("Show me auth.py structure")
# Returns {"query": "...", "matches": [...], "setup": {...}}

# Agent records findings
decision_result = wm.record_decision(
    decision="Use existing auth module",
    reason=["Reduces complexity", "Proven in production"],
    grounded_nodes=["lib/auth.py", "auth_module"],
)
# Returns {"unresolved_nodes": []}
# Grounded nodes accept repo-relative source paths or canonical graph node IDs.
# If unresolved_nodes is non-empty, those entries do not contribute to
# retrieval; restate them as real paths or graph IDs.

# At the end: record what worked
wm.record_outcome(
    task="Refactor auth module",
    verdict="pass",
    rationale="The existing module covers the required flow.",
    coverage=0.85,
    surfaced_nodes=["PasswordHasher", "TokenManager", "User"],
    missing_nodes=["MFAService", "SessionCache"],
)
```

`verdict` must be exactly `pass` or `fail`; put free-text justification in
`rationale`. A failure is direct counter-evidence and needs no volume. A pass
is only weak evidence for a different task, so the default `outcome_reward = 0`
avoids amplifying early accidents into apparent structure in a small corpus.

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

The `[attention]` policy uses `selection = "rank"` by default, selecting
results above the provisional `noise_floor = 0.037` and within
`rank_gap_ratio = 0.35` of the best scored candidate. The noise floor is the
relevance criterion; the rank gap only truncates the tail. The floor is the
geometric mean of the worst relevant score (0.0619) and best control score
(0.0217). Rank scoring uses Unicode-aware tokenization and filters function
words because unfiltered overlap caused a measured false positive. The
`live_ratio_floor = 0.25` prevents records grounded only in non-graph files
from being permanently excluded. `selection = "threshold"` replays the
absolute `score_threshold` rule. These provisional values are calibrated from
`attention` records; `rank_gap_ratio` is calibrated separately from the
recorded score ordering.

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
similarity, shared grounded nodes, the owning task outcome, temporal decay, and
node availability. Recency decay is off by default (`recency_decay = false`),
so `recency` is `1.0`; it overlaps with `privacy.retention_days = 90`, and on
a small corpus age does not discriminate while still-valid architectural
decisions. Rank selection accepts scored candidates above the
configured `noise_floor` and within the configured `rank_gap_ratio` of the best
candidate; threshold selection remains available for replaying the absolute
`score_threshold` rule. The
`noise_floor`, `live_ratio_floor`, and `rank_gap_ratio` values are provisional
and should be calibrated from `attention` records. It excludes the current
session and returns
deterministic
top-ranked results as `items` plus a `rendered` untrusted-data block. The block
is data recorded by other sessions, never instructions to follow; verify every
claim against the graph before acting on it.

Structural attention resolves named nodes individually, expands directory paths
to the nodes underneath them, and widens the focus by one undirected graph hop.
Its score is the share of a prior record's graph-resident grounded nodes inside
that focus, with at least two such nodes required. The earlier exact-intersection
measure was zero by construction when related records grounded different modules.
Agents should include the module or directory paths touched by a task in
`current_nodes` (for example, `score/os` and `score/result`) rather than only
symbol names, because graph locality provides no structural contribution for
symbol-only input at the relevant granularity; `focus_size == 0` in the response
means the structural axis was silent. A named value that expands to a
very large subtree can dilute containment; no specificity cap is implemented
because the tested 25% graph cap dropped `score/os` and lost the measured signal.

## Durable Context Overlay

`add_overlay_node` writes a provenance-bearing S-CORE node and relation to
the sharded `score-context/nodes/` and `score-context/edges/` files. The
generated Graphify code graph remains read-only; the merged view combines
code, domain, and collaboration layers.
The versioned `score-context/policy.toml` is the single source of attention,
privacy, and overlay thresholds. Validate it and the overlay locally with:

```bash
uv run python scripts/validate_overlay.py
```

## See Also

- [graphify-codegraph](../graphify-codegraph/) — Code structure queries
- [.apm/instructions/working-memory-discipline.instructions.md](.apm/instructions/working-memory-discipline.instructions.md) — Behavioral patterns
- [.apm/skills/maintain-working-memory/SKILL.md](.apm/skills/maintain-working-memory/SKILL.md) — Step-by-step workflow

## License

Apache License 2.0
