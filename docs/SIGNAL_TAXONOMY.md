# Signal Taxonomy v2 — Event Catalog

> Bản tham chiếu chính thức cho 25+ event mới được thêm vào `EventLog.EventName` trong roadmap v3. Bổ sung cho [event-taxonomy skill](../.ruler/skills/event-taxonomy/SKILL.md). Mỗi event có schema JSON cho `properties` field — validate bắt buộc trong `events.emitter.emit_event()`.

## 1. Cấu trúc tham chiếu

Mỗi event có:
- **Khi nào emit**: trigger condition cụ thể
- **Actor**: student / lecturer / system / counselor
- **Schema**: shape của `properties` JSON
- **Privacy**: PII level (none/indirect/direct), consent required
- **Phase**: phase nào của roadmap thêm vào
- **Sampling**: 1.0 (full) / sample rate cho high-volume events

## 2. Sensing events (Phase 1)

### 2.1 `focus_lost`

| Field | Value |
|---|---|
| Khi nào emit | Page Visibility API → hidden hoặc window blur ≥ 2s |
| Actor | student |
| Privacy | Indirect (behavioral) — `behavioral_signals` consent |
| Phase | P1 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["focus_duration_ms", "trigger"],
  "properties": {
    "focus_duration_ms": {"type": "integer", "minimum": 0},
    "trigger": {"enum": ["visibility_hidden", "window_blur", "tab_switch"]},
    "url_path": {"type": "string"},
    "task_id": {"type": "integer", "nullable": true}
  }
}
```

### 2.2 `focus_gained`

| Field | Value |
|---|---|
| Khi nào emit | Page Visibility API → visible hoặc window focus sau ≥ 2s away |
| Actor | student |
| Privacy | Indirect — `behavioral_signals` |
| Phase | P1 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["away_duration_ms"],
  "properties": {
    "away_duration_ms": {"type": "integer", "minimum": 2000},
    "url_path": {"type": "string"}
  }
}
```

### 2.3 `tab_switched`

| Field | Value |
|---|---|
| Khi nào emit | `visibilitychange` event với hidden=true (subset của focus_lost với metadata) |
| Actor | student |
| Privacy | Indirect — `behavioral_signals` |
| Phase | P1 |
| Sampling | 0.5 (high volume) |

```json
{
  "type": "object",
  "properties": {
    "current_url_path": {"type": "string"},
    "task_in_progress": {"type": "boolean"}
  }
}
```

### 2.4 `idle_started` / `idle_ended`

| Field | Value |
|---|---|
| Khi nào emit | Mouse + keyboard inactivity ≥ `IDLE_THRESHOLD_SECONDS` (default 5) / khi resume |
| Actor | student |
| Privacy | Indirect — `behavioral_signals` |
| Phase | P1 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["idle_duration_ms"],
  "properties": {
    "idle_duration_ms": {"type": "integer", "minimum": 5000},
    "url_path": {"type": "string"}
  }
}
```

### 2.5 `scroll_depth`

| Field | Value |
|---|---|
| Khi nào emit | Reach scroll milestone (25%, 50%, 75%, 100%) trên trang content |
| Actor | student |
| Privacy | None (no PII) |
| Phase | P1 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["depth_pct", "page_type"],
  "properties": {
    "depth_pct": {"enum": [25, 50, 75, 100]},
    "page_type": {"enum": ["task", "concept", "explanation", "north_star"]}
  }
}
```

### 2.6 `hint_requested`

| Field | Value |
|---|---|
| Khi nào emit | User click "Hint" button trên task |
| Actor | student |
| Privacy | None |
| Phase | P1 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["task_id", "hint_index"],
  "properties": {
    "task_id": {"type": "integer"},
    "hint_index": {"type": "integer", "minimum": 1},
    "time_since_task_start_ms": {"type": "integer"}
  }
}
```

### 2.7 `frustration_signal`

| Field | Value |
|---|---|
| Khi nào emit | Detector phát hiện rapid clicks (≥5 click/2s), ragequit pattern, hoặc repeat-wrong |
| Actor | student |
| Privacy | Indirect — `behavioral_signals` |
| Phase | P1 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["pattern", "intensity"],
  "properties": {
    "pattern": {"enum": ["rapid_click", "ragequit", "repeat_wrong", "rapid_backspace"]},
    "intensity": {"type": "number", "minimum": 0, "maximum": 1},
    "task_id": {"type": "integer", "nullable": true}
  }
}
```

### 2.8 `give_up_signal`

| Field | Value |
|---|---|
| Khi nào emit | User leave task without submit sau ≥ `GIVE_UP_MIN_TIME_S` (180), hoặc explicit "skip" |
| Actor | student |
| Privacy | Indirect — `behavioral_signals` |
| Phase | P1 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["task_id", "trigger"],
  "properties": {
    "task_id": {"type": "integer"},
    "trigger": {"enum": ["leave_no_submit", "explicit_skip", "navigation_away"]},
    "time_on_task_ms": {"type": "integer"}
  }
}
```

### 2.9 `response_time_outlier`

| Field | Value |
|---|---|
| Khi nào emit | Submit task với `response_time > 2× expected` hoặc `< 0.3× expected` |
| Actor | system |
| Privacy | None |
| Phase | P1 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["task_id", "response_time_ms", "expected_ms", "z_score"],
  "properties": {
    "task_id": {"type": "integer"},
    "response_time_ms": {"type": "integer"},
    "expected_ms": {"type": "integer"},
    "z_score": {"type": "number"},
    "outlier_type": {"enum": ["too_fast", "too_slow"]}
  }
}
```

### 2.10 `struggle_detected`

| Field | Value |
|---|---|
| Khi nào emit | Composite: ≥ N frustration_signal trong T phút HOẶC ≥ M failed attempts cùng concept |
| Actor | system |
| Privacy | Indirect |
| Phase | P1 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["concept_id", "trigger_type", "evidence"],
  "properties": {
    "concept_id": {"type": "integer"},
    "trigger_type": {"enum": ["frustration_threshold", "failed_attempts", "composite"]},
    "evidence": {"type": "object"}
  }
}
```

### 2.11 `scaffold_shown` / `scaffold_accepted`

| Field | Value |
|---|---|
| Khi nào emit | System show scaffold sau struggle_detected / user click "Yes show me" |
| Actor | system / student |
| Privacy | None |
| Phase | P1 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["scaffold_type", "concept_id"],
  "properties": {
    "scaffold_type": {"enum": ["worked_example", "hint_chain", "video", "peer_explanation"]},
    "concept_id": {"type": "integer"},
    "task_id": {"type": "integer", "nullable": true}
  }
}
```

### 2.12 `cognitive_calibration_recorded`

| Field | Value |
|---|---|
| Khi nào emit | User submit confidence (1-5) trước nộp bài; system pair với actual_correct |
| Actor | student |
| Privacy | Indirect — `cognitive_calibration` consent |
| Phase | P1 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["task_id", "confidence_pre", "actual_correct", "calibration_error", "judgment_type"],
  "properties": {
    "task_id": {"type": "integer"},
    "confidence_pre": {"type": "integer", "minimum": 1, "maximum": 5},
    "actual_correct": {"type": "boolean"},
    "calibration_error": {"type": "number", "minimum": 0, "maximum": 1},
    "judgment_type": {"enum": ["JOL", "FOK", "EOL"]}
  }
}
```

## 3. Direction events (Phase 2)

### 3.1 `goal_set`

| Field | Value |
|---|---|
| Khi nào emit | User create/update Career/Semester/Weekly goal |
| Actor | student |
| Privacy | None |
| Phase | P2 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["goal_type", "goal_id"],
  "properties": {
    "goal_type": {"enum": ["career", "semester", "weekly"]},
    "goal_id": {"type": "integer"},
    "target_minutes": {"type": "integer", "nullable": true},
    "target_concepts": {"type": "array", "items": {"type": "integer"}}
  }
}
```

### 3.2 `goal_drift`

| Field | Value |
|---|---|
| Khi nào emit | Celery `goals.tasks.detect_drift` phát hiện actual vs target lệch ≥ `DRIFT_THRESHOLD_PCT` (40%) |
| Actor | system |
| Privacy | None |
| Phase | P2 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["weekly_goal_id", "target_minutes", "actual_minutes", "drift_pct"],
  "properties": {
    "weekly_goal_id": {"type": "integer"},
    "target_minutes": {"type": "integer"},
    "actual_minutes": {"type": "integer"},
    "drift_pct": {"type": "number"}
  }
}
```

### 3.3 `reflection_submitted`

| Field | Value |
|---|---|
| Khi nào emit | User submit weekly reflection (3 câu + EffortRating + StrategyEffectiveness) |
| Actor | student |
| Privacy | Indirect (free text → linguistic affect khi có consent) |
| Phase | P2 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["reflection_id", "effort_rating"],
  "properties": {
    "reflection_id": {"type": "integer"},
    "effort_rating": {"type": "integer", "minimum": 1, "maximum": 5},
    "strategy_effectiveness": {"type": "integer", "minimum": 1, "maximum": 5},
    "free_text_word_count": {"type": "integer"}
  }
}
```

Ghi chú: **không** bao giờ emit free_text trong properties — chỉ word_count. Free text store trong `GoalReflection.text` field encrypted.

### 3.4 `strategy_plan_set`

```json
{
  "type": "object",
  "required": ["weekly_goal_id", "strategy_label"],
  "properties": {
    "weekly_goal_id": {"type": "integer"},
    "strategy_label": {"enum": ["spaced_practice", "deep_focus_blocks", "peer_teaching", "worked_examples", "self_explanation", "other"]},
    "predicted_minutes": {"type": "integer"}
  }
}
```

## 4. Peer events (Phase 3)

### 4.1 `peer_benchmark_viewed`

| Privacy | `peer_comparison` consent required |
| Phase | P3 |

```json
{
  "type": "object",
  "required": ["cohort_id"],
  "properties": {
    "cohort_id": {"type": "integer"},
    "view_type": {"enum": ["percentile", "frontier", "buddy"]}
  }
}
```

### 4.2 `reciprocal_teaching_started`

| Privacy | `peer_teaching` consent required |
| Phase | P3 |

```json
{
  "type": "object",
  "required": ["session_id", "match_id", "concept_a_to_b", "concept_b_to_a"],
  "properties": {
    "session_id": {"type": "integer"},
    "match_id": {"type": "integer"},
    "concept_a_to_b": {"type": "integer"},
    "concept_b_to_a": {"type": "integer"}
  }
}
```

### 4.3 `reciprocal_teaching_rated`

```json
{
  "type": "object",
  "required": ["session_id", "rating_role", "rating"],
  "properties": {
    "session_id": {"type": "integer"},
    "rating_role": {"enum": ["teacher", "student"]},
    "rating": {"type": "integer", "minimum": 1, "maximum": 5},
    "mastery_delta_after": {"type": "number", "nullable": true}
  }
}
```

## 5. Coach events (Phase 4)

### 5.1 `coach_turn`

| Privacy | `ai_coach_cloud` hoặc `ai_coach_local` consent. Free text NOT in properties |
| Phase | P4 |
| Sampling | 1.0 |

```json
{
  "type": "object",
  "required": ["conversation_id", "turn_number", "role", "llm_provider", "llm_model", "intent", "tokens_in", "tokens_out", "latency_ms"],
  "properties": {
    "conversation_id": {"type": "integer"},
    "turn_number": {"type": "integer"},
    "role": {"enum": ["user", "coach", "system", "tool"]},
    "llm_provider": {"enum": ["anthropic", "openai", "ollama_local", "none"]},
    "llm_model": {"type": "string"},
    "intent": {"type": "string"},
    "tokens_in": {"type": "integer"},
    "tokens_out": {"type": "integer"},
    "latency_ms": {"type": "integer"},
    "tools_called": {"type": "array", "items": {"type": "string"}},
    "safety_flags": {"type": "array", "items": {"type": "string"}}
  }
}
```

### 5.2 `coach_nudge_sent`

```json
{
  "type": "object",
  "required": ["nudge_id", "trigger_source", "channel"],
  "properties": {
    "nudge_id": {"type": "integer"},
    "trigger_source": {"enum": ["goal_drift", "herd_cluster", "risk_score", "inactivity", "calibration_feedback", "fsrs_due", "manual_lecturer"]},
    "channel": {"enum": ["in_app", "sse", "web_push", "email"]},
    "bandit_arm_id": {"type": "integer", "nullable": true}
  }
}
```

## 6. Emergency events (Phase 4)

Đặc biệt nhạy cảm — xem [EMERGENCY_RESPONSE_TRAINING.md](EMERGENCY_RESPONSE_TRAINING.md).

### 6.1 `emergency_detected`

| Privacy | Direct (PII high). Audit log mandatory. Encrypted at rest |
| Phase | P4 |
| Sampling | 1.0 (NEVER sample) |

```json
{
  "type": "object",
  "required": ["incident_id", "severity", "trigger_type"],
  "properties": {
    "incident_id": {"type": "integer"},
    "severity": {"enum": ["low", "medium", "high", "critical"]},
    "trigger_type": {"enum": ["keyword_match", "classifier_score", "manual_report", "composite"]},
    "classifier_confidence": {"type": "number", "nullable": true}
  }
}
```

**Properties tuyệt đối không chứa nội dung message gốc.** Message gốc encrypted lưu riêng trong `EmergencyEvent.encrypted_evidence`.

### 6.2 `counselor_responded`

```json
{
  "type": "object",
  "required": ["incident_id", "counselor_id_hash", "response_time_seconds", "channel"],
  "properties": {
    "incident_id": {"type": "integer"},
    "counselor_id_hash": {"type": "string", "description": "SHA256 hash, not direct ID"},
    "response_time_seconds": {"type": "integer"},
    "channel": {"enum": ["direct_message", "phone", "in_person", "emergency_contact"]}
  }
}
```

### 6.3 `emergency_resolved`

```json
{
  "type": "object",
  "required": ["incident_id", "resolution", "follow_up_scheduled"],
  "properties": {
    "incident_id": {"type": "integer"},
    "resolution": {"enum": ["counselor_intervention", "self_resolved", "escalated_external", "false_positive"]},
    "follow_up_scheduled": {"type": "array", "items": {"enum": ["24h", "48h", "72h"]}}
  }
}
```

## 7. Affect events (Phase 6D)

### 7.1 `affect_keystroke_window`

| Privacy | `affect_keystroke` consent (3-tier) |
| Phase | P6 |
| Sampling | 0.1 (very high volume — sample) |

```json
{
  "type": "object",
  "required": ["window_seconds", "dwell_time_avg_ms", "flight_time_avg_ms", "speed_wpm"],
  "properties": {
    "window_seconds": {"type": "integer"},
    "dwell_time_avg_ms": {"type": "number"},
    "flight_time_avg_ms": {"type": "number"},
    "speed_wpm": {"type": "number"},
    "rhythm_variance": {"type": "number"}
  }
}
```

### 7.2 `affect_linguistic_processed`

| Privacy | `affect_linguistic` consent |
| Phase | P6 |

```json
{
  "type": "object",
  "required": ["coach_turn_id", "valence", "arousal"],
  "properties": {
    "coach_turn_id": {"type": "integer"},
    "valence": {"type": "number", "minimum": -1, "maximum": 1},
    "arousal": {"type": "number", "minimum": 0, "maximum": 1},
    "model_version": {"type": "string"}
  }
}
```

### 7.3 `affect_facial_window`

| Privacy | `affect_facial` consent. **On-device only** — server chỉ nhận 2 scalar |
| Phase | P6 |

```json
{
  "type": "object",
  "required": ["window_seconds", "valence", "arousal"],
  "properties": {
    "window_seconds": {"type": "integer"},
    "valence": {"type": "number", "minimum": -1, "maximum": 1},
    "arousal": {"type": "number", "minimum": 0, "maximum": 1},
    "on_device_processed": {"type": "boolean", "const": true}
  }
}
```

**Server từ chối event nếu `on_device_processed != true`.** Không bao giờ chấp nhận raw landmarks/video.

## 8. Migration plan

### 8.1 Migration 0008

[`backend/events/migrations/0008_alter_eventlog_event_name.py`](../backend/events/migrations/0008_alter_eventlog_event_name.py) — chỉ mở rộng choices, không phá indices.

```python
operations = [
    migrations.AlterField(
        model_name="eventlog",
        name="event_name",
        field=models.CharField(
            max_length=50,
            choices=EXTENDED_CHOICES,  # 25+ event mới
            db_index=True,
        ),
    ),
]
```

### 8.2 JSON schema validation

Tạo folder [`backend/events/schemas/`](../backend/events/schemas/) với 1 file JSON per event_name. Loader trong `events.emitter`:

```python
SCHEMAS_DIR = Path(__file__).parent / "schemas"
def get_schema(event_name: str) -> dict:
    return json.loads((SCHEMAS_DIR / f"{event_name}.json").read_text())

def emit_event(event_name, properties, **kwargs):
    schema = get_schema(event_name)
    jsonschema.validate(properties, schema)
    EventLog.objects.create(event_name=event_name, properties=properties, **kwargs)
```

### 8.3 Sampling rate config

```python
PALP_EVENT_SAMPLING = {
    "tab_switched": 0.5,
    "scroll_depth": 1.0,
    "affect_keystroke_window": 0.1,
    # default: 1.0
}
```

## 9. Hard rules (event-taxonomy enforcement)

1. **Never PII in properties** — chỉ IDs hoặc hash. Free text NEVER in properties.
2. **Required fields enforced** — schema validation reject nếu thiếu.
3. **Idempotency** — `request_id + event_name + actor` unique within 5 min window.
4. **Sampling consistent** — quyết định sample tại ingest time, ghi `sampled=true/false` trong properties cho high-volume events.
5. **Privacy consent gate** — `signals/views.py SignalIngestView` reject 403 nếu chưa consent với type tương ứng.

Xem chi tiết workflow trong [event-taxonomy skill](../.ruler/skills/event-taxonomy/SKILL.md) (đã có) và [signals-pipeline skill](../.ruler/skills/signals-pipeline/SKILL.md) (mới).
