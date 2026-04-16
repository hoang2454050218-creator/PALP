# PALP Migration Runbook

> **Scope**: All Django database migrations for the PALP platform
> **Owner**: Tech Lead / DevOps
> **Effective**: From Sprint 4 onward

---

## 1. Migration Graph -- Dependency Order

```
accounts (0001)
    |
    +---> curriculum (0001) ---> assessment (0001)
    |         |                       |
    |         +----> adaptive (0001)  |
    |         |                       |
    |         +----> dashboard (0001) |
    |         |                       |
    |         +----> events (0001)    |
    |
    +---> wellbeing (0001)
    +---> privacy (0001)

analytics (0001)  [no local app dependencies]
```

Always apply in this order when running from scratch:

1. `accounts`
2. `curriculum`
3. `assessment`
4. `adaptive`
5. `dashboard`
6. `analytics`
7. `events`
8. `wellbeing`
9. `privacy`

---

## 2. Backward-Compatible Migration Rules

### ALLOWED without coordination

| Operation | Example | Backward? |
|-----------|---------|-----------|
| Add nullable column | `AddField(null=True, blank=True)` | YES |
| Add column with default | `AddField(default=...)` | YES |
| Add index | `AddIndex(...)` | YES |
| Add constraint (partial/conditional) | `AddConstraint(condition=...)` | YES |
| Create new table | `CreateModel(...)` | YES |

### REQUIRES two-phase release

| Operation | Phase 1 (deploy code) | Phase 2 (migrate) |
|-----------|-----------------------|-------------------|
| Remove column | Stop reading column in code | `RemoveField` in next release |
| Remove table | Stop using model in code | `DeleteModel` in next release |
| Rename column | Add new column + backfill | Drop old column in next release |
| Make nullable -> non-null | Backfill all NULL values | `AlterField(null=False)` |

### NEVER in a single release

- Drop column that existing code still reads
- Change column type without backfill
- Add non-null column without default on table with existing data
- Delete data without confirmed backup

---

## 3. Data Migration Rules

Every `RunPython` migration MUST:

1. Have a `reverse_code` function (even if it's `migrations.RunPython.noop` for irreversible)
2. Be idempotent -- safe to run multiple times
3. Use `apps.get_model()` instead of direct model imports
4. Include a docstring explaining what it does and why
5. Have a size estimate for large tables (expected runtime)

```python
def forward_func(apps, schema_editor):
    """Backfill version=1 for existing MasteryState rows."""
    MasteryState = apps.get_model("adaptive", "MasteryState")
    MasteryState.objects.filter(version__isnull=True).update(version=1)

def reverse_func(apps, schema_editor):
    pass  # version field will be dropped by schema rollback

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(forward_func, reverse_func),
    ]
```

---

## 4. Rollback Strategy

### Per-migration rollback

```bash
# Rollback one migration
python manage.py migrate <app_label> <previous_migration_number>

# Example: rollback adaptive from 0002 to 0001
python manage.py migrate adaptive 0001_initial

# Rollback to zero (remove all tables for app)
python manage.py migrate <app_label> zero
```

### Release rollback procedure

```
1. IDENTIFY the failing migration
   python manage.py showmigrations | grep "\[ \]"

2. ROLLBACK migrations in REVERSE dependency order
   python manage.py migrate privacy <previous>
   python manage.py migrate wellbeing <previous>
   python manage.py migrate events <previous>
   python manage.py migrate dashboard <previous>
   python manage.py migrate adaptive <previous>
   python manage.py migrate assessment <previous>
   python manage.py migrate curriculum <previous>
   python manage.py migrate accounts <previous>

3. DEPLOY previous code version
   git checkout <previous_tag>
   docker-compose up -d --build

4. VERIFY
   python manage.py showmigrations  # all applied
   curl http://localhost:8000/api/health/  # 200 OK
```

### Rollback time budget

| Tables affected | Max acceptable rollback time |
|----------------|------------------------------|
| < 10K rows | < 30 seconds |
| 10K - 100K rows | < 5 minutes |
| > 100K rows | Requires scheduled maintenance window |

---

## 5. Pre-release Migration Checklist

### Before merging migration PR

- [ ] Migration runs cleanly on empty database (`migrate` from zero)
- [ ] Migration runs cleanly on prod-like snapshot
- [ ] `python manage.py migrate <app> <previous>` rollback succeeds
- [ ] No `RunSQL` without reverse SQL
- [ ] No `RunPython` without `reverse_code`
- [ ] `python manage.py showmigrations` shows no conflicts
- [ ] All new indexes verified with `EXPLAIN ANALYZE` on representative data
- [ ] Migration does not hold exclusive lock for > 5 seconds on large tables
- [ ] PR description includes: what changed, why, rollback steps

### Before deploying to production

- [ ] Full backup taken: `pg_dump -Fc palp > pre_migrate_$(date +%Y%m%d_%H%M).dump`
- [ ] Migration tested on staging with prod-like data volume
- [ ] Rollback tested on staging
- [ ] Monitoring alerts configured (Sentry, health endpoint)
- [ ] Team notified of deployment window
- [ ] Deployment log started

---

## 6. CI Migration Gate

### Automated checks (run on every PR)

```yaml
migration-check:
  steps:
    - name: Check for missing migrations
      run: python manage.py makemigrations --check --dry-run

    - name: Apply migrations on empty DB
      run: python manage.py migrate

    - name: Verify rollback to zero
      run: |
        python manage.py migrate accounts zero
        python manage.py migrate curriculum zero
        python manage.py migrate assessment zero
        python manage.py migrate adaptive zero
        python manage.py migrate dashboard zero
        python manage.py migrate analytics zero
        python manage.py migrate events zero
        python manage.py migrate wellbeing zero
        python manage.py migrate privacy zero

    - name: Re-apply all migrations
      run: python manage.py migrate

    - name: Run index benchmark
      run: python manage.py benchmark_indexes --fail-on-seqscan
```

---

## 7. Index Inventory

### Core indexes (must exist and be benchmarked)

| Table | Index | Query pattern |
|-------|-------|---------------|
| `palp_alert` | `idx_alert_student_status_sev` | Dashboard: filter alerts by student |
| `palp_alert` | `idx_alert_class_status_created` | Lecturer: active alerts per class |
| `palp_assessment_session` | `idx_session_student_assess_st` | Check active sessions |
| `palp_task_attempt` | `idx_attempt_student_task` | Latest attempt per task |
| `palp_task_attempt` | `idx_attempt_student_recent` | Early warning: recent activity |
| `palp_mastery_state` | `idx_mastery_student_updated` | Pathway: all mastery for student |
| `palp_wellbeing_nudge` | `idx_nudge_student_created` | Nudge history |
| `palp_event_log` | `palp_event__actor_t_idx` | Event queries by actor type |
| `palp_event_log` | `palp_event__course_idx` | Event queries by course |
| `palp_event_log` | `palp_event__actor_ev_idx` | Event queries by actor |
| `palp_event_log` | `palp_event__session_idx` | Session event timeline |
| `palp_consent_record` | (user, purpose, -created_at) | Latest consent per purpose |
| `palp_audit_log` | (actor, -created_at) | Audit trail by actor |

### Constraint inventory

| Table | Constraint | Type |
|-------|-----------|------|
| `palp_class_membership` | `uq_membership_student_class` | UNIQUE |
| `palp_lecturer_class_assignment` | `uq_lecturer_class` | UNIQUE |
| `palp_assessment_session` | `uq_one_active_session_per_student_assessment` | UNIQUE (partial: status=in_progress) |
| `palp_assessment_response` | `uq_response_session_question` | UNIQUE |
| `palp_learner_profile` | `uq_learner_profile_student_course` | UNIQUE |
| `palp_mastery_state` | `uq_mastery_student_concept` | UNIQUE |
| `palp_student_pathway` | `uq_pathway_student_course` | UNIQUE |
| `palp_enrollment` | `uq_enrollment_student_course_semester` | UNIQUE |
| `palp_concept` | `uq_concept_course_code` | UNIQUE |
| `palp_concept_prerequisite` | `uq_prereq_concept_prerequisite` | UNIQUE |
| `palp_concept_prerequisite` | `ck_prereq_no_self_loop` | CHECK |
| `palp_alert` | `uq_alert_dedupe_active` | UNIQUE (partial: status=active) |

---

## 8. Soft Delete Policy

| Model | Soft delete? | Reason |
|-------|-------------|--------|
| `User` | YES (`is_deleted` + `deleted_at`) | GDPR/privacy compliance; retain for audit |
| `EventLog` | NO (append-only) | Immutable audit trail; retention enforced by cron |
| `AuditLog` | NO (append-only) | Security compliance; never delete |
| `ConsentRecord` | NO (append-only) | Legal record of consent changes |
| All other models | NO (CASCADE from User) | Cascade handles cleanup; simplicity |

`User.objects` returns only active users via `ActiveUserManager`.
Use `User.all_objects` for admin access to soft-deleted users.

---

## 9. N+1 Query Prevention

### Tooling

- `nplusone` package enabled in test settings (`NPLUSONE_RAISE = True`)
- Tests will fail on any detected N+1 query

### Critical paths to monitor

| Endpoint | Required optimization |
|----------|-----------------------|
| `GET /dashboard/class/{id}/overview/` | `select_related("student")` + `prefetch_related("alerts")` |
| `GET /dashboard/alerts/` | `select_related("student", "concept", "milestone")` |
| `GET /adaptive/pathway/{course_id}/` | `select_related("current_concept", "current_milestone")` |
| `POST /adaptive/submit/` | Single MasteryState fetch + update |
| `GET /assessment/sessions/{sid}/` | `prefetch_related("responses__question")` |

---

## 10. Emergency Procedures

### Database corruption detected

```
1. STOP all application servers immediately
2. TAKE a backup of the corrupted state for investigation
3. RESTORE from the latest known-good backup
4. VERIFY data integrity using data QA checks (Section 6 in QA_STANDARD)
5. INVESTIGATE root cause before restarting
```

### Migration stuck / long-running

```
1. CHECK pg_stat_activity for lock waits
   SELECT pid, query, state, wait_event_type
   FROM pg_stat_activity
   WHERE state != 'idle';

2. If migration holds AccessExclusiveLock on large table:
   - DO NOT kill the process unless > 15 minutes
   - Monitor progress via pg_stat_progress_create_index (for index creation)

3. If deadlocked:
   SELECT pg_cancel_backend(<pid>);
   -- Then rollback and retry during low-traffic window
```
