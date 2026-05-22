# AGENTS.md

SCORE canonical assistant policy for this repository.

This file is the shared, runtime-neutral source of behavioral guidance across:
- Codex (reads AGENTS.md directly)
- Claude Code (via CLAUDE.md import)
- Other assistants (via their runtime-specific instructions file)

## Scope

This repository keeps a thin governance overlay only.
Do not add large local agent or prompt catalogs.

## Core responsibilities

1. Preserve issue-first traceability.
2. Preserve SCORE contracts:
   - .github/references/repo-manifest.schema.json
   - .github/references/agent-card.schema.json
   - .github/score/repo-manifest.json
3. Apply coding standards from .github/instructions/.

Terminology note: .github/references/agent-card.schema.json defines a SCORE work/handoff artifact, not an A2A service-discovery AgentCard.

## Artifact rules

Use issue-scoped artifacts only:

```text
.stage/ISSUE-<number>/...
```

Do not create anonymous stage artifacts at repo root.

## SDLC status block

When reporting progress, use:

```markdown
### SDLC Progress -- <ISSUE-ID>
- [ ] PLAN -- Not Started
- [ ] CODE -- Not Started
- [ ] BUILD -- Not Started
- [ ] TEST -- Not Started
- [ ] RELEASE -- Not Started
```

## Governance constraints

- Keep SCORE policy concise and deterministic.
- Keep workflow frameworks external (for example Spec Kit or OpenSpec).
- Keep shared commands in .github/score/repo-manifest.json.
