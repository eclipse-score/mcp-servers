---
applyTo: '**'
---

# Security Guidelines

## Mandatory Checks Before Every Commit
- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated at system boundaries
- [ ] SQL injection prevention (parameterized queries only)
- [ ] XSS prevention (sanitized HTML output)
- [ ] CSRF protection enabled
- [ ] Authentication and authorization verified
- [ ] Rate limiting on public endpoints
- [ ] Error messages do not leak internal details

## Secret Management
- NEVER hardcode secrets in source code
- Use environment variables or a secret/config manager
- Validate required secrets are present at startup
- Rotate any secrets that may have been exposed
- Keep files with secrets in `.gitignore`

## Input Validation
- Validate all user input before processing
- Use schema-based validation where available (Bean Validation, Zod, Pydantic)
- Fail fast with clear error messages
- Never trust external data (API responses, user input, file content)

## Dependency Security
- Audit transitive dependencies regularly
- Use OWASP Dependency-Check, Snyk, or Dependabot for CVE scanning
- Keep dependencies updated with automated tooling
- Pin versions in production deployments

## Error Responses
- Never expose stack traces in API responses
- Map exceptions to safe, generic client messages at handler boundaries
- Log detailed errors server-side only
- Maintain an ErrorCode mapping for consistent client-facing messages

## Authentication
- Never implement custom auth crypto — use established libraries
- Store passwords with bcrypt or Argon2 (never MD5/SHA1)
- Enforce authorization checks at service boundaries
- Never log passwords, tokens, or PII

## Security Response Protocol
If a security issue is found during development:
1. STOP current work immediately
2. Assess severity (Critical / High / Medium / Low)
3. Fix CRITICAL issues before continuing any other work
4. Rotate any potentially exposed secrets
5. Review codebase for similar patterns
