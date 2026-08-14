# AGENTS.md: Guide for Creating APM Packages

This guide is for AI agents contributing to the mcp-servers monorepo.

## What This Repository Is

**Eclipse S-CORE APM Monorepo** — a collection of APM (Agent Package Manager) packages providing **local-only code understanding and working memory** for AI agents.

**Key principles:**
- ✅ No cloud dependencies
- ✅ No vendor lock-in
- ✅ 100% deterministic
- ✅ Open source (Apache 2.0)
- ✅ Runs locally in every project

## Repository Structure

```
mcp-servers/
├── apm.yml                    # Root marketplace manifest
├── README.md                  # User-facing documentation
├── AGENTS.md                  # This file: agent contributor guide
├── .gitignore                 # Git exclusions (.score-local/, graphify-out/, etc.)
│
├── packages/
│   ├── _template/             # Copy this to create new packages
│   ├── graphify-codegraph/    # ✅ Complete: code graph queries
│   ├── context-discipline/    # ✅ Complete: working memory + local learning
│   └── context/               # Legacy reference
│
├── scripts/
│   ├── do                     # Task runner: ./do <task>
│   ├── setup-common.sh        # Shared utilities (colors, prompts, validation)
│   └── setup-graphify         # Interactive wizard for graphify setup
│
└── .score-local/              # 🔓 Local (not committed): observations.jsonl
    └── observations.jsonl     # Accumulated local learning data
```

## What Is an APM Package?

An APM package is a **self-contained, installable unit** containing:

1. **Metadata** (`apm.yml`)
   - Name, version, license, description
   - Dependencies (other APM packages)
   - MCP server declarations (if any)

2. **Behavioral Guidance** (`.apm/instructions/`)
   - How the agent should think about this domain
   - Best practices
   - Example patterns

3. **Workflow Skills** (`.apm/skills/`)
   - VSCode integration patterns
   - Step-by-step workflows
   - Tool-specific guidance

4. **MCP Server** (optional)
   - Python/Node.js executable declared in `apm.yml` under `dependencies.mcp:`
   - Implements functions agents can call

### Example: graphify-codegraph

```
packages/graphify-codegraph/
├── apm.yml                                 # Declares MCP server
├── README.md                               # User documentation
├── mcp.yml                                 # MCP server config
│
├── src/
│   ├── __init__.py                         # Module marker
│   └── serve.py                            # MCP server launcher
│
└── .apm/
    ├── instructions/
    │   └── repository-graph-navigation.instructions.md
    └── skills/
        └── map-repository-graph/SKILL.md
```

## Creating a New APM Package

### Step 1: Copy the Template

```bash
cp -r packages/_template packages/your-package-name
```

### Step 2: Edit the Manifest (`apm.yml`)

```yaml
name: your-package-name
version: 0.1.0
description: One-line description of what this package does
license: Apache-2.0

targets:
  - copilot
  - claude
  - cursor

# If you're wrapping an external tool or service
external_dependencies:
  - name: some-cli-tool
    install: uv tool install package-name

# If you have an MCP server
dependencies:
  mcp:
    - name: your-package-name
      type: stdio
      command: python -m your_package_name.src.serve
      env: {}
```

### Step 3: Add Behavioral Guidance

Create `.apm/instructions/<topic>.instructions.md`:

```markdown
# Your Topic Instructions

## When to Use
Explain when an agent should apply this guidance.

## Key Patterns
List 3-5 patterns the agent should follow.

## Example Workflow
1. Agent does X
2. Agent calls MCP tool Y
3. Agent records outcome Z

## Integration Points
How does this connect to other packages?
```

### Step 4: Add Skills (VSCode Workflows)

Create `.apm/skills/<skill-name>/SKILL.md`:

```markdown
# <Skill Name>

## Prerequisites
- VSCode with Python extension
- MCP server running

## Workflow
1. User opens command palette
2. Runs: "Your Skill: Do Something"
3. Shows results in panel

## Example
[Show code or interaction example]
```

### Step 5: Implement MCP Server (if needed)

Create `src/serve.py`:

```python
#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

import sys
import json

def main():
    """MCP server entry point."""
    # Read from stdin, write to stdout
    # Implement your MCP protocol here
    pass

if __name__ == "__main__":
    main()
```

Create `mcp.yml`:

```yaml
name: your-package-name
description: What this MCP server does
version: 0.1.0

tools:
  - name: tool_function_name
    description: What the tool does
    inputSchema:
      type: object
      properties:
        arg_name:
          type: string
          description: What this arg is
      required: [arg_name]
```

### Step 6: Register in Root Marketplace

Edit root `apm.yml`:

```yaml
marketplace:
  packages:
    - name: your-package-name
      source: ./packages/your-package-name
      version: 0.1.0
```

### Step 7: Add License Headers

Every new file must have:

```python
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
# ... rest of file
```

### Step 8: Test Your Package

```bash
# Validate structure
apm pack --offline --json
apm marketplace check --offline

# Test locally
cd packages/your-package-name
python -m your_package_name.src.serve  # If you have MCP

# Verify installed tools
apm compile -t copilot
cat .github/copilot-instructions.md  # Should include your guidance
```

## Two Existing Packages: Reference Implementations

### 1. graphify-codegraph

**What it does:** Queries code structure using deterministic AST parsing

**Key files:**
- `apm.yml` — Declares external_dependency (graphify CLI), MCP server
- `src/serve.py` — Thin wrapper: `subprocess.run([...graphify.serve])`
- `.apm/instructions/repository-graph-navigation.instructions.md` — Usage patterns
- `.apm/skills/map-repository-graph/SKILL.md` — VSCode integration

**MCP tools:** (delegated to graphify CLI)
- None direct (MCP server launches graphify's built-in MCP)

**Setup:** `./do setup-graphify` installs CLI + generates graph.json

### 2. context-discipline

**What it does:** Working memory management + local outcome recording

**Key files:**
- `apm.yml` — Depends on graphify-codegraph
- `mcp.yml` — Declares 6 tools
- `src/context_discipline_mcp.py` — Full implementation (~220 lines)
- `.apm/instructions/working-memory-discipline.instructions.md` — Behavioral guidance
- `.apm/skills/maintain-working-memory/SKILL.md` — VSCode workflows

**MCP tools:**
1. `initialize_session(goal, subgoals, assumptions)` → Creates session
2. `query_graph(query)` → Delegates to graphify-codegraph
3. `record_decision(decision, reason[], reversible)` → Tracks reasoning
4. `record_outcome(task, verdict, coverage, nodes, missing)` → Records for learning
5. `get_working_memory()` → Returns session state
6. `get_unverified_assumptions()` → Returns uncertain assumptions

**Output:** `.score-local/observations.jsonl` (append-only JSONL, local only)

## Patterns to Follow

### Pattern 1: External Tool Wrapping (graphify-codegraph)

When wrapping an external CLI tool:

```python
# src/serve.py
import subprocess, sys

def main():
    subprocess.run([sys.executable, "-m", "<external>.serve"], check=True)
```

**Why:** Let the external tool handle MCP; you just proxy it.

### Pattern 2: Full MCP Implementation (context-discipline)

When building your own MCP server:

```python
# src/your_package.py
from dataclasses import dataclass

@dataclass
class YourData:
    field: str

class YourMCP:
    def tool_name(self, arg):
        # Implement tool logic
        return result
```

**Why:** Use dataclasses for JSON serialization; keep logic in class methods.

### Pattern 3: Local Storage (context-discipline)

For local-only learning/state:

```python
# Store as JSONL (append-only)
import json
from pathlib import Path

obs_file = Path(".score-local/observations.jsonl")
obs_file.parent.mkdir(exist_ok=True)

with open(obs_file, "a") as f:
    f.write(json.dumps(asdict(observation)) + "\n")
```

**Why:** JSONL is append-only, queryable, and git-ignored. Perfect for ephemeral data.

### Pattern 4: Setup Wizard (scripts/setup-*)

For interactive first-time setup:

```bash
#!/bin/bash
source "${script_dir}/setup-common.sh"

main() {
    case "${1:-}" in
        --verify)
            check_status
            ;;
        *)
            # Interactive flow
            info "Your Package Setup Wizard"
            confirm "Do step 1?" && run_step_1
            confirm "Do step 2?" && run_step_2
            success "Setup complete!"
            ;;
    esac
}

main "$@"
```

**Why:** Makes onboarding seamless; `./do setup-your-pkg` guides users interactively.

### Pattern 5: Documentation Structure

Every package needs:

1. **README.md** — User-facing: problem, solution, quick start
2. **.apm/instructions/** — Behavioral guidance: when/how to use
3. **.apm/skills/** — VSCode workflows: step-by-step
4. **apm.yml** — Package metadata and dependencies
5. **mcp.yml** — MCP server declarations (if applicable)

## Testing Your Package

### Unit Tests

```python
# tests/test_your_module.py
import sys
sys.path.insert(0, "src")

from your_module import YourClass

def test_tool():
    obj = YourClass()
    result = obj.tool_name(arg="test")
    assert result is not None
```

Run: `python tests/test_your_module.py`

### Integration Tests

Test with actual MCP server:

```bash
cd packages/your-package-name
python -m your_package_name.src.serve &
MCP_PID=$!

# Send MCP calls to it
sleep 1
kill $MCP_PID
```

### APM Validation

```bash
apm pack --offline --json       # Package structure valid?
apm marketplace check --offline # Manifest metadata valid?
```

## Common Mistakes to Avoid

| Mistake | ✅ Do This Instead |
|---------|---|
| Cloud dependencies | Use only local/offline tools. Store state in `.score-local/` |
| Hard-coded paths | Use `Path.cwd()` or relative paths; make it portable |
| Complex MCP tools | Keep tool logic simple; delegate heavy lifting to library code |
| Missing headers | Add SPDX headers to every file (Apache-2.0) |
| Undocumented APIs | Every MCP tool needs description + example in README |
| Large monolithic files | Split logic: `src/core.py`, `src/mcp_server.py`, etc. |

## Adding a New Setup Task

To add `./do setup-your-package`:

1. Create `scripts/setup-your-package`:

```bash
#!/bin/bash
## setup-your-package: Interactive setup for your-package

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd -P)"
source "${script_dir}/setup-common.sh"

main() {
    case "${1:-}" in
        --help|-h)
            echo "Usage: ./do setup-your-package [--verify]"
            ;;
        --verify)
            check_status
            ;;
        *)
            info "Your Package Setup Wizard"
            # Interactive steps
            ;;
    esac
}

main "$@"
```

2. Make it executable: `chmod +x scripts/setup-your-package`
3. Task runner automatically discovers it via `./do`

## Dependency Resolution

When your package depends on others:

```yaml
# packages/your-package/apm.yml
dependencies:
  apm:
    - name: context-discipline
      version: ">=0.1.0"
  mcp:
    - name: your-mcp-server
      type: stdio
      command: python -m your_module.src.serve
```

APM will:
1. Fetch both packages
2. Merge instructions/skills from both
3. Configure MCP for both
4. Agent sees unified interface

## Contributing Back

If you create a reusable package:

1. Test thoroughly with `apm pack` and `apm marketplace check`
2. Add comprehensive README + documentation
3. Use Apache-2.0 license (SPDX headers everywhere)
4. Submit PR with:
   - New package directory
   - Updated root `apm.yml`
   - Description of what it adds
   - Testing instructions

## Questions?

- **APM docs:** https://github.com/microsoft/apm
- **MCP protocol:** https://modelcontextprotocol.io/
- **Package examples:** Look at `packages/graphify-codegraph/` or `packages/context-discipline/`

---

**Remember:** Packages are guidance + tools. Agents use them. Keep them simple, well-documented, and deterministic.
