---
applyTo: '**'
---

# Clean Code Guidelines (All Languages)

## Goal
Code is *extremely readable*, composed of *very small and focused* methods/functions, and avoids all code smells.

## General Principles
- Code is for **humans first**, computers second
- Express intent clearly -- self-explanatory names for variables, methods, classes
- Prefer self-documenting code; comments as last resort
- **Small is beautiful** -- small, focused methods and classes
- Duplication is a bad sign -- extract and reuse
- KISS -- reduce complexity as much as possible
- YAGNI -- avoid over-engineering
- Boy Scout Rule -- leave the codebase cleaner than you found it
- Tell, Don't Ask -- promote loose coupling
- Be Consistent -- follow existing conventions
- Encapsulate boundary conditions in one place
- Avoid negative conditionals
- Use dependency injection

## SOLID Principles
- **SRP**: Each method/class does one thing only
- **OCP**: Open for extension, closed for modification
- **LSP**: Subtypes substitutable for base types
- **ISP**: Small, focused interfaces
- **DIP**: Depend on abstractions, not concretions

## Code Smells to Remove
Long Method, Large Class, Primitive Obsession, Long Parameter List (max 3), Data Clumps, Switch Statements, Temporary Field, Divergent Change, Shotgun Surgery, Duplicated Code, Dead Code, Feature Envy, Middle Man, Magic Numbers (replace with named constants).

## Class Design
- Small: max ~7 fields, ~3-5 public methods
- Single clear purpose aligned with domain
- Domain-focused naming (e.g. `PolicyRenewalService`, not `HelperUtil`)
- Encapsulation -- hide internal structure
- Prefer immutability, composition over inheritance
- Follow Law of Demeter
- Prefer value objects over primitives
- Avoid God objects and util classes

## Method Design
- Ideal length: ~3 lines, rarely more than 5
- Single atomic step of logic
- Names describe *what* not *how*
- No side effects
- Use guard clauses / early returns
- Avoid nested ifs/loops
- No flag arguments -- split into separate methods
- Extract complex predicates into named boolean methods

## Test Design
- Small, specific, isolated, fast, independent, repeatable
- Arrange-Act-Assert format
- Max 3 assertions per test
- Always test new public behavior
- At least one negative test per API
- Avoid duplicated test data -- extract to class level

## Naming
- Descriptive and unambiguous
- Methods: verbs. Classes: nouns. Variables: clear names
- Pronounceable, searchable, no encodings

## Comments
- Explain *why*, not *what*
- Document assumptions, invariants, edge cases
- Never comment out code -- just remove it

## Error Handling
- Use domain-specific custom exceptions
- Handle exceptions gracefully; never swallow them
- Externalize user-facing messages
- Maintain ErrorCode mapping

## Security
- No hardcoded secrets, URLs, or sensitive info
- All sensitive config resolved via environment or config server
- PII protection: data masking, tokenization

## Performance
- Avoid premature micro-optimizations unless profiled
- Batch operations in single transactions
- Refactor nested loops into indexed maps (O(n+m))

## API Design
- RESTful conventions with domain-driven design
- Plural noun resources: `/v1/templates`
- Accept filtering & expansion parameters
- Consistent resource naming
