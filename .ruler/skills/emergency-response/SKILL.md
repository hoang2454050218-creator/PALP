---
name: emergency-response
description: Mental health emergency pipeline — detection, counselor queue 15min SLA, 3-level escalation, opt-in emergency contact, 24/48/72h follow-up. Use when modifying backend/emergency/ or working with counselor flow.
---

# Emergency Response — Mental Health Crisis Pipeline

## When to use

- Editing `backend/emergency/` (detector, queue, escalator, follow_up, models)
- Modifying counselor flag (`accounts.User.counselor_certified`)
- Adding to `EmergencyKeyword` model (vocabulary update)
- Tuning detection classifier
- Onboarding new counselor (link [EMERGENCY_RESPONSE_TRAINING.md](../../../docs/EMERGENCY_RESPONSE_TRAINING.md) section 6)
- Investigating false positive/negative
- Reviewing PR touching emergency code (CRITICAL — extra reviewer required)

## Hard invariants

1. **15-minute counselor SLA** — `PALP_EMERGENCY["COUNSELOR_SLA_MINUTES"]` enforced via Celery `check_counselor_sla` every minute.
2. **Counselor must be certified** — `User.counselor_certified=True` only after training + quiz pass + admin approval.
3. **Emergency contact opt-in only** — never use without explicit `EmergencyContact` consent.
4. **Template responses, NOT LLM-generated** for crisis communication.
5. **Audit log every step** — detection, assignment, response, escalation, follow-up, resolution.
6. **Encrypted at rest** — `EmergencyEvent.encrypted_evidence` Fernet, key in `PII_ENCRYPTION_KEY`.
7. **Detection runs PARALLEL** with normal coach flow — don't block.
8. **Sampling NEVER applied** — every potential emergency event must be processed.
9. **Follow-up automated** — 24/48/72h Celery tasks, can't be skipped.
10. **Lecturer notified for assigned class** — with student consent, post-resolution.

## Pipeline overview

```
detect → triage → counselor queue → counselor response → resolution → follow-up
                       (SLA 15min)         (if no response)
                                          → emergency_contact (opt-in)
                                          → admin escalate
```

## Workflow when modifying

### 1. Detection — keyword + classifier

```python
# backend/emergency/detector.py
from .models import EmergencyKeyword, EmergencyEvent

class EmergencyDetector:
    async def detect(self, message: str, user) -> EmergencyDetection:
        # Layer 1: keyword match (fast)
        keyword_hits = self._scan_keywords(message)
        
        # Layer 2: zero-shot classifier (slower, more accurate)
        classifier_result = await self._classify_local_llm(message)
        
        # Composite decision
        severity = self._combine(keyword_hits, classifier_result)
        
        if severity in ("high", "critical"):
            incident = self._create_incident(user, message, severity, keyword_hits, classifier_result)
            return EmergencyDetection(
                severity=severity,
                should_escalate=True,
                incident_id=incident.id,
                evidence={"keyword_hits": keyword_hits, "classifier": classifier_result},
            )
        return EmergencyDetection(severity=severity, should_escalate=False)
    
    def _scan_keywords(self, message):
        active_keywords = EmergencyKeyword.objects.filter(active=True)
        message_lower = message.lower()
        hits = []
        for kw in active_keywords:
            if kw.keyword.lower() in message_lower:
                hits.append({
                    "keyword": kw.keyword,
                    "category": kw.category,
                    "severity_weight": kw.severity_weight,
                })
        return hits
    
    async def _classify_local_llm(self, message):
        # Use Local LLM (NEVER cloud for emergency) for zero-shot classification
        from backend.coach.llm.local_client import LocalLLMClient
        client = LocalLLMClient()
        prompt = build_emergency_classifier_prompt(message)
        result = await client.classify(prompt, labels=["low", "medium", "high", "critical"])
        return {"severity": result["label"], "confidence": result["score"]}
    
    def _create_incident(self, user, message, severity, kw_hits, cls_result):
        return EmergencyEvent.objects.create(
            student=user,
            severity=severity,
            trigger_type="composite" if (kw_hits and cls_result["severity"] in ("high", "critical")) else "keyword_match" if kw_hits else "classifier_score",
            classifier_confidence=cls_result["confidence"],
            encrypted_evidence=encrypt(message),  # NEVER plaintext
            status="awaiting_counselor",
        )
```

### 2. Triage + Counselor Assignment

```python
# backend/emergency/queue.py
def assign_counselor(incident):
    """Assign best-available certified counselor."""
    candidates = User.objects.filter(
        counselor_certified=True,
        is_active=True,
    ).annotate(
        active_load=Count("counselor_assignments", filter=Q(counselor_assignments__incident__status="awaiting_counselor")),
    ).order_by("active_load")
    
    # Prefer student's class lecturer (relationship)
    student_lecturers = get_student_lecturers(incident.student)
    for c in candidates:
        if c in student_lecturers:
            return _assign(incident, c)
    
    # Fallback: round-robin by load
    return _assign(incident, candidates.first())

def _assign(incident, counselor):
    CounselorAssignment.objects.create(
        incident=incident,
        counselor=counselor,
        assigned_at=timezone.now(),
        response_due_at=timezone.now() + timedelta(minutes=settings.PALP_EMERGENCY["COUNSELOR_SLA_MINUTES"]),
    )
    
    # Notify all 4 channels in parallel
    NotificationService.send(
        recipient=counselor,
        urgency="critical",
        channels=["sse", "web_push", "email", "sms"],  # if SMS enabled
        template="emergency_assigned",
        context={"incident_id": incident.id, "student_name_masked": mask_name(incident.student.name)},
    )
```

### 3. SLA monitor

```python
# backend/emergency/tasks.py
@shared_task
def check_counselor_sla():
    """Run every minute. Escalate overdue incidents."""
    overdue = EmergencyEvent.objects.filter(
        status="awaiting_counselor",
        counselor_assignments__response_due_at__lt=timezone.now(),
        counselor_assignments__counselor_responded_at__isnull=True,
    )
    for incident in overdue:
        escalate_to_emergency_contact(incident)
```

### 4. Escalation chain

```python
# backend/emergency/escalator.py
def escalate_to_emergency_contact(incident):
    """Level 2: counselor missed SLA, try emergency_contact."""
    
    if hasattr(incident.student, "emergency_contact") and incident.student.emergency_contact:
        contact = incident.student.emergency_contact
        
        # 2-step verification: another counselor must confirm SLA missed
        verification = CounselorVerification.objects.create(
            incident=incident,
            verifier=find_admin_or_certified_counselor(),
            verified_at=timezone.now(),
        )
        
        # Decrypt contact info (audit logged)
        decrypted_phone = decrypt(contact.phone_encrypted)
        
        # Contact (use existing notification + SMS provider)
        NotificationService.send(
            recipient_external={"name": contact.name, "phone": decrypted_phone},
            channels=["sms", "phone_call"],
            template="emergency_contact_outreach",
            context={"student_name": incident.student.name},
        )
        
        # Notify student that contact was activated
        NotificationService.send(
            recipient=incident.student,
            urgency="high",
            channels=["in_app"],
            template="emergency_contact_activated_notice",
            context={"contact_name": contact.name},
        )
        
        incident.status = "escalated_emergency_contact"
        incident.escalated_at = timezone.now()
        incident.save()
    else:
        # Level 3: no emergency_contact opt-in, escalate to admin
        escalate_to_admin(incident)

def escalate_to_admin(incident):
    """Level 3: critical situation, no contact, alert admin team."""
    admins = User.objects.filter(is_superuser=True, is_active=True)
    for admin in admins:
        NotificationService.send(
            recipient=admin,
            urgency="critical",
            channels=["sse", "web_push", "email", "sms"],
            template="emergency_admin_escalation",
            context={"incident_id": incident.id},
        )
    
    incident.status = "escalated_admin"
    incident.save()
```

### 5. Resolution + Follow-up

```python
# backend/emergency/follow_up.py
@shared_task
def schedule_follow_ups(incident_id):
    """When incident resolved, schedule 24/48/72h follow-ups."""
    incident = EmergencyEvent.objects.get(pk=incident_id)
    if incident.status not in ("counselor_intervention", "professional_referral"):
        return
    
    for hours in settings.PALP_EMERGENCY["FOLLOW_UP_HOURS"]:
        followup_at = incident.resolved_at + timedelta(hours=hours)
        EmergencyFollowUp.objects.create(
            incident=incident,
            scheduled_at=followup_at,
            interval_hours=hours,
            status="scheduled",
        )

@shared_task
def execute_follow_ups():
    """Run hourly. Execute due follow-ups."""
    due = EmergencyFollowUp.objects.filter(
        status="scheduled",
        scheduled_at__lte=timezone.now(),
    )
    for fu in due:
        send_follow_up(fu)
        fu.status = "sent"
        fu.sent_at = timezone.now()
        fu.save()
```

## Adding to EmergencyKeyword vocabulary

Vocabulary curated by mental health professional, NOT dev:

```python
# backend/emergency/management/commands/import_keywords.py
"""
Import vocabulary from professional-curated CSV. Don't hardcode in Python.
"""
import csv
from backend.emergency.models import EmergencyKeyword

def handle(*args, **options):
    csv_path = options["csv_path"]
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            EmergencyKeyword.objects.update_or_create(
                keyword=row["keyword"],
                language=row["language"],
                defaults={
                    "category": row["category"],
                    "severity_weight": float(row["severity_weight"]),
                    "active": True,
                },
            )
```

Run quarterly review with mental health team to update.

## Tuning detection classifier

Local LLM zero-shot is starting point. Future: fine-tuned model on labeled data:

1. Collect labeled corpus (anonymized, IRB approved)
2. Train DistilBERT or PhoBERT classifier
3. Evaluate sensitivity vs specificity tradeoff
4. Default to high sensitivity (false positive OK; false negative not)
5. A/B test new classifier vs zero-shot
6. Per [Model Card](../../../docs/model_cards/) document

## Common pitfalls

- **Sampling emergency events**: NEVER. All events processed.
- **LLM-generated emergency response**: NEVER. Template only.
- **Cloud LLM for detection**: NEVER. Local only (PII).
- **Storing message plaintext**: NEVER. Always encrypted.
- **Skipping audit log**: legal exposure + cannot improve system.
- **Hard-coded SLA**: use settings.
- **Not notifying student about escalation**: violates trust.
- **Auto-contact emergency_contact without 2-step verification**: high false positive risk.
- **Counselor without certification**: untrained crisis response can do harm.

## Test matrix

```python
# backend/emergency/tests/
@pytest.mark.emergency
def test_detect_keyword_match():
    """Detection picks up known keyword."""

@pytest.mark.emergency
def test_detect_classifier_high_severity():
    """Detection picks up via classifier even without keyword."""

@pytest.mark.emergency
def test_no_consent_emergency_contact_escalates_admin():
    """If sv has no emergency_contact, SLA timeout escalates to admin."""

@pytest.mark.emergency
def test_counselor_responds_within_sla_no_escalation():
    """Happy path: counselor responds, no escalation."""

@pytest.mark.emergency
def test_follow_up_scheduled_after_resolution():
    """24/48/72h follow-ups created."""

@pytest.mark.emergency
def test_evidence_encrypted_at_rest():
    """Database row has encrypted_evidence, not plaintext."""

@pytest.mark.emergency
def test_template_response_not_llm_generated():
    """Emergency response text matches template, not LLM output."""

@pytest.mark.security
def test_lecturer_only_sees_assigned_class_emergencies():
    """RBAC: lecturer can't see other classes' emergencies."""
```

## Related

- [EMERGENCY_RESPONSE_TRAINING.md](../../../docs/EMERGENCY_RESPONSE_TRAINING.md) — full training course content
- [COACH_SAFETY_PLAYBOOK.md](../../../docs/COACH_SAFETY_PLAYBOOK.md) section 9 — coach integration
- [PRIVACY_V2_DPIA.md](../../../docs/PRIVACY_V2_DPIA.md) section 3.9 — emergency_contact consent
- [INCIDENT_CULTURE.md](../../../docs/INCIDENT_CULTURE.md) — postmortem
- [PRIVACY_INCIDENT.md](../../../docs/PRIVACY_INCIDENT.md) — incident handling general (existing)
- [coach-safety skill](../coach-safety/SKILL.md)
- [llm-routing skill](../llm-routing/SKILL.md)
