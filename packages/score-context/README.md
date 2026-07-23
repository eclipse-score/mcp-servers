# score-context

The MCP-free schema and normalized context-delta model for the Agent Context
Attention Layer. It reuses node and relation identifiers from the S-CORE
`score_metamodel` and adds trace/event vocabulary for sources outside
sphinx-needs.

Adapters, graph composition, ranking, APM generation, and MCP endpoints are
reserved for later phases.

## Relation mapping

The relation enum reuses every entry from `needs_extra_links` in the S-CORE
metamodel and adds trace relations from the ADR:

| ADR term | Schema relation(s) |
| --- | --- |
| `implements` | `implements` (reused) |
| `verifies` | `fully_verifies` or `partially_verifies` (reused) |
| `supersedes` | `supersedes`, with decision-record status tracking |
| `affects` | `affects` |
| `depends_on` | `depends_on` |
| `discussed_in` | `discussed_in` |
| `blocks` | `blocks` |
| `conflicts_with` | `conflicts_with` |
| `authored_by` | `authored_by` |
| `owns` | `owns` (for CODEOWNERS ownership) |
