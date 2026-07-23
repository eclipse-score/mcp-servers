# Eclipse S-CORE APM Monorepo

This repository is an **APM monorepo** for Eclipse S-CORE: a single home for
[Microsoft APM](https://github.com/microsoft/apm) packages (skills, instructions,
prompts, agents, hooks, context) and their supporting harness tools. New packages
are added here and distributed to the S-CORE organization through APM.

It uses APM's **monorepo-hybrid** shape: a root `apm.yml` acts as the marketplace
manifest and points at local packages, and each package under `packages/` is a
full, independently installable APM package with its own `apm.yml` and `.apm/`
tree.

On top there is a first context attention layer (`packages/context`).
This is a context distribution mechansim which later on crates an asynch
knowledge graph of "signals" in score.


## Layout

- `apm.yml` — root **marketplace manifest**; lists the local packages.
- `packages/<pkg>/` — one APM package each (own `apm.yml` + `.apm/<type>/`).
  - `packages/_template/` — copy-to-add-a-package skeleton.
  - `packages/context/` — the attention-layer package (one example).
- `libs/` — shared Python code, MCP-free and independent of APM.
  - `libs/score-context/` — the engine + Phase 0 schema used by `packages/context`.

APM primitives live under each package's `.apm/<type>/` tree, where `<type>` is
one of `instructions`, `skills`, `prompts`, `agents`, `hooks`, or `context`.
MCP servers are **not** a directory — they are declared in a package's `apm.yml`
under `dependencies.mcp:`, and APM writes each harness's MCP config on install.

## Adding a new APM package

1. **Copy the template** to a new package directory:

   ```shell
   cp -r packages/_template packages/<your-package>
   ```

2. **Edit `packages/<your-package>/apm.yml`** — set `name`, `version`,
   `description`, keep `license: Apache-2.0`, and uncomment/set `type:` and
   `targets:` (e.g. `copilot`, `claude`, `cursor`, `codex`, `gemini`, `opencode`)
   as needed. Declare any MCP servers under `dependencies.mcp:`.

3. **Add your primitives** under `.apm/<type>/` — for example a skill at
   `.apm/skills/<name>/SKILL.md`, or instructions at
   `.apm/instructions/<name>.instructions.md`. Remove the `.gitkeep` files from
   directories you populate and delete `.apm/<type>/` trees you do not use.

4. **Register the package in the root marketplace** — add an entry under
   `marketplace.packages` in the root `apm.yml`:

   ```yaml
   marketplace:
     packages:
       - name: <your-package>
         source: ./packages/<your-package>
         version: 0.1.0
   ```

5. **Add license/copyright headers** to every new file (Apache-2.0 SPDX header;
   for files that cannot carry an inline header, add an entry to `REUSE.toml`) so
   the repository stays REUSE-compliant.

6. **Validate with the APM CLI** (a green `apm` run is the definition of valid):

   ```shell
   apm pack --offline --json
   apm marketplace check --offline
   ```

## Development

Python tooling for the shared engine and any package that ships code:

```shell
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```
