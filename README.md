# Eclipse S-CORE APM Monorepo

Local-only agent packages for code understanding, working memory...

## What You Get

Ready-to-use packages for your AI agent:

| Package | What It Does |
|---------|---|
| **graphify-codegraph** | Query code structure (what classes/functions exist, how they're connected) |
| **context-discipline** | Working memory + outcome recording (agent tracks decisions and learns from past work) |
| **sdlc-harness** | Traceable SDLC lifecycle, task evidence, and loopback logging |

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
apm compile -t copilot --force-instructions
apm approve --pending
```

Use `--force-instructions` so APM writes an always-on `AGENTS.md`; without it,
the guidance remains in individual instruction files and is loaded only at the
agent's discretion.

Approval is optional: it enables executable hooks for Copilot, Claude, Cursor,
Gemini, Codex, Windsurf, and Kiro; unsupported targets such as opencode and
grok-build skip hooks silently. The core package works fully without approval.
These observations come from APM 0.26: `apm approve --pending` prints the
exact key to approve, and that key is what you pass to `apm approve`. However,
APM 0.26 does not discover nested virtual marketplace packages such as
`apm_modules/<owner>/<repo>/packages/<pkg>` in the `apm approve` scanner at
all; the observed installed path was
`apm_modules/eclipse-score/mcp-servers/packages/context-discipline`. For that
install form, `--pending`, `--list`, `--all`, and every package-specific
invocation report the package as absent, so approval through `apm approve` is
not available. Use an explicit project `executables.allow` entry with the
verified dependency key instead:

```yaml
executables:
  allow:
    github.com/eclipse-score/mcp-servers/packages/context-discipline#metamodel_flow:
      hooks: true
      mcp: true
```

After that entry is added, the next install deploys the hooks
(`exec_status: deployed`). We also measured APM 0.30.0 in a fresh pinned
marketplace consumer: its `--pending` scanner found the nested packages and
printed version keys, but approving those printed keys and reinstalling still
left the executable packages gated, so that output is not documented as a
working deployment flow here. The identity mismatch is that APM 0.30's
approval scanner emits `#<version>` identities while its install-time gate
expects `#<ref>`. `apm approve --recommended` only acts on recommendations
from an active org policy.

Installing `context-discipline` also installs its transitive dependencies:
`graphify-codegraph` and `apm-setup`.

**Option B: From a local path** (development)

```bash
apm install /path/to/mcp-servers/packages/context-discipline --target copilot --trust-transitive-mcp
apm compile -t copilot --force-instructions
apm approve --pending
```

Installing `context-discipline` also installs its transitive dependencies:
`graphify-codegraph` and `apm-setup`.

**Option C: From a cloned checkout**

```bash
git clone https://github.com/eclipse-score/mcp-servers
cd mcp-servers
apm install ./packages/context-discipline --target copilot --trust-transitive-mcp
apm compile -t copilot --force-instructions
apm approve --pending
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

### sdlc-harness

Traceable SDLC lifecycle, task evidence, and loopback logging for AI agents.

**MCP tools:**
- `bootstrap_sdlc_issue()` - Initialize structured stage artifacts from a requirement
- `write_stage_artifact()` - Write numbered requirement, specification, architecture, plan, or task
- `assess_sdlc_issue()` - Assess stage artifacts for completeness and evidence
- `check_stage_completeness()` - Verify prerequisite artifacts for a stage
- `record_implementation_evidence()` - Record task test outcomes and status
- `assess_implementation_progress()` - Report task completion and evidence summary
- `record_loopback()` - Record discovered gaps and mark affected artifacts for review

See [packages/sdlc-harness/README.md](packages/sdlc-harness/README.md) for details.

---

## How It Works

```
apm install context-discipline@eclipse-score-apm-marketplace --trust-transitive-mcp
  ↓
  Installs context-discipline plus graphify-codegraph and apm-setup

apm compile -t copilot --force-instructions
  ↓
  Generates AGENTS.md
  
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

## Releasing

MCP sources are pinned to a commit SHA with the version as a comment:

```yaml
- git+https://github.com/eclipse-score/mcp-servers@<sha>#subdirectory=packages/apm-setup # v0.1.0
```

1. Open and merge one PR with your code, documentation, or generated graph changes.
   No separate release PR or manual pin update is required.
2. The `Release` workflow pins MCP sources to that merged commit and prepares the
   next patch version automatically. To request a higher minor or major version,
   update the package versions in the same PR.
3. The workflow tests the release, creates a metadata commit reachable only from
   its version tag, and pushes that tag. It never pushes changes to `main` and
   does not need a branch-protection bypass or an Otterdog policy change.
4. It smoke-tests the exact shipped MCP pins, publishes devcontainer features
   from the same release commit, and then publishes the GitHub release.

Use the version tag when installing the released marketplace. Versions and pins
on `main` are development metadata; release metadata lives on the tags.
Rerunning a workflow for the same merged commit reuses its tag and retries
publication rather than allocating another version or skipping failed features.
`python3 scripts/prepare_release.py --plan` prints the planned version as JSON.

## More Information

- **Setup MCP:** See [packages/apm-setup/README.md](packages/apm-setup/README.md)
- **Package examples:** See each package's `README.md`
- **Create new packages:** See [AGENTS.md](AGENTS.md)
- **Contribute to this repo:** See [CONTRIBUTION.md](CONTRIBUTION.md)
