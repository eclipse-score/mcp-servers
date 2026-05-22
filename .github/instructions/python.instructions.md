---
applyTo: '**/*.py'
---

# Python Guidelines

## Project Structure
```
project-root/
├── README.md
├── requirements.txt or pyproject.toml
├── src/mypackage/
│   ├── __init__.py
│   └── module1.py
├── scripts/
│   └── run_analysis.py
└── tests/
    ├── __init__.py
    └── test_module1.py
```
- Source code in dedicated package directory (`src/mypackage/`)
- Scripts in `scripts/` with `if __name__ == "__main__":` entry points
- Tests in parallel `tests/` directory mirroring code structure

## Code Style
- Follow PEP 8; use auto-formatting (Black) and linting (ruff/flake8)
- `snake_case` for modules/functions, `CapWords` for classes, `UPPER_SNAKE_CASE` for constants
- Explicit, descriptive names for all identifiers
- Imports at top: standard library, third-party, local -- with blank lines between
- Absolute imports only; no wildcard imports
- Docstrings for all public modules, classes, functions, methods
- Minimize comments -- code must be self-explanatory

## Function & Parameter Rules
- **Never use mutable default arguments** (lists, dicts) -- use `None` and create inside function
- **No blank strings/lists as defaults**
- **No `.get()` for required dict keys** -- access directly so missing keys raise errors
- Check explicitly for `None` or absence for optional values

## Error Handling
- Catch specific exception types only -- never bare `except:`
- Use `logging` module, never `print()`
- Log or re-raise errors appropriately

## Type Hints & Readability
- Use type hints to clarify input/output types
- Small, focused functions (Single Responsibility)
- Prefer comprehensions and built-ins for clarity
- Avoid deep nesting; break logic into helpers

## Dependencies & Configuration
- Pin all dependency versions in `requirements.txt` or `pyproject.toml`
- Always use virtual environments
- Environment variables or config files for secrets -- never hardcode
- `.gitignore` excludes venvs, caches, non-source artifacts

## Security
- **No hardcoded secrets** — use environment variables, `.env` files (in `.gitignore`), or secret managers
- **Parameterized queries only** — never use f-strings or `%` formatting for SQL
- **Path traversal prevention** — validate and sanitize all file paths; reject `..` components
- **Input validation** at API boundaries — use Pydantic models or marshmallow schemas
- **No `eval()` or `exec()`** on user input — ever
- **Dependency scanning** — use `pip-audit` or `safety` in CI pipeline
- **No sensitive data in logs** — mask PII, tokens, passwords

## Data Validation with Pydantic
- Use Pydantic `BaseModel` for request/response validation at API boundaries
- Define strict types with `Field()` constraints (`min_length`, `max_length`, `ge`, `le`)
- Use `@validator` or `@field_validator` for custom validation logic
- Return Pydantic models from service layer for type safety

## Testing
- **TDD mandatory**: RED → GREEN → REFACTOR for new features and bug fixes
- pytest for all testing
- `test_` prefix for files and functions
- Use pytest fixtures for shared setup
- Never mix tests with production code
- Happy path + edge case tests with clear assertions
- Use `@pytest.mark.parametrize` for data-driven tests
- `unittest.mock` for external dependencies
- Min 80% coverage; 100% for security-critical code
- Use `pytest-cov` for coverage enforcement in CI

## General
- Prefer standard library; add third-party only for clear benefit
- Validate and sanitize all inputs; no silent failures
- Use context managers (`with`) for resource management
