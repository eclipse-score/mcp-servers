# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

---
name: setup-propagation
description: Use the setup MCP server to initialize local APM package state
applyTo: "**"
---

# APM Setup Propagation

Use the setup MCP tools explicitly when a repository needs local package state.

- Call `verify_setup` before setup when status is unknown.
- Call `setup_graphify` before the first graph query when the graph is missing.
- Call `setup_context_discipline` before recording local observations.
- Run setup again after major repository changes when generated state is stale.

APM installation and compilation do not run setup tools automatically. Setup
operations are repository-local and must be explicitly requested.
