---
applyTo: '**'
---

# Testing Requirements

## Minimum Coverage: 80%

100% required for:
- Financial calculations
- Authentication logic
- Security-critical code
- Core business logic

## Test Types (ALL required for production features)
1. **Unit Tests** — Individual functions, utilities, components
2. **Integration Tests** — API endpoints, database operations, service interactions
3. **System/Scenario Tests** — Critical cross-component flows where applicable

## Test-Driven Development (TDD)

Mandatory workflow for new features and bug fixes:
1. **RED** — Write a failing test first
2. **GREEN** — Write minimal implementation to pass
3. **REFACTOR** — Improve code while keeping tests green
4. Repeat for each scenario

### Rules
- Never write implementation before the test
- Run tests after every change
- Write minimal code to make tests pass
- Refactor only when tests are green

## Test Structure
- Arrange-Act-Assert (AAA) pattern
- One logical assertion per test (max 3 related assertions)
- Descriptive test names: `methodName_scenario_expectedBehavior`
- Use `@DisplayName` or equivalent for human-readable descriptions

## Test Quality
- Tests must be independent and isolated
- No shared mutable state between tests
- Fast execution (unit tests < 100ms each)
- Deterministic — no flaky tests
- Fix implementation, not tests (unless tests are wrong)

## Language-Specific Frameworks
| Language | Unit | Mocking | Integration | Coverage |
|----------|------|---------|-------------|----------|
| C++ | GoogleTest | GoogleMock | Bazel test targets | lcov/gcov |
| Python | pytest | unittest.mock | pytest + service/integration fixtures | pytest-cov |
| Rust | cargo test | mockall (or equivalent) | integration tests in `tests/` | llvm-cov/grcov |
| Go | go test | gomock/testify | package/integration tests | go test -cover |
