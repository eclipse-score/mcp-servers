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
description: Track working memory and decisions to produce observations for Phase 2 learning
---

# Working Memory Discipline

When solving a coding task, maintain explicit working memory and track decisions. This guidance feeds into the Phase 2 experience learning system (`libs/score-context`).

## What Gets Tracked

You track:
1. **The goal** — What are you trying to achieve?
2. **Assumptions** — What are you assuming about the codebase?
3. **Navigation path** — What did you query/read to understand the code?
4. **Decisions** — What did you decide and why?
5. **Outcome** — Did it work? (For Phase 2 feedback)

## Phase 2: From Working Memory to Experience Learning

Your working memory observations feed into:

```
.working-memory/
└── observations.jsonl  ← Your session observations (gitignored)
    ↓
libs/score-context/
  ├── ExperienceNode  ← Phase 2 learns from your routes
  └── experiences.jsonl  ← Global experience log
```

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

## Integration with Phase 2

In Phase 2 (when `libs/score-context` is fully integrated):

Your working memory observations map to `ExperienceNode`:

| Your Tracking | ExperienceNode Field |
|---|---|
| Navigation path | `route_edges`, `route_node_ids` |
| Surfaced nodes | `surfaced_node_ids` |
| Missed nodes | `missing_node_ids` |
| Outcome (pass/fail) | `verdict` |
| Coverage % | `coverage_ratio` |

**Result:** Your local observations feed global learning. Future sessions benefit from your routes.

## Local Artifacts (Gitignored)

Don't commit working memory:

```
.gitignore:
  .working-memory/
  *.session.json
  *.observation.jsonl
```

These are ephemeral scaffolding for your reasoning, not deliverables.

## Key Principles

1. **Explicit initialization** — Know your goal before exploring
2. **Verify before risky decisions** — Check assumptions against the code
3. **Track coverage** — What % of the scope did you understand?
4. **Record navigation** — What queries/reads led to understanding?
5. **Local → Global** — Phase 2 learns from your routes to improve future agents

## See Also

- [maintain-working-memory/SKILL.md](../skills/maintain-working-memory/SKILL.md) — Workflow guide
- `libs/score-context/schema/experience.py` — ExperienceNode format (Phase 2)
- `libs/score-context/harness/experience.py` — ExperiencePersistence (how observations feed learning)
