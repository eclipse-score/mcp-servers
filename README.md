# Eclipse S-CORE Agent Context Attention Layer

## The Problem

When an AI agent works on a complex task, it needs the right information—fast and accurately. Today, if you ask an agent to review a pull request or make a decision about architectural changes, it might:

- Spend time searching for relevant decisions, contracts, or requirements
- Miss critical context that changes the answer
- Lack guidance on which parts of a massive knowledge base matter for *this specific task*

This repo solves that with an **Attention Layer**: a system that learns what information matters for different tasks, and gets smarter over time.

## The Idea

Imagine a **knowledge graph** of everything in your organization: pull requests, architectural decisions (ADRs), contracts, requirements, test cases, etc. These are all connected—PR-42 affects Contract-A, which implements ADR-17.

**Phase 1 (current PR):** Given a task and a starting point (seed), the system intelligently **selects the most relevant nodes** from this graph using proven scoring rules (relation weights, freshness, centrality). This context is delivered to the agent.

**Phase 2 (proposed in this design):** Every time the system succeeds or fails at a task, it records the **exact path it took through the graph**. Over time, it learns which paths work best—similar to how ant colonies optimize routes. These learned "good paths" become feedback signals that improve future selections, without changing the core algorithm.

**No online learning. No magic. Git-native.** Every route, every decision, every learning update is captured as a file you can review in a pull request.

## How It Works

```
1. Task arrives          → "Find all contracts affected by PR-42"
2. Graph consulted       → "Start at PR-42, follow edges..."
3. Context selected      → "Here are Contracts A, B, and ADR-17"
4. Agent acts on it      → Task completes (success or failure)
5. Route recorded        → "We traversed: PR-42 → Contract-A → ADR-17"
6. Learning signal sent  → "That path worked! Use it again next time"
7. Graph updated         → Future tasks benefit from this experience
```

See [EXPERIENCE_LEARNING_DESIGN.md](./EXPERIENCE_LEARNING_DESIGN.md) for the full technical proposal.

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
| **Attention Weight** | A confidence boost/dampen applied to edges based on historical success/failure |

---

## Quick Start

```shell
# Install dependencies
uv sync

# Run quality checks
uv run ruff check .
uv run ruff format --check .
uv run pyright

# Run tests (Lane A deterministic evaluation)
uv run pytest

# See test coverage
uv run pytest --cov=score_context
```

---

## How APM Packages Work

APM primitives live under each package's `.apm/<type>/` tree. To add a package, copy `packages/_template`, edit its `apm.yml`, and add primitives under `.apm/<type>/`.

MCP servers are declared in a package's `apm.yml` under `dependencies.mcp:`; they are not a separate directory. The `get_context` MCP server is planned for a later phase.

---

## Phase Timeline

- **Phase 0 (done):** Core schema and graph engine, no APM/MCP yet
- **Phase 1 (current PR):** Context selection harness with deterministic evaluation (Lane A)
- **Phase 2 (proposed):** Experience learning—routes recorded, confidence signals updated, Git-native persistence
- **Phase 3 (future):** Meta-harness for higher-level routing policies learned from experience data
