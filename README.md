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

### 2. Add This Marketplace

From your project root:

```bash
apm marketplace add https://github.com/eclipse-score/mcp-servers
```

Or use the local path (for development):

```bash
apm marketplace add /path/to/mcp-servers
```

### 3. Install Packages

```bash
apm install graphify-codegraph@eclipse-score-packages context-discipline@eclipse-score-packages
apm compile -t copilot
```

(Replace `eclipse-score-packages` with your marketplace name if different. Check with: `apm marketplace list`)

### 4. Run Setup Wizards

After compilation, configure each package:

```bash
# From your project root (where apm.yml is)
./node_modules/.bin/do setup-graphify   # Generates code graph
./node_modules/.bin/do setup-context-discipline  # Creates working memory
```

Or copy setup scripts from this repo:

```bash
cp -r /path/to/mcp-servers/scripts ./scripts
./scripts/setup-graphify
./scripts/setup-context-discipline
```

### 5. Agent Uses It

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

**One-time setup:** `graphify .` in your repo  
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
apm install context-discipline
  ↓
  Fetches context-discipline + graphify-codegraph
  Merges instructions/skills for your agent
  
apm compile -t copilot
  ↓
  Generates .github/copilot-instructions.md
  
./do setup-graphify
  ↓
  Installs graphify CLI
  Generates graph.json in your repo
  
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

- **Interactive setup:** `./do setup-graphify --help`
- **Check setup status:** `./do setup-graphify --verify`
- **Package examples:** See each package's `README.md`
- **Create new packages:** See [AGENTS.md](AGENTS.md)
- **Contribute to this repo:** See [CONTRIBUTION.md](CONTRIBUTION.md)
