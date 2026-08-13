# Contributing to mcp-servers

Thank you for contributing to Eclipse S-CORE! This guide explains how to add packages, run tests, and submit PRs.

## Getting Started

### Clone and Setup

```bash
git clone https://github.com/user/mcp-servers.git
cd mcp-servers

# Verify structure
ls packages/  # Should see: _template, context-discipline, graphify-codegraph, context
```

### Understand the Structure

```
packages/
├── _template/             # Template for new packages (copy this)
├── graphify-codegraph/    # Example: external tool wrapper
├── context-discipline/    # Example: full MCP implementation
└── context/               # Legacy reference

Root files:
├── apm.yml                # Marketplace manifest
├── README.md              # Quick start (for users)
├── AGENTS.md              # Agent guidance (for AI)
└── CONTRIBUTING.md        # This file
```

## Adding a New Package

### 1. Copy Template

```bash
cp -r packages/_template packages/your-package-name
```

### 2. Update Package Metadata

Edit `packages/your-package-name/apm.yml`:

```yaml
name: your-package-name
version: 0.1.0
description: What this package does
license: Apache-2.0

targets:
  - copilot
  - claude
  - cursor

# If wrapping external tool:
external_dependencies:
  - name: some-tool
    install: uv tool install package-name

# If you have MCP server:
dependencies:
  mcp:
    - name: your-package-name
      type: stdio
      command: python -m your_package_name.src.serve
```

### 3. Add Behavioral Guidance

Create `.apm/instructions/<topic>.instructions.md`:

```markdown
# Your Topic

## When to Use
Brief description of when agent should use this.

## Key Patterns
List 3-5 best practices.

## Example
Show how agent should use this.
```

### 4. Add Skills (Optional)

Create `.apm/skills/<skill-name>/SKILL.md`:

```markdown
# Your Skill Name

## What It Does
One-line description.

## How to Use
Step-by-step instructions.

## Example
Show usage example.
```

### 5. Implement MCP Server (If Needed)

**Option A: Wrap External Tool** (like graphify-codegraph)

```python
# src/serve.py
import subprocess
import sys

def main():
    subprocess.run(
        [sys.executable, "-m", "external_tool.serve"],
        check=True
    )

if __name__ == "__main__":
    main()
```

**Option B: Full Implementation** (like context-discipline)

```python
# src/your_package.py
from dataclasses import dataclass

@dataclass
class YourData:
    field: str

class YourMCP:
    def tool_name(self, arg: str) -> str:
        """Your tool."""
        return f"Result: {arg}"
```

Edit `mcp.yml`:

```yaml
name: your-package-name
description: What this does
version: 0.1.0

tools:
  - name: tool_name
    description: What it does
    inputSchema:
      type: object
      properties:
        arg:
          type: string
          description: The argument
      required: [arg]
```

### 6. Add License Headers

Every Python file must start with:

```python
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
```

Bash files:

```bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
```

### 7. Write README

Create `packages/your-package-name/README.md`:

```markdown
# Your Package Name

**What it does:** One sentence.

## Quick Start

1. Install: `apm install ...`
2. Use: Show example
3. Verify: How to check it works

## MCP Tools

- `tool_name()` — Description

## See Also

- [Parent docs](../parent/)
- [APM docs](https://github.com/microsoft/apm)
```

### 8. Register in Marketplace

Edit `apm.yml` (root):

```yaml
marketplace:
  packages:
    - name: your-package-name
      source: ./packages/your-package-name
      version: 0.1.0
```

## Testing Your Package

### Validate Structure

```bash
# Check manifest syntax
apm pack --offline --json

# Check marketplace
apm marketplace check --offline
```

### Unit Tests

```bash
# Create tests/
mkdir -p packages/your-package-name/tests

# Write test
cat > packages/your-package-name/tests/test_core.py << 'EOF'
import sys
sys.path.insert(0, "../src")

from your_package import YourClass

def test_tool():
    obj = YourClass()
    result = obj.tool_name("test")
    assert result is not None
EOF

# Run
python packages/your-package-name/tests/test_core.py
```

### Integration Test

```bash
# Start MCP server
cd packages/your-package-name
python -m your_package.src.serve &
MCP_PID=$!

# Test tool calls (implementation depends on MCP protocol)
# ...

# Cleanup
kill $MCP_PID
```

## Code Style

### Python

- Follow [PEP 8](https://pep8.org/)
- Use type hints
- Use `dataclasses` for data models
- Add docstrings to public functions

```python
def tool_name(self, arg: str) -> str:
    """One-line description.
    
    Args:
        arg: What this argument is
    
    Returns:
        What this returns
    """
```

### Bash

- Use `set -euo pipefail` at top
- Quote variables: `"$var"` not `$var`
- Use functions for reusable logic
- Source `setup-common.sh` for utilities

## Commit Messages

```
Short description (50 chars max)

- Bullet point (what changed)
- Bullet point (why it changed)
- Link to issue if applicable

Closes #123
```

Example:

```
Add observability package for tracing

- Implements OTEL MCP server
- Wraps external observability tool
- Adds working memory integration

See AGENTS.md for package patterns
```

## Pull Request Process

1. **Create branch** from `main`:
   ```bash
   git checkout -b feature/your-package-name
   ```

2. **Make changes** (follow steps above)

3. **Validate locally:**
   ```bash
   apm pack --offline --json
   apm marketplace check --offline
   ```

4. **Test your package:**
   ```bash
   # If it has MCP server
   cd packages/your-package-name
   python -m your_package.src.serve  # Should start without errors
   ```

5. **Commit with clear message** (see Commit Messages above)

6. **Push branch:**
   ```bash
   git push origin feature/your-package-name
   ```

7. **Open PR** with:
   - Title: "Add <package name> package"
   - Description: What the package does, why it's useful
   - Link to any issues
   - Verification steps (how to test it)

8. **Wait for CI** (APM validation, tests, etc.)

9. **Address review feedback** and push updates

10. **Merge** when approved

## Common Patterns

### Pattern 1: Query-Based Tool (graphify-codegraph style)

For tools that query static data (code graphs, documentation):

```python
class QueryMCP:
    def query(self, text: str) -> dict:
        """Query and return structured results."""
        # Load pre-generated data
        graph = load_graph("graph.json")
        
        # Filter/search
        results = graph.search(text)
        
        return {"results": results}
```

### Pattern 2: Session-Based Tool (context-discipline style)

For tools that maintain state across calls:

```python
class SessionMCP:
    def __init__(self):
        self.session = {}
    
    def initialize(self, goal: str) -> str:
        """Create session."""
        self.session["goal"] = goal
        return session_id
    
    def record_outcome(self, outcome: str) -> None:
        """Record in session."""
        self.session["outcomes"].append(outcome)
        # Persist to disk
```

### Pattern 3: Integration (context-discipline delegating to graphify style)

For tools that orchestrate other MCP servers:

```python
class IntegrationMCP:
    def query_graph(self, q: str) -> str:
        """Delegate to graphify-codegraph MCP."""
        # Call graphify_codegraph tool
        result = self.graphify_mcp.query_graph(q)
        
        # Enhance or process result
        self.record_finding(result)
        
        return result
```

## Review Checklist

Before submitting PR, verify:

- [ ] `apm pack --offline --json` passes
- [ ] `apm marketplace check --offline` passes
- [ ] All `.py` files have SPDX header
- [ ] All `.sh` files have SPDX header
- [ ] `README.md` has quick start + examples
- [ ] `.apm/instructions/` populated
- [ ] `.apm/skills/` populated (if applicable)
- [ ] `mcp.yml` defines all tools (if applicable)
- [ ] `apm.yml` registered in root `apm.yml`
- [ ] Tests pass locally
- [ ] Commit messages follow format above
- [ ] No hardcoded paths (use `Path.cwd()`, relative paths)

## Questions?

- **APM docs:** https://github.com/microsoft/apm
- **MCP protocol:** https://modelcontextprotocol.io/
- **Package examples:** 
  - graphify-codegraph (external tool wrapper)
  - context-discipline (full MCP + state)
- **For agents creating packages:** See [AGENTS.md](AGENTS.md)

---

**Thank you for contributing!** Your packages help agents work smarter, faster, and more locally.
