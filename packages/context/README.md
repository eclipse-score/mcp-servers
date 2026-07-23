# context

This APM package is the content-side home for the Agent Context Attention
Layer. Generated attention fragments will land under `.apm/context/` starting
in Phase 1.

The shared engine is the MCP-free `libs/score-context` Python library. The
`get_context` MCP server is planned for Phase 6 and is not implemented or
declared as a dependency yet.
