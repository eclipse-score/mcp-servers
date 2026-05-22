You are operating inside the SCORE governance overlay.

This file is runtime-specific glue.
The canonical, runtime-neutral policy lives in AGENTS.md at repository root.

Keep this file aligned with AGENTS.md and use it only for assistant-runtime specifics.
Update distributed policy files by running `copier update` from the repository root.

## Responsibilities

1. Preserve issue-first traceability — all work artifacts reference a GitHub issue number.
2. Honour SCORE contracts:
   - `.github/references/repo-manifest.schema.json`
   - `.github/references/agent-card.schema.json`
   - `.github/score/repo-manifest.json`
3. Apply coding standards from `.github/instructions/`.

Terminology note: `.github/references/agent-card.schema.json` defines a SCORE work/handoff artifact, not an A2A service-discovery AgentCard.

## Artifact Naming

Use issue-scoped stage folders for all work artifacts:

```
.stage/ISSUE-<number>/
  plan.md
  work-card.json
```

## SDLC Progress Block

Paste this into every response when tracking work:

### SDLC Progress -- <ISSUE-ID>
- [ ] PLAN -- Not Started
- [ ] CODE -- Not Started
- [ ] BUILD -- Not Started
- [ ] TEST -- Not Started
- [ ] RELEASE -- Not Started

## Governance Rules

- Do not embed large agent/prompt catalogs here.
- Use an upstream SDD framework (Spec Kit, OpenSpec, BMAD) for workflow orchestration.
- Keep this file and `.github/instructions/` as the only SCORE-specific overlay.
- If AGENTS.md and this file conflict, treat AGENTS.md as the canonical project policy and reconcile the files.
