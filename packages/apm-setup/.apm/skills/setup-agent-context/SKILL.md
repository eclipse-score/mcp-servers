---
name: setup-agent-context
description: Initialize local graph and working-memory state for APM packages
---

<!--
*******************************************************************************
Copyright (c) 2026 Contributors to the Eclipse Foundation

SPDX-License-Identifier: Apache-2.0
*******************************************************************************
-->

# Setup Agent Context

Use the registered `apm-setup` MCP server for all setup actions.

Before using graph or working-memory tools:

1. Call `verify_setup` for the target repository.
2. Call `setup_graphify` if the reported graph is missing or stale.
3. Call `setup_context_discipline` if the reported user-state directory is missing.
4. Continue only after setup reports success.

Do not assume that `apm install` or `apm compile` generated repository state.
Use returned graph and state paths; setup writes outside the consumer checkout without editing `.gitignore`.
For APM installation and compilation, use supported `--root` output redirection or user-scoped `--global` deployment without disabling either workflow.
Ensure the harness can discover relocated instructions, skills, hooks, and MCP configuration; a cache path alone is not registration.
