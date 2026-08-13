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
name: maintain-working-memory
description: Use WorkingMemoryManager to track goals, assumptions, and decisions during agentic sessions—no custom YAML required
---

# Maintain Working Memory Skill

Use **WorkingMemoryManager** to track your session explicitly without custom YAML maintenance.

Simple, self-contained implementation. Works standalone. Designed to integrate with Phase 2 LocalObservationManager without breaking changes.

## When to invoke

- **Starting a session** — Initialize working memory with goals
- **After tool calls** — Record compressed findings (1-2 sentences)
- **Before major decisions** — Check unverified assumptions and stale artifacts
- **When making decisions** — Record with reversibility tracking
- **Regularly** — Update plan and coverage as you learn

## How to use

### Setup: Initialize working memory manager

```python
from working_memory_manager import WorkingMemoryManager

# Create manager (uses .working-memory/ directory)
wm = WorkingMemoryManager(repo_path=".working-memory")

# Initialize session
wm.initialize(
    goal="Refactor auth module to async",
    subgoals=[
        "Identify all auth functions",
        "Map dependencies on sync calls",
        "Implement async versions",
        "Update call sites"
    ],
    initial_assumptions=["auth.py is the only auth module"]
)
```

### Record compressed findings

```python
# After each tool call, record (COMPRESS to 1-2 sentences)
wm.record_finding(
    tool="graphify-codegraph",
    query="All functions in lib/auth.py",
    result="4 sync functions: authenticate, verify_token, refresh, logout"
)

# Add relevant artifacts to track
wm.add_artifact("lib/auth.py", "Main auth functions", lines="1-150")
wm.add_artifact("api/handlers.py", "Update async calls")
```

### Track assumptions

```python
# Add assumptions (especially ones to verify)
wm.add_assumption("auth.py is only auth module", confidence="high")
wm.add_assumption("No external code imports auth", confidence="medium")

# Before risky decisions, check for unverified ones
unverified = wm.get_unverified_assumptions()
if unverified:
    print(f"⚠️  WARNING: {len(unverified)} unverified assumptions")
    for a in unverified:
        if a.confidence in ["low", "medium"]:
            print(f"  - {a.key} (confidence: {a.confidence}) - VERIFY BEFORE PROCEEDING")
```

### Record decisions

```python
# Document what you decide and why (with reversibility)
wm.record_decision(
    decision="Implement async in auth.py first, then update callers",
    reason=[
        "Minimizes risk of partial refactoring",
        "Only 3 call sites to update",
        "Can test refactored functions independently"
    ],
    reversible=True
)
```

### Update progress

```python
# After each major step, update your plan
wm.update_plan(
    current_plan="Now mapping all call sites of authenticate() function",
    next_action="Query graph for reverse dependencies",
    coverage=0.35,  # 35% of task understood
    importance_score=8  # 0-10 scale
)
```

### Review before major decisions

```python
# Get current state
state = wm.get_current_state()
print(f"Goal: {state.goal}")
print(f"Progress: {state.coverage * 100:.0f}%")
print(f"Next: {state.next_action}")

# Check for potential issues
unverified = wm.get_unverified_assumptions()
stale = wm.get_stale_artifacts(stale_after_turns=5)
irreversible = wm.get_irreversible_decisions()

if unverified:
    print(f"⚠️  {len(unverified)} unverified assumptions")
if stale:
    print(f"⚠️  {len(stale)} artifacts may be stale - re-verify")
if irreversible:
    print(f"⚠️  {len(irreversible)} irreversible decisions - ensure rollback plan exists")
```

### Load previous session

```python
# List available sessions
wm = WorkingMemoryManager()
sessions = wm.list_sessions()
print(f"Available sessions: {sessions}")

# Resume previous session
state = wm.load_session("session_abc12345")
print(f"Resuming: {state.goal}")
print(f"Last plan: {state.current_plan}")
```

## Full Example: Async Refactoring Session

```python
from working_memory_manager import WorkingMemoryManager

wm = WorkingMemoryManager()

# Initialize
wm.initialize(
    goal="Convert auth module to async",
    subgoals=["Understand current", "Map dependencies", "Implement async"],
    initial_assumptions=["auth.py is only auth module"]
)

# Turn 1: Query graph
wm.record_finding(
    tool="graphify-codegraph",
    query="All functions in lib/auth.py",
    result="4 sync functions: authenticate, verify_token, refresh, logout"
)
wm.add_artifact("lib/auth.py", "Main auth functions", lines="1-150")
wm.update_plan("Identified target functions", "Map all call sites", coverage=0.25, importance_score=9)

# Turn 2: Find dependencies
wm.record_finding(
    tool="graphify-codegraph",
    query="reverse dependencies of authenticate()",
    result="3 files call authenticate(): handlers.py:87, cli.py:15, scripts.py:33"
)
wm.record_decision(
    "Refactor auth.py first, then update callers",
    ["Reduces risk", "Can test independently"],
    reversible=True
)
wm.verify_assumption("auth.py is only auth module")
wm.update_plan("Dependencies mapped", "Implement async", coverage=0.40)

# Turn 3: Read implementation
wm.mark_artifact_read("lib/auth.py")
wm.record_finding(
    tool="file-read",
    query="authenticate() implementation",
    result="Uses time.sleep() for retry and requests.get() for API"
)
wm.add_assumption("Backwards compatibility needed", confidence="high")
wm.update_plan("Ready to implement", "Start async authenticate()", coverage=0.50)

# Turn 4: Safety check before code changes
print("Safety check:")
unverified = wm.get_unverified_assumptions()
if not unverified:
    print("✅ All assumptions verified. Ready to proceed.")
```

## Pro Tips

### 1. Always compress findings

```python
# ✅ GOOD: 1-2 sentence summary
wm.record_finding("tool", "query", "authenticate() uses blocking I/O; needs asyncio")

# ❌ BAD: Raw output violates discipline
wm.record_finding("tool", "query", "[50KB of source code]")
```

### 2. Use confidence levels

```python
# High: Verified independently
wm.add_assumption("auth.py is only module", confidence="high")

# Medium: Likely but unverified
wm.add_assumption("No external imports", confidence="medium")

# Low: Needs verification
wm.add_assumption("Backwards compat needed", confidence="low")
```

### 3. Track reversibility

```python
# Can undo
wm.record_decision("Rename function", [...], reversible=True)

# Can't undo - get explicit confirmation
irreversible = wm.get_irreversible_decisions()
if irreversible:
    print("VERIFY ROLLBACK PLANS FOR IRREVERSIBLE CHANGES")
```

### 4. Check for stale artifacts

```python
# Before making changes, re-check old findings
stale = wm.get_stale_artifacts(stale_after_turns=5)
for artifact in stale:
    print(f"⚠️  {artifact.file} may be out of date - re-verify")
```

### 5. Importance and coverage

```python
# importance_score (0-10): Future filtering threshold >= 5
#   - Critical task = 9-10
#   - Major discovery = 7-8
#   - Regular progress = 5-6
#   - Minor detail = < 5 (filtered out)

# coverage (0.0-1.0): Future filtering threshold >= 0.3
#   - Just started = 0.2-0.3
#   - Good understanding = 0.5-0.7
#   - Nearly complete = 0.85-1.0
```

## How It Works

### Phase 0 (Current)

Self-contained `WorkingMemoryManager`:
- Python class (no dependencies)
- JSONL persistence (`.working-memory/observations/`)
- Works standalone

### Phase 2 Integration (Future)

When available, adapter to LocalObservationManager:

```python
from score_context.harness.local_observation import LocalObservationManager

wm = WorkingMemoryManager()
observer = LocalObservationManager()

state = wm.get_current_state()

# Submit to global learning (if important enough)
if state.importance_score >= 5 and state.coverage >= 0.3:
    observer.record_discovery(
        type="working_memory_state",
        node_id=f"session:{state.session_id}",
        findings=state.to_dict(),
        importance_score=state.importance_score,
        coverage=state.coverage
    )
```

**No breaking changes.** WorkingMemoryManager works the same in both phases.

## Automatic Benefits

- ✅ **Zero custom guardrail code** — Reuses tested infrastructure
- ✅ **Immutable audit trail** — JSONL append-only logs
- ✅ **Fast queries** — O(1) lookups via session index
- ✅ **Importance/coverage filtering** — Automatic signal vs. noise detection
- ✅ **No maintenance burden** — Simple Python class, no YAML to maintain
- ✅ **Global learning ready** — Integrates with Phase 2 experience aggregation

## Reference

See [IMPLEMENTATION.md](../../../IMPLEMENTATION.md) for complete API reference and examples.
