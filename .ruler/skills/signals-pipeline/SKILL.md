---
name: signals-pipeline
description: Behavioral signal pipeline (frontend SDK + ingest backend + rollup). Use when modifying focus/idle/tab/frustration/idle detectors, signals app models/views, or signal-derived RiskScore inputs.
---

# Signals Pipeline — Behavioral Signal Workflow

## When to use

- Editing `frontend/src/lib/sensing/` (focus-tracker, idle-detector, tab-switch, frustration-detector, ingest-buffer)
- Editing `backend/signals/` (models, views, services, scoring, tasks)
- Adding new signal type that goes into `SignalSession` rollup
- Modifying ingest endpoint `/api/signals/ingest/`
- Tuning thresholds in `PALP_SIGNALS` settings

## Hard invariants

1. **Consent gated**: ingest endpoint MUST 403 if user lacks `behavioral_signals` consent. Frontend SDK MUST not start without consent.
2. **No PII in payload**: signal events carry only IDs + timing + metric values. Never URLs with query params, never page text, never form input content.
3. **Sampling consistent**: high-volume events (`tab_switched` 0.5, `affect_keystroke_window` 0.1) — sample decision happens at ingest, log `sampled` flag.
4. **Rollup not raw**: `EventLog` stores discrete events; `SignalSession` stores 5-min rollup. Don't query `EventLog` for analytics — query `SignalSession`.
5. **Idempotency**: ingest with same `(user, session_id, client_ts, event_type)` within 5 min = dedup, not duplicate.

## Frontend SDK pattern

```typescript
// frontend/src/lib/sensing/index.ts
import { hasConsent } from "@/lib/privacy/consent";

export function initSensing(userId: number, sessionId: string) {
  if (!hasConsent("behavioral_signals")) {
    return { stop: () => {} };
  }
  
  const buffer = new IngestBuffer({ batchSize: 50, flushMs: 5000 });
  
  const focusTracker = new FocusTracker(buffer);
  const idleDetector = new IdleDetector(buffer, { thresholdMs: 5000 });
  const tabSwitchTracker = new TabSwitchTracker(buffer);
  const frustrationDetector = new FrustrationDetector(buffer);
  
  // ... start all
  
  return {
    stop: () => {
      focusTracker.stop();
      idleDetector.stop();
      tabSwitchTracker.stop();
      frustrationDetector.stop();
      buffer.flush();
    },
  };
}
```

Mount in [`frontend/src/app/(student)/layout.tsx`](frontend/src/app/(student)/layout.tsx) via `useSensing()` hook.

## Backend ingest pattern

```python
# backend/signals/views.py
class SignalIngestView(APIView):
    permission_classes = [IsStudent, ConsentBehavioralSignals]
    throttle_scope = "signals_ingest"
    
    @extend_schema(...)
    def post(self, request):
        serializer = SignalBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Defer to Celery (don't block ingest response)
        process_signals_batch.delay(
            user_id=request.user.id,
            events=serializer.validated_data["events"],
            session_id=serializer.validated_data["session_id"],
        )
        return Response({"queued": len(serializer.validated_data["events"])}, status=202)
```

```python
# backend/signals/services.py
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_signals_batch(self, user_id, events, session_id):
    """Idempotent: re-running with same input produces same result."""
    user = User.objects.get(pk=user_id)
    
    for event in events:
        # Validate per JSON schema (docs/SIGNAL_TAXONOMY.md)
        schema = get_schema(event["event_name"])
        try:
            jsonschema.validate(event["properties"], schema)
        except jsonschema.ValidationError as e:
            logger.warning("Invalid signal event", extra={"event": event, "error": str(e)})
            continue
        
        # Idempotency check
        if EventLog.objects.filter(
            actor=user,
            event_name=event["event_name"],
            client_timestamp=event["client_timestamp"],
        ).exists():
            continue
        
        # Sample decision (per PALP_EVENT_SAMPLING)
        sample_rate = settings.PALP_EVENT_SAMPLING.get(event["event_name"], 1.0)
        if random.random() > sample_rate:
            continue
        
        emit_event(
            event_name=event["event_name"],
            actor=user,
            session_id=session_id,
            properties=event["properties"],
        )
    
    # Trigger rollup (5-min window)
    rollup_signals_5min.delay(user_id, session_id)
```

## Rollup pattern

```python
# backend/signals/tasks.py
@shared_task
def rollup_signals_5min(user_id, session_id):
    """Aggregate raw events into SignalSession 5-min window."""
    user = User.objects.get(pk=user_id)
    now = timezone.now()
    window_start = now - timedelta(minutes=5)
    
    raw_events = EventLog.objects.filter(
        actor=user,
        session_id=session_id,
        timestamp_utc__gte=window_start,
        timestamp_utc__lt=now,
    )
    
    # Compute aggregates
    aggregates = {
        "focus_minutes": compute_focus_minutes(raw_events),
        "idle_minutes": compute_idle_minutes(raw_events),
        "tab_switches": raw_events.filter(event_name="tab_switched").count(),
        "hint_count": raw_events.filter(event_name="hint_requested").count(),
        "frustration_score": compute_frustration_score(raw_events),
    }
    
    # Upsert
    SignalSession.objects.update_or_create(
        student=user,
        session_id=session_id,
        window_start=window_start,
        defaults=aggregates,
    )
    
    # Push features to Feast for downstream models (RiskScore, Bandit)
    push_to_feature_store(user, aggregates)
```

## Adding new signal type

1. Add event_name to [`backend/events/models.py`](backend/events/models.py) `EventLog.EventName` (per [event-taxonomy skill](../event-taxonomy/SKILL.md))
2. Create JSON schema in [`backend/events/schemas/{event_name}.json`](backend/events/schemas/) per [SIGNAL_TAXONOMY.md](../../../docs/SIGNAL_TAXONOMY.md)
3. Add detector in `frontend/src/lib/sensing/{detector}.ts`
4. Wire to `IngestBuffer`
5. Update `SignalSession` model if new aggregate field needed (with migration zero-downtime per [migration-runbook skill](../migration-runbook/SKILL.md))
6. Update [`backend/signals/scoring.py`](backend/signals/scoring.py) if affects scores
7. Add unit test for detector + ingest + rollup
8. Update [SIGNAL_TAXONOMY.md](../../../docs/SIGNAL_TAXONOMY.md) with new schema row
9. Bump `CONSENT_VERSION` if consent type changed

## Common pitfalls

- **Forgetting consent check**: ingest endpoint will leak signals from non-consenting users
- **Storing PII in `properties`**: schema validation should catch but be careful with free-form fields
- **Not deferring to Celery**: ingest endpoint blocks → frontend timeouts under load
- **Skipping idempotency**: duplicate events skew aggregates
- **Forgetting Feast push**: downstream models don't see new signal → adaptive flow breaks
- **Hardcoding thresholds**: use `PALP_SIGNALS` settings (not magic numbers in detector)

## Performance budget

- Ingest endpoint p95: < 100ms
- `process_signals_batch` Celery: < 5s for 50 events
- `rollup_signals_5min` Celery: < 1s per user-window
- Feast push: < 50ms per feature

## Related

- [SIGNAL_TAXONOMY.md](../../../docs/SIGNAL_TAXONOMY.md) — full event reference
- [PRIVACY_V2_DPIA.md](../../../docs/PRIVACY_V2_DPIA.md) section 3.1 — DPIA
- [event-taxonomy skill](../event-taxonomy/SKILL.md) — base event mechanism
- [risk-scoring skill](../risk-scoring/SKILL.md) — downstream consumer
- [celery-task skill](../celery-task/SKILL.md) — Celery patterns
