<!--
*******************************************************************************
Copyright (c) 2026 Contributors to the Eclipse Foundation

See the NOTICE file(s) distributed with this work for additional
information regarding copyright ownership.

This program and the accompanying materials are made available under the
terms of the Apache License Version 2.0 which is available at
https://www.apache.org/licenses/LICENSE-2.0

SPDX-License-Identifier: Apache-2.0
*******************************************************************************
-->

# Eclipse S-CORE Agent Context Attention Layer

This repository contributes infrastructure for the
[Eclipse Safe Open Vehicle Core](https://projects.eclipse.org/projects/automotive.score)
(S-CORE) project. The source code is hosted on
[GitHub](https://github.com/eclipse-score).

Please note that the Eclipse Foundation's
[Terms of Use](https://www.eclipse.org/legal/terms-of-use/) apply. Contributors
must sign the [Eclipse Contributor Agreement (ECA)](https://www.eclipse.org/legal/ECA.php)
and follow the [Developer Certificate of Origin (DCO)](https://www.eclipse.org/legal/dco/).
Every commit must include a `Signed-off-by` trailer.

## Contributing


### Directory structure for packages

```text
my-pkg/
+-- apm.yml                       # The manifest. Required. See below.
+-- apm.lock.yaml                 # Resolved versions + content hashes. Generated.
+-- apm_modules/                  # Installed dependencies. Generated. Gitignore.
+-- .apm/                         # Source primitives you author.
|   +-- instructions/             # Always-on rules attached to file globs.
|   +-- skills/                   # Multi-file capabilities (SKILL.md + assets).
|   +-- prompts/                  # Reusable prompt templates.
|   +-- agents/                   # Named agents (model + system prompt + tools).
|   +-- context/                  # Shared context fragments.
|   +-- hooks/                    # Lifecycle hooks (pre/post events).
+-- .github/                      # Compiled output for Copilot. Generated.
|   +-- instructions/
|   +-- agents/
|   +-- copilot-instructions.md
+-- .claude/                      # Compiled output for Claude Code. Generated.
+-- .cursor/                      # Compiled output for Cursor. Generated.
+-- .codex/                       # Compiled output for Codex. Generated.
+-- AGENTS.md                     # Compiled context for agents-family targets. Generated.
+-- GEMINI.md                     # Compiled context for Gemini. Generated.
+-- apm-policy.yml                # Optional org/repo policy. See enterprise docs.
+-- scripts/                      # Optional helper scripts you author.
+-- tests/                        # Optional tests for your primitives.
```


### Getting the source code and building

Refer to [README.md](README.md) for the repository overview. Validate the
repository and generate the marketplace from `apm.yml`:

```shell
./scripts/validate.sh
apm pack --json
apm pack --check-versions --dry-run --json
```

`apm pack` generates `.claude-plugin/marketplace.json`. Do not hand-create or
edit that generated file. Commit the generated marketplace artifact when the
marketplace configuration changes.

To verify package discovery from outside the repository, use a clean directory:

```shell
mkdir -p /tmp/test-marketplace
cd /tmp/test-marketplace
apm marketplace add /path/to/mcp-servers/.claude-plugin/marketplace.json
apm marketplace browse eclipse-score-apm-marketplace
```

The browse command should list `context-discipline` and `graphify-codegraph`.

### Package changes

When adding or changing a package:

1. Update the package's `apm.yml`, `mcp.yml`, documentation, and source files.
2. Add or update its entry under `marketplace.packages` in the root `apm.yml`.
3. Run `apm pack` to regenerate `.claude-plugin/marketplace.json`.
4. Run the validation and version checks above.
5. Test installation from a clean directory with an explicit target such as
   `--target copilot`.

### Getting involved

Please use GitHub issues and pull requests for contributions. Keep pull
requests focused, describe the motivation and verification performed, and mark
them as drafts until they are ready for committer review. Reviews and final
merges are performed according to the
[Eclipse Foundation Project Handbook](https://www.eclipse.org/projects/handbook/).

For a contribution:

1. Open or identify an issue describing the bug, improvement, or governance
   change.
2. Create a focused branch and pull request.
3. Run the checks documented in the README and report the results.
4. Ensure every commit has the required DCO sign-off.

All contributions are subject to the Eclipse Foundation project processes and
the applicable community code of conduct.
