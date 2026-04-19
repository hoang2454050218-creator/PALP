---
name: release-gate
description: Definition of Done D1-D12 checklist and release-gate runner. Use when preparing a release, reviewing a release-candidate PR, or running scripts/release_gate.py.
---

# Release Gate — Go/No-Go Workflow

## When to use

- Preparing a release branch (`release/x.y.z`)
- Final review of a feature PR before squash-merge
- Running `scripts/release_gate.py` locally or in CI (`workflow_dispatch` with `run_release_gate=true`)
- Gating a hotfix to production

## Definition of Done (D1–D12)

Every PR must satisfy each applicable item before merge. Source: `docs/DEFINITION_OF_DONE.md`.

| ID | Item | Verify by |
|----|------|-----------|
| D1 | Code review | ≥1 approval, 0 unresolved comments, CODEOWNERS satisfied |
| D2 | Unit tests pass | CI `backend-test` + `frontend-test` green, coverage not regressed |
| D3 | Integration tests pass | `pytest -m integration` green for affected flow |
| D4 | Negative tests | 401, 403, 404, 400 cases for every new endpoint |
| D5 | Analytics events | `events.services.audit_log` called for new user actions |
| D6 | Audit log | `AUDIT_SENSITIVE_PREFIXES` updated for PII paths |
| D7 | UI states | loading + empty + error + success rendered |
| D8 | Accessibility | WCAG 2.1 AA min, AAA on 3 critical pages (login, dashboard, learning loop) — `axe` clean |
| D9 | Monitoring | Prometheus metric + Grafana panel for critical paths |
| D10 | Documentation | docstring + relevant `docs/*.md` section if contracts changed |
| D11 | PO sign-off | for user-facing change |
| D12 | QA sign-off | per `docs/QA_STANDARD.md` checklist |

CI surfaces these via the `dod-hints` job (non-blocking but visible).

## Release-gate runner

```bash
# Local dry-run
python scripts/release_gate.py --format text

# JSON output for tooling
python scripts/release_gate.py --format json > release-gate-report.json

# CI: triggered via workflow_dispatch
gh workflow run ci.yml -f run_release_gate=true
```

Outputs: pass/fail per D1-D12 with cited evidence (test result, coverage XML, OpenAPI diff, axe report).

## Pre-release checklist

1. [ ] All open `release-blocker` labels resolved
2. [ ] CHANGELOG.md updated under `[Unreleased]` -> `[x.y.z] - YYYY-MM-DD`
3. [ ] `docs/POST_PILOT_ROADMAP.md` reviewed for scope creep
4. [ ] Migration tested on copy of prod DB (`scripts/backup_db.sh` + restore)
5. [ ] OpenAPI baseline updated: `backend/openapi/schema-baseline.yaml`
6. [ ] Lighthouse score not regressed (CI `lighthouse.yml`)
7. [ ] Mutation testing score >= 75% on 3 core modules (`adaptive`, `assessment`, `dashboard`)
8. [ ] Backup verification job `db-backup` last status: SUCCESS
9. [ ] Production env vars set: `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `PII_ENCRYPTION_KEY`, `DJANGO_DEBUG=False`
10. [ ] Health check `/api/health/` responds within 30s after deploy
11. [ ] Rollback runbook reviewed: `docs/RELEASE_RUNBOOK.md`

## Hotfix exception path

If skipping any D-item is required for hotfix:
- Document in PR body under "## Waivers"
- Cite incident ticket
- Tag `@palp/release-managers` for explicit approval
- Open follow-up issue to retire the waiver within 1 sprint

## Post-release

- Tag release: `git tag -s vX.Y.Z -m "..."` then `git push --tags`
- Create GitHub Release from tag with CHANGELOG section as body
- Verify Upptime status page (`.github/workflows/upptime.yml`) green for 24h
- Schedule post-release retro if any D-item was waived
