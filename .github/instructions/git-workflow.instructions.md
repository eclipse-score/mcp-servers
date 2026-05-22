---
applyTo: '**'
---

# Git Workflow

## Commit Message Format
```
<prefix>: <summary>

<optional body>

<optional footer: Also-by: Name <email>>
```

### Types
`feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`, `style`

### Rules
- Use imperative mood: "add feature" not "added feature"
- Keep subject line under 72 characters
- One logical change per commit
- Run `gitlint` locally before pushing

## Branch Naming
Format: `<type>/<short-description>`

Examples:
- `feature/add-login`
- `bugfix/fix-null-pointer`
- `hotfix/auth-patch`

## Pull Request Workflow
1. Analyze full commit history: `git diff <base-branch>...HEAD`
2. Draft comprehensive PR summary covering what changed and why
3. Include a test plan with verification steps
4. Push with `-u` flag if new branch
5. Request review from at least one peer

## Pre-Commit Checklist
- [ ] All tests pass locally
- [ ] No lint errors or warnings
- [ ] No `console.log` / `System.out.println` left in production code
- [ ] No TODO/FIXME without a linked issue
- [ ] Commit message follows format above
- [ ] Branch is rebased on latest base branch

## Merge Strategy
- Use squash merge when all commits are from the same author and represent one topic
- Use rebase/merge commit when commits represent distinct topics or multiple authors
- Preserve clear history and avoid merge commits from `main` into feature branches
