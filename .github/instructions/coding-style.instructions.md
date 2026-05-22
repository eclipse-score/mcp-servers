---
applyTo: '**'
---

# Coding Style

## Immutability (CRITICAL)

ALWAYS create new objects, NEVER mutate existing ones:
- Return new instances rather than modifying in place
- Use spread operators, `List.copyOf()`, `Map.copyOf()`, or equivalent
- Mark fields `final` / `readonly` / `const` by default

Rationale: Immutable data prevents hidden side effects, makes debugging easier, and enables safe concurrency.

## File Organization

MANY SMALL FILES > FEW LARGE FILES:
- High cohesion, low coupling
- 200-400 lines typical, 800 max
- Extract utilities from large modules
- Organize by feature/domain, not by type

## Function Size

- Ideal: 3-10 lines, rarely more than 20
- Max: 50 lines — split if exceeded
- Single atomic step of logic per function
- No flag arguments — split into separate functions

## Nesting

- Max 4 levels of nesting
- Use guard clauses and early returns to flatten
- Extract complex predicates into named boolean methods
- Extract inner loops into helper functions

## Error Handling

ALWAYS handle errors comprehensively:
- Handle errors explicitly at every level
- Provide user-friendly error messages in UI-facing code
- Log detailed error context on the server side
- Never silently swallow errors

## Input Validation

ALWAYS validate at system boundaries:
- Validate all user input before processing
- Use schema-based validation where available
- Fail fast with clear error messages
- Never trust external data (API responses, user input, file content)

## Code Quality Checklist

Before marking work complete:
- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Proper error handling at every level
- [ ] No hardcoded values (use constants or config)
- [ ] No mutation (immutable patterns used)
- [ ] No `console.log` / `System.out.println` in production code
- [ ] No TODO/FIXME without a linked issue
