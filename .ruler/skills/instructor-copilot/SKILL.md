---
name: instructor-copilot
description: Lecturer co-pilot for auto-generate exercises (KG gaps), grade assist (rubric-aware LLM), curriculum optimization, draft feedback messages. Draft-must-approve rule. Use when modifying backend/instructor_copilot/.
---

# Instructor Co-pilot — Auto-Generate / Grade / Feedback (Draft-Must-Approve)

## When to use

- Editing `backend/instructor_copilot/` (exercise_generator, grading_assistant, curriculum_optimizer, feedback_drafter)
- Adding new copilot tool
- Tuning LLM prompts for copilot
- Reviewing PR touching copilot autonomy
- Investigating lecturer complaint "copilot did X without my permission"

## Hard invariants

1. **DRAFT-MUST-APPROVE rule**: every output is **draft**. Lecturer reads, edits, approves before action. No auto-action ever.
2. **Audit log every action**: who used copilot, what input, what draft, what was approved/rejected, what edits made.
3. **RBAC strict**: lecturer scope to assigned classes only. Cannot copilot for unassigned students.
4. **No grade auto-finalization**: grading_assistant suggests, lecturer always finalizes (legal + ethical reasons).
5. **Fairness check**: drafts checked for bias (esp. grading) — flag if disparate.
6. **Cite source**: copilot output cites which student data / curriculum data it used.
7. **LLM via cloud OK** (if lecturer consent + non-sensitive content) — copilot doesn't trigger SENSITIVE_INTENTS routing.
8. **Adoption metric**: track lecturer weekly active use ≥ 50% as P6 gate.

## App structure

```
backend/instructor_copilot/
├── models.py              # CopilotSession, GeneratedExercise, GradingDraft, FeedbackDraft, CopilotAuditLog
├── exercise_generator.py  # LLM + KG concept gaps → auto-generate exercises
├── grading_assistant.py   # rubric-aware LLM grading suggestions
├── curriculum_optimizer.py # cohort DKT patterns → ordering suggestions
├── feedback_drafter.py    # auto-draft messages cho sv risk cao
├── views.py               # /api/copilot/*
├── permissions.py         # IsLecturerOrAdmin + AssignedClassOnly
└── tests/
```

## 4 main capabilities

### 1. Exercise Generator

```python
# backend/instructor_copilot/exercise_generator.py
def generate_exercises_for_concept_gap(concept, target_difficulty, n=5):
    """Generate N draft exercises for a concept where cohort shows gap.
    
    LLM cloud OK — exercises are non-sensitive content.
    """
    prompt = f"""Tạo {n} bài tập về concept "{concept.name}" ở mức độ {target_difficulty}.
    
    Concept context: {concept.description}
    Prerequisites: {[p.name for p in concept.prerequisites.all()]}
    Common misconceptions: {concept.misconceptions_json}
    
    Mỗi bài: question, expected_answer, hint, difficulty_estimate.
    Format: JSON array.
    """
    
    response = call_cloud_llm(prompt, model="claude-opus-4")
    drafts = parse_json_array(response)
    
    # Save as GeneratedExercise (status="draft")
    exercises = []
    for d in drafts:
        ex = GeneratedExercise.objects.create(
            concept=concept,
            question=d["question"],
            expected_answer=d["expected_answer"],
            hint=d["hint"],
            difficulty=d["difficulty_estimate"],
            status="draft",
            generated_by_copilot=True,
        )
        exercises.append(ex)
    
    log_copilot_action(
        action="generate_exercises",
        target_concept=concept.id,
        draft_ids=[e.id for e in exercises],
    )
    
    return exercises
```

Lecturer reviews via `/(lecturer)/copilot/exercises/` UI:
- Edit question/answer/hint
- Approve → creates `MicroTask` in production
- Reject → archive draft

### 2. Grading Assistant

```python
# backend/instructor_copilot/grading_assistant.py
def suggest_grade(submission, rubric):
    """Rubric-aware LLM grading suggestion.
    
    NEVER auto-applies. Lecturer always finalizes.
    """
    prompt = f"""Bạn là grading assistant. Theo rubric sau, đánh giá bài nộp:
    
    Rubric: {rubric.criteria_json}
    Bài nộp: {submission.text}
    
    Output JSON: {{
        "score_per_criterion": {{...}},
        "total_score": int,
        "strengths": [str],
        "improvements": [str],
        "rationale": str
    }}
    """
    
    response = call_cloud_llm(prompt)
    suggestion = parse_json(response)
    
    draft = GradingDraft.objects.create(
        submission=submission,
        suggested_score=suggestion["total_score"],
        suggested_breakdown=suggestion["score_per_criterion"],
        rationale=suggestion["rationale"],
        status="awaiting_lecturer_review",
    )
    
    # Fairness flag — compare to lecturer's prior grading
    if abs(suggestion["total_score"] - mean_lecturer_grade(submission.assignment, suggestion)) > 20:
        draft.fairness_flag = "outlier_vs_lecturer_average"
        draft.save()
    
    log_copilot_action(action="suggest_grade", submission_id=submission.id, draft_id=draft.id)
    return draft
```

Lecturer UI shows:
- Suggested score + breakdown
- Rationale
- Edit field (lecturer can adjust)
- Approve = finalize submission grade
- Reject = grade manually (no copilot suggestion saved)

**Fairness audit**: weekly Celery task aggregates copilot suggestions vs final grades, checks for disparate impact across student demographics. Per [fairness-audit skill](../fairness-audit/SKILL.md).

### 3. Curriculum Optimizer

```python
# backend/instructor_copilot/curriculum_optimizer.py
def suggest_curriculum_changes(course):
    """Analyze cohort DKT patterns → suggest concept ordering changes.
    
    Output: list of suggestions with evidence.
    """
    cohort = active_students_in(course)
    dkt_patterns = analyze_dkt_struggle_patterns(cohort, course)
    
    suggestions = []
    
    # Pattern 1: many students struggle at concept X with high mastery on prereq Y
    # → maybe concept X needs more bridging
    for struggle in dkt_patterns["unexpected_struggles"]:
        suggestions.append({
            "type": "add_bridging_content",
            "before": struggle.concept,
            "evidence": f"{struggle.affected_count} students with mastery({struggle.prereq})>=0.85 still struggle on {struggle.concept.name}",
            "suggested_action": "Add 1-2 worked examples between prereq and concept",
        })
    
    # Pattern 2: high mastery but boredom signal (rapid completion + low frustration)
    # → maybe concept too easy, can compress
    # ... more patterns
    
    return suggestions
```

Lecturer UI shows suggestions, lecturer decides which to implement (route to Content Creator).

### 4. Feedback Drafter

```python
# backend/instructor_copilot/feedback_drafter.py
def draft_feedback_message(student, lecturer):
    """Auto-draft a feedback message for high-risk student.
    
    Pulls in risk score + recent activity + suggested next steps.
    """
    risk_breakdown = compute_risk_score(student)
    recent_activity = recent_signals_summary(student)
    
    prompt = f"""Bạn là Coach giúp giảng viên viết tin nhắn động viên cho sinh viên {student.name}.
    
    Risk score: {risk_breakdown.composite}
    Top factors: {risk_breakdown.explanation_factors[:3]}
    Recent activity: {recent_activity}
    
    Viết tin nhắn (≤ 100 từ):
    - Empathy first, không phán xét
    - Cụ thể về cải thiện gì (counterfactual từ XAI)
    - Mời meeting nếu phù hợp
    - SDT-aligned (autonomy, không "must do X")
    
    Tone: ấm, nhưng professional.
    """
    
    response = call_cloud_llm(prompt)
    
    draft = FeedbackDraft.objects.create(
        student=student,
        lecturer=lecturer,
        draft_text=response,
        context_summary=recent_activity,
        status="awaiting_lecturer_review",
    )
    
    return draft
```

Lecturer UI:
- Draft text editable
- Approve & send → message goes to student via NotificationService
- Reject → discard

## Audit log

Every copilot action logged in `CopilotAuditLog`:

```python
class CopilotAuditLog(models.Model):
    lecturer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)  # generate_exercises, suggest_grade, etc.
    input_summary = models.JSONField()  # what was input (e.g., concept_id, student_id)
    draft_id = models.IntegerField(null=True)
    final_action = models.CharField(max_length=20, null=True)  # approved, rejected, edited_then_approved
    edits_diff = models.JSONField(null=True)  # what lecturer changed
    timestamp = models.DateTimeField(auto_now_add=True)
```

Used for:
- Adoption metrics
- Fairness analysis (do suggestions align with manual?)
- Postmortem if lecturer claims "copilot did X without my permission"
- Compliance — automated decision audit

## Lecturer onboarding

Per [MULTISTAKEHOLDER_GUIDE.md](../../../docs/MULTISTAKEHOLDER_GUIDE.md) — lecturer add-on training:
- Copilot is **assistant, not replacement**
- Lecturer always reviews + approves
- Edit before approve is encouraged
- Reject when not useful
- Tools have biases — fairness audit reports

## Common pitfalls

- **Auto-action without approve**: violates draft-must-approve rule
- **No edit tracking**: can't measure copilot quality (rejected vs edited vs accepted as-is)
- **Forgetting fairness audit on grading**: bias amplifies through copilot
- **Cloud LLM with PII without mask**: route through PII Guard if any PII (per [coach-safety skill](../coach-safety/SKILL.md))
- **No rationale in suggestion**: lecturer can't trust without explanation
- **Hard-coded prompts**: use `CoachPrompt` model versioned

## Adoption metric (P6 gate)

`copilot_weekly_active_users / total_lecturers ≥ 0.50`. Track via Grafana `copilot-quality` dashboard.

If adoption low:
- User research: why not used? Friction? Trust? Quality?
- Iterate on prompts + UX
- Lecturer onboarding refresh

## Test coverage

- Every action creates audit log
- Draft status correctly changes (draft → approved/rejected)
- Edits diff captured
- RBAC: lecturer can't generate for unassigned class
- Fairness audit on grading drafts
- LLM mock for unit tests (don't call real cloud)

## Related

- [MULTISTAKEHOLDER_GUIDE.md](../../../docs/MULTISTAKEHOLDER_GUIDE.md) section 3 — Lecturer role
- [coach-safety skill](../coach-safety/SKILL.md) — LLM safety patterns
- [fairness-audit skill](../fairness-audit/SKILL.md) — grading fairness
- [llm-routing skill](../llm-routing/SKILL.md) — copilot uses cloud route (non-sensitive)
- [MOTIVATION_DESIGN.md](../../../docs/MOTIVATION_DESIGN.md) — feedback tone (SDT)
- [PRIVACY_V2_DPIA.md](../../../docs/PRIVACY_V2_DPIA.md) — copilot doesn't add new consent type (uses lecturer existing)
