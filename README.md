# Eclipse S-CORE Agent Context Attention Layer

## The Problem

When an AI agent works on a complex task, it needs the right information—fast and accurately. Today, if you ask an agent to review a pull request or make a decision about architectural changes, it might:

- Spend time searching for relevant decisions, contracts, or requirements
- Miss critical context that changes the answer
- Lack guidance on which parts of a massive knowledge base matter for *this specific task*

This repo solves that with an **Attention Layer**: a system that learns what information matters for different tasks, and gets smarter over time.

## The Idea

Imagine a **knowledge graph** of everything in your organization: pull requests, architectural decisions (ADRs), contracts, requirements, test cases, etc. These are all connected—PR-42 affects Contract-A, which implements ADR-17.

**Phase 1:** Given a task and a starting point (seed), the system deterministically selects the most relevant nodes from this graph.

**Phase 2:** Each run appends one experience to `harness/artifacts/experiences.jsonl`.
`score-ctx aggregate` derives one deterministic `weights.json`; learned keys are
edge classes `(relation, source_type, target_type)`, so they generalize across
repositories. All scoring and learning knobs live in `harness/policy.yml`.

## How It Works

```
1. Task arrives          → "Find all contracts affected by PR-42"
2. Graph consulted       → "Start at PR-42, follow edges..."
3. Context selected      → "Here are Contracts A, B, and ADR-17"
4. Agent acts on it      → Task completes (success or failure)
5. Route recorded        → "We traversed: PR-42 → Contract-A → ADR-17"
6. Aggregate experiences → "Class weights are derived deterministically"
7. Future selection      → "The scorer reads only weights.json"
```

---

## Repository Structure

This is a Python/uv monorepo using Microsoft's APM **monorepo-hybrid** shape:

- **`libs/score-context`** — The core engine: graph storage, deterministic ranking, harness evaluation
- **`packages/context`** — The APM package for the attention layer
- **`packages/_template`** — Skeleton for adding new packages
- **`harness/`** — Testing and evaluation artifacts
- **`apm.yml`** — Marketplace manifest

### Key Concepts

| Term | What It Is |
|------|-----------|
| **Context Graph** | A typed, versioned knowledge structure with nodes (PRs, ADRs, Contracts, etc.) and edges (affects, implements, depends_on, etc.) |
| **ContextHarness** | The evaluator that selects context for a task and checks if it contains everything the task needs |
| **Route** | The actual path through the graph that the scoring algorithm took to reach selected nodes |
| **Experience** | A recorded route + outcome (pass/fail) that becomes a learning signal |
| **Attention Weight** | A class-level boost/dampen from historical success/failure |

---

## Quick Start

```shell
uv sync

uv run score-ctx demo
uv run score-ctx run --task harness/spec/task_001_contract_change.json
uv run score-ctx aggregate
```

---

## How APM Packages Work

APM primitives live under each package's `.apm/<type>/` tree. To add a package, copy `packages/_template`, edit its `apm.yml`, and add primitives under `.apm/<type>/`.

MCP servers are declared in a package's `apm.yml` under `dependencies.mcp:`; they are not a separate directory. The `get_context` MCP server is planned for a later phase.

---

## Phase Timeline

- **Phase 0 (done):** Core schema and graph engine, no APM/MCP yet
- **Phase 1:** Context selection harness with deterministic evaluation (Lane A)
- **Phase 2:** Append-only experience learning with class-level derived weights
- **Phase 3 (future):** Meta-harness for higher-level routing policies learned from experience data
