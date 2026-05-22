# Assistant Runtime Alignment

This repository distributes one shared policy across multiple assistant runtimes.

## Canonical instruction source

- AGENTS.md is the canonical, runtime-neutral project policy.
- CLAUDE.md imports AGENTS.md for Claude Code compatibility.
- .github/<instructions-file> is runtime-specific glue (for example copilot-instructions.md).

## Why this layout

- Codex reads AGENTS.md directly and supports layered AGENTS files.
- Claude Code reads CLAUDE.md and recommends importing AGENTS.md when both are used.
- MCP is the primary runtime integration path across assistants, so governance should align around MCP-first behavior.

## Runtime settings alignment

The template includes runtime settings stubs in:

- .claude/settings.json
- .github/copilot/settings.json

Use these stubs for runtime-local preferences and MCP-related defaults. Avoid hardcoding plugin marketplace repositories.

## Adoption checklist

1. Keep AGENTS.md as the source of truth for shared behavioral policy.
2. Keep CLAUDE.md minimal and import-first.
3. Keep .github/<instructions-file> minimal and runtime-specific.
4. Prefer MCP-native integrations over plugin marketplace dependencies.
5. Use copier update to roll out governance and alignment updates.
