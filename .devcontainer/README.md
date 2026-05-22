# Devcontainer

This repository supports development in the Eclipse S-CORE devcontainer image.

## What happens automatically

When the container is created, VS Code runs the post-create command from [devcontainer.json](devcontainer.json):

1. Install project dependencies with `uv sync --all-groups`.
2. Install git hooks with `uv run pre-commit install --install-hooks`.

When the container starts, VS Code runs the post-start command to refresh the local SSH known-host entry used by the workspace tooling.

## Daily workflow

1. Reopen the repository in container.
2. Run tests: `uv run pytest -xvs`.
3. Run checks: `uv run ruff check src/ tests/` and `uv run basedpyright src/`.
4. Run hooks manually if needed: `uv run pre-commit run --all-files`.

## Troubleshooting

- If tools are missing, run `uv sync --all-groups` manually.
- If hooks are missing, run `uv run pre-commit install --install-hooks` manually.
- To verify runtime availability from MCP, call the `server_health` tool.
