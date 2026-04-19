---
name: pr-review
description: Code-review playbook for PALP PRs. Use when reviewing a teammate's PR or self-reviewing before requesting review.
---

# PR Review — Reviewer Playbook

## When to use

- Reviewing a teammate's PR (assigned via CODEOWNERS)
- Self-review before clicking "Ready for review"
- Reviewing your own draft to catch issues before CI burns minutes

## SLA

- First response within **24 hours** of "Ready for review"
- Approval or block decision within **48 hours**
- If you can't meet SLA, comment with ETA or hand off

## Review pass order (15-30 min total)

### Pass 1: Title, description, scope (2 min)

- [ ] Title follows Conventional Commits: `feat(scope): subject` (≤72 chars)
- [ ] Description fills `PULL_REQUEST_TEMPLATE.md` — Why? What changed?
- [ ] Linked issue: `Closes #123`
- [ ] Scope is reasonable (≤200 LOC ideally; if larger, justified)
- [ ] Single logical change (not "fix bug + refactor + add feature")

If any fail -> request restructure before deeper review.

### Pass 2: CI status (1 min)

- [ ] All jobs green: `lint`, `migration-check`, `openapi`, `security-audit`, `backend-test`, `frontend-test`, `e2e`, `build`
- [ ] No skipped jobs that should run
- [ ] If `release-gate` ran, all D1-D12 passed

If red -> ask author to fix before review.

### Pass 3: Architecture & design (5-10 min)

- [ ] Aligns with PALP module map (`.ruler/01-project-architecture.md`)
- [ ] Single responsibility per function/class/module
- [ ] No new dependency without `requirements.txt` / `package.json` update + ADR for major
- [ ] Reuses existing utilities (`backend/<app>/utils.py`, `frontend/src/lib/`, `frontend/src/components/ui/`)
- [ ] No God-object, no mega-function (>100 lines without justification)
- [ ] Naming consistent with project (snake_case backend, camelCase frontend, kebab-case URL)

### Pass 4: Correctness (5-10 min)

Read the diff line-by-line. For each change ask:

- [ ] Does this do what the description says?
- [ ] Edge cases handled? (empty input, max int, unicode, null, very long string, concurrent)
- [ ] Off-by-one, infinite loop, division by zero?
- [ ] Race condition? (`select_for_update` for concurrent writes; atomic transaction)
- [ ] N+1 query? (prefer `select_related`/`prefetch_related`)
- [ ] Async edge case? (Celery task idempotent? Retry safe?)

### Pass 5: Security & privacy (3-5 min)

- [ ] No hardcoded secret (run `detect-secrets` mental check)
- [ ] PII flows through `EncryptedTextField`, never plaintext column
- [ ] New PII endpoint -> consent + audit prefix + RBAC test (see `privacy-gate` skill)
- [ ] RBAC enforced in `get_queryset()` not just `permission_classes` (see `rbac-check` skill)
- [ ] Cross-user access test exists (`test_other_student_cannot_access`)
- [ ] No raw SQL with user input (ORM only)
- [ ] Rate limit/throttle on auth-adjacent endpoints

### Pass 6: Tests (3-5 min)

- [ ] New code has new tests (coverage not regressed)
- [ ] Tests follow `TestSomethingUnit` + `@pytest.mark.integration` pattern
- [ ] Negative tests: 401, 403, 404, 400 covered
- [ ] No test depends on execution order
- [ ] Fixtures used (no manual user/object construction)
- [ ] Test name reads as a sentence: `test_lecturer_cannot_export_other_class_data`
- [ ] Mocked external deps (S3, email, third-party APIs)

### Pass 7: Migration & contract (2-3 min)

- [ ] Migration backward-compatible (see `migration-runbook` skill)
- [ ] No `RemoveField` in same PR as code that uses it
- [ ] OpenAPI baseline updated if API changed (see `openapi-update` skill)
- [ ] No breaking change without ADR + version bump
- [ ] `docs/API.md` updated if contract changed
- [ ] AGENTS.md / .ruler/ updated if conventions changed

### Pass 8: UX & a11y (2-3 min, frontend only)

- [ ] D7: loading + empty + error + success states all rendered
- [ ] D8: keyboard navigable (Tab, Enter, Esc)
- [ ] D8: screen reader labels (`aria-label`, `<label htmlFor>`)
- [ ] D8: color contrast >= AA (axe-clean)
- [ ] Mobile responsive (`sm:`, `md:`, `lg:` breakpoints)
- [ ] Vietnamese strings ready for i18n (no hardcoded user-facing English)
- [ ] Component follows `frontend-component` skill pattern (Radix + cva + cn)

### Pass 9: Observability (2 min)

- [ ] D5: analytics event emitted for new user action (use `event-taxonomy` skill)
- [ ] D6: audit log triggers for sensitive access (in `AUDIT_SENSITIVE_PREFIXES`)
- [ ] D9: metric + alert if critical path (Prometheus + Grafana)
- [ ] Structured log with `request_id` and domain IDs
- [ ] Log level appropriate (debug/info/warning/error)

## Comment style

- Prefer **suggestions** (GitHub's commit suggestion) for nits
- Use **threading**: one comment per concern, not a giant essay
- Severity tags: `[blocker]`, `[concern]`, `[nit]`, `[praise]`
- Cite the rule: "[blocker] Per `06-privacy-security.md`, this endpoint needs to be added to `AUDIT_SENSITIVE_PREFIXES`."
- Be kind. Praise good code (`[praise] Clean abstraction here, will reuse it.`)

## Approval criteria

Approve when:
- All blockers resolved
- All concerns either addressed or acknowledged with rationale
- Nits remain (optional cleanup, not gating)
- CI green
- DoD D1-D12 boxes checked or N/A justified

Block when:
- Any of: P0 security, broken contract, regression test missing, CI red
- Significant rework needed (suggest closing + reopening with new branch)

## Anti-patterns (don't do this)

- Approving without reading the diff ("LGTM" with no comment)
- Demanding a complete rewrite in review (should have been discussed in issue)
- Bikeshedding style/naming when CI lint already passed
- Holding PR hostage for unrelated tech debt
- Self-merging without required approval
- Force-pushing after review starts (rebase OK but communicate it)

## Quick reference

Other skills relevant during review:
- `privacy-gate` — for endpoints touching PII
- `rbac-check` — for any new view
- `bkt-engine` — for adaptive logic changes
- `celery-task` — for new background jobs
- `migration-runbook` — for any migration in the PR
- `openapi-update` — for any DRF view change
- `event-taxonomy` — for new analytics events
- `release-gate` — final pre-merge sanity check
- `frontend-component` — for new React components
- `incident-response` — if review reveals a possible production issue
