# AI Contribution Policy - mcp-servers

**Scope:** This repository (eclipse-score/mcp-servers)
**Status:** Draft

## AI Tools Are Welcome

This is developer tooling, not safety-critical vehicle software. AI-assisted contributions are encouraged - MCP server code is an ideal use case for AI coding tools.

## Disclosure

### When Required

Disclose when AI generated code, tests, documentation, or design approaches you included.

### When Not Required

No disclosure needed for: IDE autocomplete (single-line), Q&A/learning, spell/grammar fixes, AI-assisted code review (reading).

When in doubt, disclose.

### How

Commit trailers (mandatory for AI-assisted commits):

```text
Assisted-by: GitHub Copilot <noreply@github.com>
```

PR template checkbox (supplementary - catches forgotten trailers):

```text
- [x] This PR contains AI-assisted code
- Tool(s) used: Copilot, Claude Code
```

## Human Accountability

- AI tools cannot be authors or co-authors
- Signed-off-by (DCO) comes from humans only
- You must read, understand, and verify all AI-generated code
- The human submitter bears full legal responsibility

## Quality

AI-assisted code is held to the same standard:

- Must pass CI (build, test, lint, type check)
- Must follow coding standards (.github/instructions/)
- Must include tests
- Low-effort unreviewed AI output may be rejected without detailed feedback

## Licensing

- All contributions licensed under Apache 2.0
- Eclipse Foundation IP review applies for contributions >1000 lines
- Ensure AI-generated code does not include incompatibly licensed content

## References

- [KubeVirt AI Policy](https://github.com/kubevirt/community/blob/main/ai-contribution-policy.md)
- [Linux Kernel AI Policy](https://lore.kernel.org/all/) (April 2026)
- [Eclipse Foundation Contribution Guidelines](https://www.eclipse.org/legal/ECA.php)
