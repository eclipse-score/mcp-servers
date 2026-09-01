# Eclipse S-CORE APM Monorepo

Local-only agent packages for code understanding, working memory...

## What You Get

Two ready-to-use packages for your AI agent:

| Package | What It Does |
|---------|---|
| **graphify-codegraph** | Query code structure (what classes/functions exist, how they're connected) |
| **context-discipline** | Working memory + outcome recording (agent tracks decisions and learns from past work) |

**Local only:** Everything runs in your project. Observations stored in `.score-local/` (not committed).

## Quick Start

### 1. Install APM CLI

```bash
# macOS/Linux/Windows: https://github.com/microsoft/apm#installation
brew install microsoft/apm/apm  # or: pip install apm-cli
```

### 2. Install Packages

**Option A: From the marketplace**

The marketplace manifest is generated from `apm.yml` during packaging and
committed at `.claude-plugin/marketplace.json`. From this repository, run:

```bash
apm pack
```

Then, from your project root:

```bash
apm marketplace add https://github.com/eclipse-score/mcp-servers
apm install context-discipline@eclipse-score-apm-marketplace --target copilot --trust-transitive-mcp
apm compile -t copilot
```

Installing `context-discipline` also installs its transitive dependencies:
`graphify-codegraph` and `apm-setup`.

**Option B: From a local path** (development)

```bash
apm install /path/to/mcp-servers/packages/context-discipline --target copilot --trust-transitive-mcp
apm compile -t copilot
```

Installing `context-discipline` also installs its transitive dependencies:
`graphify-codegraph` and `apm-setup`.

**Option C: From a cloned checkout**

```bash
git clone https://github.com/eclipse-score/mcp-servers
cd mcp-servers
apm install ./packages/context-discipline --target copilot --trust-transitive-mcp
apm compile -t copilot
```

Installing `context-discipline` also installs its transitive dependencies:
`graphify-codegraph` and `apm-setup`.

### 3. Initialize Repository Setup Through MCP

After registering the server, call these tools for the target repository:

```text
verify_setup(repo_path)
setup_graphify(repo_path)
setup_context_discipline(repo_path)
```

APM installation registers the declared MCP server, but does not execute
repository setup automatically. Repository setup is explicit and performed by
the `apm-setup` MCP server.

### 4. Agent Uses It

Once configured, your agent can call MCP tools:

```python
# Working memory
wm.initialize_session(goal="...", subgoals=[...])
wm.query_graph("Show auth functions")
wm.record_decision(decision="...", reason=[...])
wm.record_outcome(task="...", verdict="pass", coverage=0.85)
```

Results: `.score-local/observations.jsonl` (local only, not committed).

---

## Documentation

- **For users:** You're reading it. More examples in each package's `README.md`.
- **For agents:** See [AGENTS.md](AGENTS.md) to create new packages.
- **For contributors:** See [CONTRIBUTION.md](CONTRIBUTION.md).

---

## Packages at a Glance

### graphify-codegraph

Wraps [Graphify Labs graphify](https://github.com/Graphify-Labs/graphify) — deterministic AST parsing, no LLMs.

**Generates:** `graphify-out/graph.json` (code structure), `graph.html` (interactive explorer)

**One-time setup:** `setup_graphify(repo_path)` through the `apm-setup` MCP  
**Runtime:** Agents query via MCP (no re-parsing)

See [packages/graphify-codegraph/README.md](packages/graphify-codegraph/README.md) for details.

### context-discipline

Working memory system + local learning.

**MCP tools:**
- `initialize_session()` — Start a session with goal + subgoals + assumptions
- `query_graph()` — Ask about code structure
- `record_decision()` — Track reasoning
- `record_outcome()` — Record results (appends to `.score-local/observations.jsonl`)
- `get_working_memory()` — Retrieve session memory
- `get_unverified_assumptions()` — Check uncertain assumptions

See [packages/context-discipline/README.md](packages/context-discipline/README.md) for details.

---

## How It Works

```
apm install context-discipline@eclipse-score-apm-marketplace --trust-transitive-mcp
  ↓
  Installs context-discipline plus graphify-codegraph and apm-setup

apm compile -t copilot
  ↓
  Generates .github/copilot-instructions.md
  
Agent runs
  ↓
  Calls MCP tools (initialize_session, query_graph, etc.)
  MCP servers execute
  Observations accumulate in .score-local/
```

For deeper details on APM concepts, see [Microsoft APM docs](https://github.com/microsoft/apm).

---

## Local Learning Loop

```
Session 1: query_graph() + record_outcome()
Session 2: query_graph() + record_outcome()
Session 3: query_graph() + record_outcome()
   ↓ (observations.jsonl grows)
Agent patterns emerge
   ↓
Result: Fewer tokens, faster time-to-solution (all local)
```

---

## More Information

- **Setup MCP:** See [packages/apm-setup/README.md](packages/apm-setup/README.md)
- **Package examples:** See each package's `README.md`
- **Create new packages:** See [AGENTS.md](AGENTS.md)
- **Contribute to this repo:** See [CONTRIBUTION.md](CONTRIBUTION.md)
