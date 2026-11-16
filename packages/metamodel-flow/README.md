<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# metamodel-flow

`metamodel-flow` delivers the normative S-CORE artifact model as an APM
instruction package. `docs-as-code` owns `metamodel.yaml`; this package projects
it into `model/agent_context.json` and renders that projection into
deterministic Markdown for agents.

## Updating the model

The `Refresh model` workflow (`.github/workflows/refresh-model.yml`) runs daily
and refreshes everything in `model/`:

1. **Metamodel:** fetches `metamodel.yaml` from docs-as-code `main` and
   regenerates `agent_context.json`, `metamodel-data.json`, `source.txt` and the
   instructions.
2. **Process graph:** builds `needs.json` from process_description `main` with
   Bazel and regenerates `process_graph.json` and `process_source.txt`.

Both steps write only when their content changed. If anything changed, the
workflow opens or updates one PR from `bot/model-refresh-<branch>`. Review and merge it
like any other change. A failed run appears in the Actions tab.

To refresh by hand, from a checkout of this repo:

```bash
uv run python packages/metamodel-flow/src/refresh_model.py --ref <docs-as-code branch or SHA>
```

The package tests compare the committed instructions against a fresh render, so
the existing `pytest` job in CI fails whenever projection and instructions
disagree.

`export_metamodel_data.py` exports the data from a local `metamodel.yaml` file
without fetching it:

```bash
uv run --with ruamel.yaml python packages/metamodel-flow/src/export_metamodel_data.py \
  --metamodel /tmp/metamodel.yaml \
  --source-commit <sha> \
  --output packages/metamodel-flow/model/metamodel-data.json
```

`--source-commit` is required so the output records the docs-as-code revision it
was built from. `metamodel-data.json` has no consumer in this repo yet.

## Model files

| File | Produced by | Contents |
| --- | --- | --- |
| `model/agent_context.json` | `refresh_model.py` | Agent projection of `metamodel.yaml` |
| `model/source.txt` | `refresh_model.py` | docs-as-code commit the projection came from |
| `model/metamodel-data.json` | `export_metamodel_data.py` | Flat instance data for `metamodel.yaml` |
| `model/process_graph.json` | `refresh_process_graph.py` | Process graph projected from process_description |
| `model/process_source.txt` | `refresh_process_graph.py` | process_description commit the graph came from |

## Testing

```bash
uv run --with ruamel.yaml --with pytest python -m pytest -q packages/metamodel-flow/tests
```
