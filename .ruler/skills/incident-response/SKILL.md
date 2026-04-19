---
name: incident-response
description: Privacy/security incident workflow with 48-hour SLA. Use when responding to PII leak, RBAC bypass, encryption failure, or any privacy alert.
---

# Incident Response — Privacy & Security

## When to use

- Privacy/security alert from Grafana, Sentry, or user report
- Any of: PII leak, RBAC bypass, encryption failure, data export bug, GDPR-style deletion failure
- "User X can see User Y's data" report (P0)
- Failed retention enforcement or audit trail gap

## SLA

`PALP_PRIVACY.SLA_HOURS = 48` from incident detection to resolution + notification. Hourly check via Celery beat (`privacy.tasks.check_incident_sla`) escalates if breached.

## Severity ladder

| Level | Examples | Response |
|-------|----------|----------|
| **P0** | PII leak in production, RBAC bypass, key compromise, mass data exposure | Page on-call within 15 min, public disclosure if user data affected |
| **P1** | Privacy bug affecting <100 users, audit trail gap, single failed export | Fix within 24h, internal post-mortem |
| **P2** | UI bug exposing non-PII (analytics IDs), retention 1-day late | Fix in next sprint, no disclosure |
| **P3** | Documentation error, test gap, minor logging issue | Backlog |

## Workflow (P0/P1)

### 1. Detect & contain (target: 15 min for P0)

- Acknowledge alert in `#palp-incidents` Slack/Discord
- Identify affected users (query `AuditLog` for path + time range)
- Contain: disable endpoint via feature flag, revoke compromised key, block suspicious IP
- Snapshot DB state if forensics needed: `pg_dump -Fc -t affected_table`

### 2. Triage (target: 1h)

- Assign incident commander (rotates per on-call)
- Open tracking issue in `palp-incidents` GitHub project (private repo if PII details)
- Tag P0/P1, link to alert + logs + reproduction
- Notify DPO (Data Protection Officer) if PII affected
- Post status to status page (Upptime) if user-facing

### 3. Investigate (target: 12h)

- Pull `AuditLog` rows for affected paths + time window
- Check `EventLog` for related user actions
- Search Sentry for stack traces
- Review code changes in last 7 days touching affected code path
- Identify root cause + scope (how many users, how much data, how long)

### 4. Fix & test

- Hotfix branch from `main`: `fix/incident-<id>-<short-desc>`
- Add regression test (must reproduce the bug pre-fix)
- Run `pytest -m security` + `pytest -m integration`
- PR with `incident: P0` label — fast-track review (1 reviewer, no PO sign-off needed for hotfix)
- Deploy via `release/hotfix-x.y.z` workflow
- Verify in prod: re-run reproduction, confirm 200/403/404 as expected

### 5. Post-mortem (target: 7 days)

Write blameless post-mortem in `docs/incidents/YYYY-MM-DD-<slug>.md`:

```markdown
# Incident: <title>

- **Date detected**: YYYY-MM-DD HH:MM (Asia/Ho_Chi_Minh)
- **Severity**: P0 / P1
- **Duration**: detected -> resolved
- **Affected users**: N (X% of MAU)
- **Data exposed**: type + volume

## Timeline
- HH:MM Alert fired
- HH:MM Acknowledged by <on-call>
- HH:MM Root cause identified
- HH:MM Hotfix deployed
- HH:MM Verified in prod

## Root cause
Single sentence + technical detail

## What went well
- ...

## What went wrong
- ...

## Action items
- [ ] AI-1 (owner, due date)
- [ ] AI-2 ...
```

### 6. Notify (if PII affected)

- Email affected users within 72h (GDPR/Vietnamese decree)
- Public disclosure if >1000 users affected
- Notify regulators per local law (DPO handles)

## Reference paths

- Sensitive endpoint list: `AUDIT_SENSITIVE_PREFIXES` in `backend/palp/settings/base.py`
- Audit log: `backend/privacy/models.py::AuditEntry`
- Consent middleware: `backend/privacy/middleware.py::ConsentGateMiddleware`
- Incident SLA checker: `backend/privacy/tasks.py::check_incident_sla`
- Runbook: `docs/PRIVACY_INCIDENT.md`
- DPO contact: `security@palp.dau.edu.vn`

## Hard rules

- **Never** discuss PII details in public Slack/Discord channels — use the private incident channel.
- **Never** share screenshots with user data unless redacted.
- **Always** capture forensic snapshot before modifying production data.
- **Always** add a regression test that would catch the same bug.
- **Never** close an incident without a post-mortem (P0/P1).

## Quick commands

```bash
# Pull audit log for affected path
docker exec cnhnha-backend-1 python manage.py shell -c "
from privacy.models import AuditEntry
qs = AuditEntry.objects.filter(path__startswith='/api/auth/profile/', timestamp__gte='2026-01-01')
for e in qs: print(e.user_id, e.path, e.status, e.timestamp)
"

# Disable endpoint via feature flag
docker exec cnhnha-backend-1 python manage.py shell -c "
from waffle.models import Switch
Switch.objects.update_or_create(name='disable_profile_endpoint', defaults={'active': True})
"

# Run privacy regression suite
docker exec cnhnha-backend-1 pytest backend/privacy/ -m security -v
```
