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
name: working-memory-discipline
description: Track working memory, decisions, and intersession context
---

# Working Memory Discipline

When solving a coding task, maintain explicit working memory and track decisions. This guidance feeds the local session log and durable context overlay.

## What Gets Tracked

You track:
1. **The goal** — What are you trying to achieve?
2. **Assumptions** — What are you assuming about the codebase?
3. **Navigation path** — What did you query/read to understand the code?
4. **Decisions** — What did you decide and why?
5. **Outcome** — Did it work?

## Intersession Context

Session records are appended to `.score-local/sessions.jsonl`:

```
.score-local/
└── sessions.jsonl
```

Reasoning records can include grounded node IDs. Later sessions can call
`get_prior_context(task_text, current_nodes)` to retrieve related reasoning.

## Pattern: Initialize → Navigate → Decide → Record

### 1. Initialize (Before coding)

Write down explicitly:
```
Goal: "Make authenticate() async without breaking callers"
Subgoals: 
  - Understand current implementation
  - Find all call sites
  - Design async version
  - Update callers

Assumptions:
  - auth.py is only module with authenticate()  [confidence: high]
  - No external packages import our auth       [confidence: medium]
```

### 2. Navigate (Understanding phase)

Every query/file read contributes to your route:

```
Query: "All functions in lib/auth.py"
Finding: "4 functions: authenticate, verify_token, refresh, logout"
Confidence gain: high (direct inspection)

Query: "All imports of authenticate()"
Finding: "3 files import it from auth.py"
Confidence gain: high (graph verified our assumption)
```

Track what you surfaced vs. what you missed:
- ✅ Surfaced: handlers.py, cli.py (code review)
- ❌ Missing: scripts.py (discovered later)

### 3. Decide (Before implementing)

Before risky changes, verify assumptions:

```
Unverified assumptions:
  - "No external packages import our auth" [confidence: medium]
  
Action: Check all .py files for external imports
Result: Verified - only internal usage

Decision: Refactor auth.py first
Reasons:
  - Isolated testing possible
  - Only 3 small caller changes
Reversible: yes (can revert to sync if needed)
```

### 4. Record Outcome

After implementation:

```
Task: "Refactor auth to async"
Route taken: [understand] → [verify] → [implement] → [test]
Verdict: pass/fail
Coverage: 95% (understood 95% of scope)
Missing nodes: [any edge cases not covered]
```

## When to Use This Pattern

- Long multi-turn coding sessions
- Uncertain codebases (new to you)
- Risky refactorings (affects many call sites)
- Complex decisions (trade-offs between approaches)

## When NOT to Use

- Simple one-file fixes
- Well-known codebase (you built it)
- Low-risk changes (add one function)

## Durable Context Overlay

Use `add_overlay_node` when a decision, requirement, contract, issue, or pull
request should survive Graphify regeneration. Overlay nodes and edges are
provenance-bearing and stored as shards in `score-context/nodes/` and
`score-context/edges/`. The versioned thresholds are in
`score-context/policy.toml`; validate them locally with
`uv run python scripts/validate_overlay.py`.

## Local Artifacts (Gitignored)

Don't commit working memory:

```
.gitignore:
  .score-local/
```

These are ephemeral scaffolding for your reasoning, not deliverables.

## Key Principles

1. **Explicit initialization** — Know your goal before exploring
2. **Verify before risky decisions** — Check assumptions against the code
3. **Track coverage** — What % of the scope did you understand?
4. **Record navigation** — What queries/reads led to understanding?
5. **Local and durable** — Keep collaboration records local and durable domain
   context in the overlay

## See Also

- [maintain-working-memory/SKILL.md](../skills/maintain-working-memory/SKILL.md) — Workflow guide
- `.score-local/sessions.jsonl` — Append-only collaboration records
- `score-context/meta.json` — Overlay version metadata
- `score-context/policy.toml` — Versioned attention/privacy/overlay thresholds
- `score-context/nodes/` — One provenance-bearing node per JSON shard
- `score-context/edges/` — One provenance-bearing edge per hash-named shard
