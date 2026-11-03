---
name: setup-propagation
description: Use the setup MCP server to initialize local APM package state
applyTo: "**"
---

<!--
*******************************************************************************
Copyright (c) 2026 Contributors to the Eclipse Foundation

SPDX-License-Identifier: Apache-2.0
*******************************************************************************
-->

# APM Setup Propagation

Use the `apm-setup` MCP tools explicitly when a repository needs local package
state.

- Call `verify_setup` before setup when status is unknown.
- Call `setup_graphify` before the first graph query when the graph is missing.
- Call `setup_context_discipline` before recording local observations when user state is missing.
- Run setup again after major repository changes when generated state is stale.

Installing the package registers its declared MCP server for the selected
target; installation still does not run setup tools.
Keep setup enabled and pass the consumer repository as `repo_path`; generated output belongs in repository-keyed user storage, not in the consumer checkout.

## Relocate Generated Files

Use `verify_setup` and the paths returned by setup instead of assuming `graphify-out/` or `.score-local/` exists in the checkout.
Graph generation uses the graph runtime's user cache under `$XDG_DATA_HOME/score-agent/` or `~/.local/share/score-agent/`.
Setup uses the launcher's shared prebuilt-first policy: download the revision artifact or nightly `main`, then fall back to a usable cached graph, a checkout-local graph, or local extraction only when no graph is available.
Do not replace a usable nightly graph merely because its commit differs from checkout HEAD.
Use `setup_graphify(repo_path, force_local=true)` only when an explicit current-checkout rebuild is needed.
Context setup and runtime use `$XDG_STATE_HOME/score-agent/` or `~/.local/state/score-agent/`.
These setup operations do not modify the consumer's `.gitignore`.

For APM-generated packages and harness files, supported APM versions accept `apm install --root <cache-dir>` and `apm compile --root <cache-dir>` to redirect outputs while resolving sources from the current project.
Use a stable, repository-keyed absolute cache directory and the same root for both commands; verify support with the installed CLI's help.
Positional package installation can still edit the source `apm.yml`; use user-scoped `apm install --global` and `apm compile --global` for supported harnesses when the consumer must have no manifest changes.
Redirecting harness files to an arbitrary cache does not make agents discover them; retain installation and connect those outputs through supported user-scoped deployment or explicit harness configuration.

Do not disable setup, delete existing consumer configuration, or blanket-ignore agent files to solve output placement.
Durable `score-context/` artifacts remain intentional, reviewable repository content.
