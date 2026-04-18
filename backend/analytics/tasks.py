import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from datetime import timedelta
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q, Max, Min
from django.utils import timezone

from accounts.models import StudentClass
from dashboard.services import compute_early_warnings
from events.metrics import (
    BACKUP_AGE_SECONDS,
    BACKUP_LAST_RESTORE_DRILL_UNIX,
    CELERY_BEAT_LAST_PING_UNIX,
    CELERY_QUEUE_DEPTH,
    CELERY_TASK_TOTAL,
    DATA_QUALITY_SCORE,
    EVENT_COMPLETENESS,
    EVENT_DUPLICATION,
)
from events.models import EventLog

from .constants import (
    CELERY_DEFAULT_QUEUES,
    CELERY_HEALTH_PING_CACHE_KEY,
    CELERY_HEALTH_PING_TTL_SECONDS,
)
from .models import DataQualityLog, KPIDefinition, KPILineageLog, KPIVersion

logger = logging.getLogger("palp")

REQUIRED_FIELDS = [
    "event_name",
    "event_version",
    "timestamp_utc",
    "actor_type",
    "session_id",
    "device_type",
    "source_page",
    "request_id",
]

LEARNING_REQUIRED_FIELDS = [
    "concept_id",
    "task_id",
    "difficulty_level",
    "attempt_number",
    "mastery_before",
    "mastery_after",
]

EVENT_GAP_THRESHOLD_HOURS = 24
VOLUME_DROP_SUSPICIOUS_RATIO = 0.3


@shared_task
def run_nightly_early_warnings():
    classes = StudentClass.objects.all()
    total_alerts = 0
    for sc in classes:
        try:
            alerts = compute_early_warnings(sc.id)
            total_alerts += len(alerts)
            CELERY_TASK_TOTAL.labels(
                task_name="early_warnings", status="success"
            ).inc()
        except Exception:
            CELERY_TASK_TOTAL.labels(
                task_name="early_warnings", status="failure"
            ).inc()
            logger.exception("Early warning failed for class %s", sc.id)
    logger.info(
        "Nightly early warnings: %d new alerts across %d classes",
        total_alerts, classes.count(),
    )
    return total_alerts


@shared_task(name="analytics.tasks.celery_health_ping")
def celery_health_ping():
    """Heartbeat written by Celery Beat so the deep health endpoint can verify
    the scheduler is alive. Reads from `palp:celery:health_ping` cache key.
    """
    now_unix = time.time()
    cache.set(CELERY_HEALTH_PING_CACHE_KEY, str(now_unix), CELERY_HEALTH_PING_TTL_SECONDS)
    CELERY_BEAT_LAST_PING_UNIX.set(now_unix)
    CELERY_TASK_TOTAL.labels(task_name="celery_health_ping", status="success").inc()
    return {"timestamp": now_unix}


@shared_task(name="analytics.tasks.check_queue_backlog")
def check_queue_backlog():
    """Sample the Celery broker queue depth and expose it via Prometheus gauge.

    Uses the broker URL directly (Redis LLEN) for accuracy. Logs warnings when
    crossing PALP_QUEUE_ALERT thresholds. Returns a dict mapping queue name to
    pending task count.
    """
    try:
        import redis as redis_lib
    except ImportError:
        logger.warning("redis-py not available; skipping queue backlog check")
        return {"status": "skipped", "reason": "redis_not_available"}

    broker_url = getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/1")
    thresholds = getattr(settings, "PALP_QUEUE_ALERT", {})
    warn = thresholds.get("WARN", 50)
    critical = thresholds.get("CRITICAL", 200)

    queue_names = getattr(settings, "PALP_CELERY_MONITORED_QUEUES", CELERY_DEFAULT_QUEUES)
    depths = {}
    try:
        client = redis_lib.from_url(broker_url, socket_timeout=3)
        for queue in queue_names:
            depth = int(client.llen(queue) or 0)
            depths[queue] = depth
            CELERY_QUEUE_DEPTH.labels(queue=queue).set(depth)

            if depth >= critical:
                logger.error(
                    "Celery queue %s critical: %d tasks pending (threshold %d)",
                    queue, depth, critical,
                )
            elif depth >= warn:
                logger.warning(
                    "Celery queue %s elevated: %d tasks pending (threshold %d)",
                    queue, depth, warn,
                )
        CELERY_TASK_TOTAL.labels(
            task_name="check_queue_backlog", status="success",
        ).inc()
    except Exception as exc:
        logger.exception("Queue backlog check failed: %s", exc)
        CELERY_TASK_TOTAL.labels(
            task_name="check_queue_backlog", status="failure",
        ).inc()
        return {"status": "error", "error": str(exc)}

    return {"status": "ok", "depths": depths}


@shared_task(name="analytics.tasks.update_backup_age_metric")
def update_backup_age_metric():
    """Read sentinel file written by backup_db.sh and expose backup freshness.

    The backup container shares the BACKUP_DIR volume; the Django process
    needs read access to the same mount (configured in docker-compose.prod.yml).
    """
    backup_dir = Path(getattr(settings, "PALP_BACKUP_DIR", "/backups"))
    sentinel = backup_dir / ".last_backup_unix"
    if not sentinel.exists():
        logger.warning("Backup sentinel %s missing; cannot compute age", sentinel)
        return {"status": "missing", "sentinel": str(sentinel)}
    try:
        last_unix = float(sentinel.read_text().strip())
    except (ValueError, OSError) as exc:
        logger.error("Cannot read backup sentinel %s: %s", sentinel, exc)
        return {"status": "error", "error": str(exc)}

    age_seconds = time.time() - last_unix
    BACKUP_AGE_SECONDS.set(age_seconds)
    CELERY_TASK_TOTAL.labels(
        task_name="update_backup_age_metric", status="success",
    ).inc()
    return {"status": "ok", "age_seconds": age_seconds}


@shared_task(name="analytics.tasks.weekly_restore_drill")
def weekly_restore_drill():
    """Verify the latest backup is restorable end-to-end.

    Steps:
        1. Read latest backup metadata.
        2. Decrypt with GPG passphrase if encrypted.
        3. Create an ephemeral Postgres database.
        4. Run psql to restore the dump.
        5. Run sanity COUNT queries against critical tables.
        6. Drop the ephemeral database, regardless of outcome.
        7. Update Prometheus metric on success.

    Designed to be safe to skip in non-production environments where the
    backup volume is not mounted -- returns ``{"status": "skipped"}`` so it
    never blocks Celery beat.
    """
    backup_dir = Path(getattr(settings, "PALP_BACKUP_DIR", "/backups"))
    meta_file = backup_dir / ".last_backup_meta.json"
    if not meta_file.exists():
        logger.info("No backup metadata at %s; skipping restore drill", meta_file)
        return {"status": "skipped", "reason": "no_backup_metadata"}

    try:
        meta = json.loads(meta_file.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Cannot read backup metadata: %s", exc)
        CELERY_TASK_TOTAL.labels(
            task_name="weekly_restore_drill", status="failure",
        ).inc()
        return {"status": "error", "error": str(exc)}

    artifact_path = Path(meta.get("artifact_path", ""))
    if not artifact_path.exists():
        logger.error("Backup artifact %s missing on disk", artifact_path)
        CELERY_TASK_TOTAL.labels(
            task_name="weekly_restore_drill", status="failure",
        ).inc()
        return {"status": "error", "reason": "artifact_missing", "path": str(artifact_path)}

    pg_host = os.environ.get("POSTGRES_HOST", "db")
    pg_port = os.environ.get("POSTGRES_PORT", "5432")
    pg_user = os.environ.get("POSTGRES_USER", "palp")
    pg_password = os.environ.get("POSTGRES_PASSWORD", "")
    target_db = f"palp_restore_drill_{int(time.time())}"

    work_dir = Path(tempfile.mkdtemp(prefix="palp-restore-"))
    sql_file = work_dir / "dump.sql.gz"
    drill_status = "started"
    detail: dict = {}
    env = os.environ.copy()
    env["PGPASSWORD"] = pg_password

    try:
        if meta.get("encrypted"):
            passphrase = os.environ.get("BACKUP_GPG_PASSPHRASE", "")
            if not passphrase:
                logger.warning("Encrypted backup but BACKUP_GPG_PASSPHRASE missing")
                drill_status = "skipped"
                detail = {"reason": "missing_gpg_passphrase"}
                return {"status": drill_status, **detail}
            # Pass the passphrase via stdin (--passphrase-fd 0) instead of as
            # an argv flag so it never appears in `ps`/proc/cmdline or in
            # CI/container logs that capture argv.
            decrypt_proc = subprocess.run(
                [
                    "gpg", "--batch", "--yes", "--pinentry-mode", "loopback",
                    "--passphrase-fd", "0",
                    "--output", str(sql_file),
                    "--decrypt", str(artifact_path),
                ],
                input=passphrase,
                capture_output=True, text=True, timeout=600,
            )
            if decrypt_proc.returncode != 0:
                drill_status = "failure"
                detail = {"stage": "decrypt", "stderr": decrypt_proc.stderr[:500]}
                return {"status": drill_status, **detail}
        else:
            shutil.copy(artifact_path, sql_file)

        create_proc = subprocess.run(
            [
                "psql",
                "-h", pg_host, "-p", pg_port, "-U", pg_user,
                "-d", "postgres",
                "-c", f'CREATE DATABASE "{target_db}" TEMPLATE template0',
            ],
            capture_output=True, text=True, env=env, timeout=60,
        )
        if create_proc.returncode != 0:
            drill_status = "failure"
            detail = {"stage": "create_db", "stderr": create_proc.stderr[:500]}
            return {"status": drill_status, **detail}

        restore_cmd = (
            f"gunzip -c {sql_file} | "
            f"psql -h {pg_host} -p {pg_port} -U {pg_user} -d {target_db}"
        )
        restore_proc = subprocess.run(
            ["bash", "-c", restore_cmd],
            capture_output=True, text=True, env=env, timeout=900,
        )
        if restore_proc.returncode != 0:
            drill_status = "failure"
            detail = {"stage": "restore", "stderr": restore_proc.stderr[:500]}
            return {"status": drill_status, **detail}

        sanity_sql = (
            "SELECT 'accounts_user' AS t, COUNT(*) FROM accounts_user "
            "UNION ALL SELECT 'palp_event_log', COUNT(*) FROM palp_event_log "
            "UNION ALL SELECT 'palp_mastery_state', COUNT(*) FROM palp_mastery_state;"
        )
        sanity_proc = subprocess.run(
            ["psql", "-h", pg_host, "-p", pg_port, "-U", pg_user,
             "-d", target_db, "-At", "-F", "|", "-c", sanity_sql],
            capture_output=True, text=True, env=env, timeout=60,
        )
        if sanity_proc.returncode != 0:
            drill_status = "failure"
            detail = {"stage": "sanity", "stderr": sanity_proc.stderr[:500]}
            return {"status": drill_status, **detail}

        row_counts = {}
        for line in sanity_proc.stdout.strip().splitlines():
            if "|" in line:
                name, count_str = line.split("|", 1)
                try:
                    row_counts[name] = int(count_str)
                except ValueError:
                    pass

        drill_status = "ok"
        detail = {"row_counts": row_counts, "target_db": target_db}
        BACKUP_LAST_RESTORE_DRILL_UNIX.set(time.time())
        CELERY_TASK_TOTAL.labels(
            task_name="weekly_restore_drill", status="success",
        ).inc()

        # Persist sentinel for release_gate auto-check.
        sentinel = backup_dir / ".last_restore_drill_unix"
        try:
            sentinel.write_text(str(int(time.time())))
        except OSError as exc:
            logger.warning("Could not write restore drill sentinel: %s", exc)

        DataQualityLog.objects.create(
            source="weekly_restore_drill",
            total_records=sum(row_counts.values()),
            quality_score=100.0,
            details={"row_counts": row_counts, "artifact": meta.get("artifact")},
        )

        return {"status": drill_status, **detail}

    except subprocess.TimeoutExpired as exc:
        drill_status = "failure"
        detail = {"stage": exc.cmd[:60] if isinstance(exc.cmd, str) else "unknown",
                  "reason": "timeout"}
        return {"status": drill_status, **detail}
    except Exception as exc:
        logger.exception("Restore drill failed unexpectedly: %s", exc)
        drill_status = "failure"
        detail = {"stage": "unexpected", "error": str(exc)}
        return {"status": drill_status, **detail}
    finally:
        if drill_status not in ("ok",):
            CELERY_TASK_TOTAL.labels(
                task_name="weekly_restore_drill", status="failure",
            ).inc()
        try:
            subprocess.run(
                ["psql", "-h", pg_host, "-p", pg_port, "-U", pg_user,
                 "-d", "postgres",
                 "-c", f'DROP DATABASE IF EXISTS "{target_db}"'],
                capture_output=True, text=True, env=env, timeout=60,
            )
        except Exception:
            logger.warning("Failed to drop temp DB %s", target_db)
        shutil.rmtree(work_dir, ignore_errors=True)


@shared_task
def generate_weekly_report(class_id=None, week_number: int = 1):
    from accounts.models import StudentClass
    from .services import generate_pilot_report

    if class_id is not None:
        try:
            report = generate_pilot_report(class_id, week_number)
            CELERY_TASK_TOTAL.labels(
                task_name="weekly_report", status="success"
            ).inc()
            logger.info("Generated weekly report: %s", report.title)
            return report.id
        except Exception:
            CELERY_TASK_TOTAL.labels(
                task_name="weekly_report", status="failure"
            ).inc()
            logger.exception("Weekly report failed for class %d", class_id)
            raise

    report_ids = []
    for sc in StudentClass.objects.all():
        try:
            report = generate_pilot_report(sc.id, week_number)
            report_ids.append(report.id)
            CELERY_TASK_TOTAL.labels(
                task_name="weekly_report", status="success"
            ).inc()
        except Exception:
            CELERY_TASK_TOTAL.labels(
                task_name="weekly_report", status="failure"
            ).inc()
            logger.exception("Weekly report failed for class %d", sc.id)
    return report_ids


@shared_task
def kpi_integrity_audit():
    """
    Daily audit that enforces KPI integrity:
    1. Raw data traceability -- every KPI must reach its source events
    2. Definition drift -- locked KPIs must not change mid-pilot
    3. Event tracking gaps -- no >24h gap in source event streams
    4. Tracking bug detection -- KPI improving while event volume drops
    """
    kpi_defs = KPIDefinition.objects.all()
    if not kpi_defs.exists():
        logger.warning("KPI integrity audit: no KPI definitions found.")
        return {"status": "skipped", "reason": "no_definitions"}

    now = timezone.now()
    window_start = now - timedelta(days=7)
    findings = {}

    for kpi_def in kpi_defs:
        kpi_findings = {}

        kpi_findings["traceability"] = _check_traceability(kpi_def, window_start, now)
        kpi_findings["definition_drift"] = _check_definition_drift(kpi_def)
        kpi_findings["event_gaps"] = _check_event_gaps(kpi_def, window_start, now)
        kpi_findings["tracking_bug"] = _check_tracking_bug(kpi_def)

        has_failure = any(
            f.get("status") == "FAIL" for f in kpi_findings.values()
        )
        kpi_findings["overall"] = "FAIL" if has_failure else "PASS"
        findings[kpi_def.code] = kpi_findings

    overall_pass = all(f["overall"] == "PASS" for f in findings.values())

    DataQualityLog.objects.create(
        source="kpi_integrity_audit",
        total_records=len(kpi_defs),
        missing_values=sum(
            1 for f in findings.values() if f["overall"] == "FAIL"
        ),
        quality_score=100.0 if overall_pass else 0.0,
        details=findings,
    )

    if not overall_pass:
        failed = [c for c, f in findings.items() if f["overall"] == "FAIL"]
        logger.error("KPI integrity FAIL for: %s", ", ".join(failed))
    else:
        logger.info("KPI integrity audit: all %d KPIs PASS.", len(kpi_defs))

    CELERY_TASK_TOTAL.labels(
        task_name="kpi_integrity_audit", status="success",
    ).inc()

    return {"status": "PASS" if overall_pass else "FAIL", "details": findings}


def _check_traceability(kpi_def, start, end):
    if kpi_def.code == "csat_score":
        return {"status": "PASS", "note": "manual_entry_kpi"}

    source_events = kpi_def.source_events or []
    if not source_events:
        return {"status": "FAIL", "reason": "no_source_events_defined"}

    missing = []
    for event_name in source_events:
        count = EventLog.objects.filter(
            event_name=event_name,
            timestamp_utc__range=(start, end),
        ).count()
        if count == 0:
            missing.append(event_name)

    if missing:
        return {
            "status": "FAIL",
            "reason": "no_raw_data_for_source_events",
            "missing_events": missing,
        }
    return {"status": "PASS"}


def _check_definition_drift(kpi_def):
    if not kpi_def.is_locked:
        return {"status": "PASS", "note": "not_locked_yet"}

    latest_version = KPIVersion.objects.filter(kpi=kpi_def).order_by("-version").first()
    if not latest_version:
        return {"status": "PASS", "note": "no_previous_versions"}

    snapshot = latest_version.definition_snapshot
    drifted_fields = []
    for field in KPIDefinition.LOCKED_FIELDS:
        current_val = getattr(kpi_def, field)
        snapshot_val = snapshot.get(field)
        if current_val != snapshot_val:
            drifted_fields.append({
                "field": field,
                "locked_value": snapshot_val,
                "current_value": current_val,
            })

    if drifted_fields:
        return {
            "status": "FAIL",
            "reason": "definition_changed_after_lock",
            "drifted_fields": drifted_fields,
        }
    return {"status": "PASS"}


def _check_event_gaps(kpi_def, start, end):
    if kpi_def.code == "csat_score":
        return {"status": "PASS", "note": "manual_entry_kpi"}

    source_events = kpi_def.source_events or []
    if not source_events:
        return {"status": "FAIL", "reason": "no_source_events_defined"}

    gaps_found = []
    for event_name in source_events:
        events = (
            EventLog.objects.filter(
                event_name=event_name,
                timestamp_utc__range=(start, end),
            )
            .order_by("timestamp_utc")
            .values_list("timestamp_utc", flat=True)
        )
        timestamps = list(events)
        if len(timestamps) < 2:
            continue

        for i in range(1, len(timestamps)):
            gap_hours = (timestamps[i] - timestamps[i - 1]).total_seconds() / 3600
            if gap_hours > EVENT_GAP_THRESHOLD_HOURS:
                gaps_found.append({
                    "event": event_name,
                    "gap_hours": round(gap_hours, 1),
                    "from": timestamps[i - 1].isoformat(),
                    "to": timestamps[i].isoformat(),
                })

    if gaps_found:
        return {
            "status": "FAIL",
            "reason": "event_stream_gap_exceeds_threshold",
            "gaps": gaps_found[:5],
        }
    return {"status": "PASS"}


def _check_tracking_bug(kpi_def):
    recent_logs = KPILineageLog.objects.filter(
        kpi=kpi_def,
    ).order_by("-week_number")[:2]

    if len(recent_logs) < 2:
        return {"status": "PASS", "note": "insufficient_history"}

    current, previous = recent_logs[0], recent_logs[1]

    if previous.event_count == 0:
        return {"status": "PASS", "note": "no_previous_events"}

    volume_change = (current.event_count - previous.event_count) / previous.event_count

    direction = kpi_def.target_direction
    if direction == KPIDefinition.TargetDirection.INCREASE:
        improved = current.computed_value > previous.computed_value
    elif direction == KPIDefinition.TargetDirection.DECREASE:
        improved = current.computed_value < previous.computed_value
    else:
        improved = abs(current.computed_value - kpi_def.target_value) < abs(
            previous.computed_value - kpi_def.target_value
        )

    if improved and volume_change < -VOLUME_DROP_SUSPICIOUS_RATIO:
        return {
            "status": "FAIL",
            "reason": "kpi_improved_but_event_volume_dropped",
            "event_volume_change_pct": round(volume_change * 100, 1),
            "value_previous": previous.computed_value,
            "value_current": current.computed_value,
            "week_previous": previous.week_number,
            "week_current": current.week_number,
        }
    return {"status": "PASS"}


@shared_task
def audit_event_completeness():
    """
    Hourly audit: check that events have all required fields populated.
    Target: >= 99.5% completeness.
    """
    window = timezone.now() - timedelta(hours=1)
    recent = EventLog.objects.filter(timestamp_utc__gte=window)
    total = recent.count()

    if total == 0:
        EVENT_COMPLETENESS.set(1.0)
        return {"total": 0, "completeness": 1.0}

    incomplete_q = Q()
    for field in REQUIRED_FIELDS:
        if field == "request_id":
            continue
        incomplete_q |= Q(**{f"{field}__exact": ""}) | Q(**{f"{field}__isnull": True})

    incomplete_general = recent.filter(incomplete_q).count()

    learning_events = recent.filter(event_name__in=[
        EventLog.EventName.ASSESSMENT_COMPLETED,
        EventLog.EventName.MICRO_TASK_COMPLETED,
        EventLog.EventName.CONTENT_INTERVENTION,
        EventLog.EventName.RETRY_TRIGGERED,
    ])
    learning_total = learning_events.count()

    learning_incomplete = 0
    if learning_total > 0:
        learning_q = Q()
        for field in LEARNING_REQUIRED_FIELDS:
            learning_q |= Q(**{f"{field}__isnull": True})
        learning_incomplete = learning_events.filter(learning_q).count()

    total_incomplete = incomplete_general + learning_incomplete
    completeness = 1 - (total_incomplete / (total + learning_total)) if (total + learning_total) > 0 else 1.0
    completeness = round(completeness, 5)

    EVENT_COMPLETENESS.set(completeness)

    threshold = settings.PALP_EVENT_COMPLETENESS_THRESHOLD
    if completeness < threshold:
        logger.warning(
            "Event completeness %.3f%% below threshold %.1f%%",
            completeness * 100, threshold * 100,
        )

    DataQualityLog.objects.create(
        source="event_completeness_audit",
        total_records=total,
        missing_values=total_incomplete,
        quality_score=completeness * 100,
        details={
            "window_hours": 1,
            "general_incomplete": incomplete_general,
            "learning_incomplete": learning_incomplete,
            "learning_total": learning_total,
        },
    )
    DATA_QUALITY_SCORE.labels(source="event_completeness").set(completeness * 100)

    CELERY_TASK_TOTAL.labels(
        task_name="event_completeness_audit", status="success"
    ).inc()

    return {"total": total, "completeness": completeness}


@shared_task
def audit_event_duplication():
    """
    Hourly audit: detect duplicated events.
    Target: <= 0.1% duplication.
    """
    window = timezone.now() - timedelta(hours=1)
    recent = EventLog.objects.filter(timestamp_utc__gte=window)
    total = recent.count()

    if total == 0:
        EVENT_DUPLICATION.set(0.0)
        return {"total": 0, "duplication_ratio": 0.0}

    duplicates = (
        recent
        .exclude(idempotency_key__isnull=True)
        .exclude(idempotency_key="")
        .values("idempotency_key")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
    )
    dup_count = sum(d["cnt"] - 1 for d in duplicates)
    dup_ratio = dup_count / total if total > 0 else 0.0
    dup_ratio = round(dup_ratio, 5)

    EVENT_DUPLICATION.set(dup_ratio)

    threshold = settings.PALP_EVENT_DUPLICATION_THRESHOLD
    if dup_ratio > threshold:
        logger.warning(
            "Event duplication %.4f%% above threshold %.2f%%",
            dup_ratio * 100, threshold * 100,
        )

    DataQualityLog.objects.create(
        source="event_duplication_audit",
        total_records=total,
        outliers_detected=dup_count,
        quality_score=(1 - dup_ratio) * 100,
        details={
            "window_hours": 1,
            "duplicate_count": dup_count,
            "unique_keys_with_dups": len(duplicates),
        },
    )
    DATA_QUALITY_SCORE.labels(source="event_duplication").set((1 - dup_ratio) * 100)

    CELERY_TASK_TOTAL.labels(
        task_name="event_duplication_audit", status="success"
    ).inc()

    return {"total": total, "duplication_ratio": dup_ratio}


@shared_task
def audit_orphan_events():
    """
    Hourly audit: detect events without valid actor mapping
    or confirmation-required events missing confirmation.
    """
    window = timezone.now() - timedelta(hours=1)
    confirmed_cutoff = timezone.now() - timedelta(minutes=5)

    orphan_actor = EventLog.objects.filter(
        timestamp_utc__gte=window,
        actor__isnull=True,
    ).exclude(
        actor_type=EventLog.ActorType.SYSTEM,
    ).count()

    unconfirmed = EventLog.objects.filter(
        timestamp_utc__gte=window,
        timestamp_utc__lte=confirmed_cutoff,
        event_name__in=settings.PALP_EVENTS_REQUIRING_CONFIRMATION,
        confirmed_at__isnull=True,
    ).count()

    if orphan_actor > 0:
        logger.warning("Found %d orphan events without valid actor", orphan_actor)

    if unconfirmed > 0:
        logger.warning(
            "Found %d unconfirmed events requiring BE confirmation", unconfirmed
        )

    DataQualityLog.objects.create(
        source="orphan_event_audit",
        total_records=EventLog.objects.filter(timestamp_utc__gte=window).count(),
        outliers_detected=orphan_actor + unconfirmed,
        quality_score=100.0 if (orphan_actor + unconfirmed) == 0 else 0.0,
        details={
            "window_hours": 1,
            "orphan_actor_count": orphan_actor,
            "unconfirmed_count": unconfirmed,
        },
    )

    CELERY_TASK_TOTAL.labels(
        task_name="orphan_event_audit", status="success"
    ).inc()

    return {
        "orphan_actor": orphan_actor,
        "unconfirmed": unconfirmed,
    }
