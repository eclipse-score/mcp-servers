<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# metamodel-flow

`metamodel-flow` delivers the normative S-CORE artifact model as an APM
instruction package. `docs-as-code` owns `metamodel.yaml`; this package projects
it into `model/agent_context.json` and renders that projection into
deterministic Markdown for agents.

## Updating the model

```bash
uv run python packages/metamodel-flow/src/refresh_model.py --ref <docs-as-code branch or SHA>
```

This fetches `src/extensions/score_metamodel/metamodel.yaml` at that commit,
regenerates `model/agent_context.json`, records the commit in
`model/source.txt` and re-renders the instructions. Commit the result in a PR.

The `Metamodel drift` workflow runs the same command with `--check` against
docs-as-code `main` every night and opens or updates an issue when the
projection changed. No workflow writes or commits generated files.

The package tests compare the committed instructions against a fresh render, so
the existing `pytest` job in CI fails whenever projection and instructions
disagree.
