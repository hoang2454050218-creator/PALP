---
name: migration-runbook
description: Zero-downtime Django migration workflow. Use when adding columns, renaming, dropping, or backfilling data. Enforces backward-compat in line with PALP DoD D-items.
---

# Migration Runbook — Zero-Downtime Django Migrations

## When to use

- Running `python manage.py makemigrations <app>`
- Adding/removing model fields
- Renaming columns or tables
- Backfilling data from a script
- Reviewing PRs that include `backend/*/migrations/*.py`

## Hard rule

**Migrations must be backward-compatible with the previous deployed code.** PALP rolls forward (new code + new migration), then can roll back code while keeping the migration. So:
- Old code must still run with new schema for at least 1 release cycle.
- New required NOT NULL columns are forbidden in a single PR — split.

## Safe patterns

### Add a column

```python
# Migration 1 (release N)
migrations.AddField(
    model_name="student",
    name="study_streak_days",
    field=models.IntegerField(null=True, blank=True),  # nullable
)
```

```python
# Backfill (data migration, release N or N+1)
def backfill_streak(apps, schema_editor):
    Student = apps.get_model("accounts", "Student")
    Student.objects.filter(study_streak_days__isnull=True).update(study_streak_days=0)

migrations.RunPython(backfill_streak, reverse_code=migrations.RunPython.noop)
```

```python
# Migration 2 (release N+1, only after backfill verified)
migrations.AlterField(
    model_name="student",
    name="study_streak_days",
    field=models.IntegerField(default=0),  # NOT NULL with default
)
```

### Drop a column

```python
# Step 1 (release N): mark as nullable + stop writing in code
# Step 2 (release N+1): stop reading in code
# Step 3 (release N+2): RemoveField
```

Never drop in a single release.

### Rename a column

Use `RenameField` only if you can deploy with maintenance window (downtime). Otherwise:

1. Add new column with new name (nullable)
2. Backfill from old column
3. Update code to write to both, read from new
4. Wait 1+ release cycle
5. Update code to read/write new only
6. Drop old column (3 steps — see above)

### Add an index

```python
migrations.AddIndex(
    model_name="eventlog",
    index=models.Index(fields=["actor", "-timestamp"], name="palp_event_actor_ts_desc"),
)
```

For large tables (>1M rows), consider:
```python
migrations.RunSQL(
    "CREATE INDEX CONCURRENTLY palp_event_actor_ts_desc ON events_eventlog (actor_id, timestamp DESC);",
    reverse_sql="DROP INDEX IF EXISTS palp_event_actor_ts_desc;",
)
```
Postgres only. Wrap in `migrations.RunPython.noop` if SQLite test settings can't run.

### JSONField changes

JSON fields are schema-less in DB; treat content schema as code-managed:
- Validate in `clean()` and serializer
- Backfill via `RunPython`, never relying on DB DDL

## Workflow checklist

1. [ ] Run `python manage.py makemigrations --check --dry-run` locally — must pass with no diff
2. [ ] Inspect generated migration — does it match the safe pattern above?
3. [ ] Run `python manage.py migrate` on local + verify no error
4. [ ] Run full test suite: `pytest` (especially `@pytest.mark.recovery`)
5. [ ] Run `pytest -m data_qa` if migration touches data
6. [ ] Test rollback: `python manage.py migrate <app> <prev_number>` — must succeed
7. [ ] Add migration test in `backend/<app>/tests/test_migrations.py` for non-trivial RunPython
8. [ ] Commit migration in same PR as code that uses it (or document split-release plan)
9. [ ] CI `migration-check` job must pass
10. [ ] Update `docs/MIGRATION_RUNBOOK.md` if introducing a new pattern

## Forbidden in single PR

- Adding a required NOT NULL column without default + without prior nullable migration
- `RemoveField` of a column still referenced in current code
- `RenameField` on a table with active prod reads (use add-backfill-drop instead)
- Migration that takes a long-held lock on a >100k-row table without `CONCURRENTLY` index

## When in doubt

- Read `docs/MIGRATION_RUNBOOK.md`
- Look at recent migrations (e.g. `backend/events/migrations/0007_alter_eventlog_event_name.py`) for examples
- Ask in PR — migrations are P0 if they break prod
