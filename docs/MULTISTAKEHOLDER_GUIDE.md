# Multi-Stakeholder Guide

> Hướng dẫn vai trò + permission cho 5 stakeholder của PALP. Phục vụ nguyên tắc 8 ([AI_COACH_ARCHITECTURE.md](AI_COACH_ARCHITECTURE.md) section 3): "Multi-stakeholder coverage — không bỏ rơi stakeholder nào". Kèm [PRIVACY_V2_DPIA.md](PRIVACY_V2_DPIA.md) cho consent details.

## 1. 5 stakeholder roles

| Role | When introduced | Primary need | Permission scope |
|---|---|---|---|
| **Student** | (existing) | Học hiệu quả, định hướng, support | Own data only |
| **Lecturer** | (existing, expanded P4-P6) | Triage, intervention, autonomy | Assigned classes |
| **Content Creator** | P6 new role | Curriculum design, KG editor | Course content scope |
| **Admin** | (existing, expanded P0-P6) | System health, analytics, governance | Full + audit |
| **Parent/Sponsor** | P6 new role | Awareness of student progress (consent) | Aggregated, opt-in |

Plus Counselor flag (sub-role of Lecturer) cho [EMERGENCY_RESPONSE_TRAINING.md](EMERGENCY_RESPONSE_TRAINING.md).

## 2. Student

### 2.1 Existing capabilities (preserved)

- Login, profile management
- Take assessment, micro-tasks
- View own pathway, mastery
- Wellbeing nudges
- Privacy export/delete
- Consent management (Privacy Hub)

### 2.2 New capabilities (v3 roadmap)

| Phase | New feature |
|---|---|
| P1 | Behavioral signal control (opt-in/out), metacognitive calibration UI |
| P2 | North Star (goal setting + daily plan + reflection) |
| P3 | Peer benchmark + reciprocal teaching (opt-in) |
| P4 | AI Coach chat + emergency contact registration |
| P5 | DKT-personalized predictions, KG visualization, FSRS review queue |
| P6 | XAI explanation panel, affect tier consent, parent_sponsor approval |

### 2.3 UI surface

Routes (existing + new):

```
/login                                    (existing)
/(student)/dashboard                       (existing)
/(student)/north-star                      P2 NEW — goals + daily plan
/(student)/pathway                         (existing, enhanced P5 KG visualization)
/(student)/curriculum/graph                P5 NEW — KG visualization
/(student)/task/[id]                       (existing, enhanced P1 calibration)
/(student)/peer                            P3 NEW — frontier/benchmark/buddy
/(student)/peer/teaching-session/[id]      P3 NEW
/(student)/spacedrep                       P6 NEW — FSRS review
/(student)/coach                           P4 NEW (or floating widget)
/(student)/wellbeing                       (existing)
/(student)/preferences/                    (existing, expanded with 14 consent toggles)
/(student)/preferences/peer                P3 NEW
/(student)/preferences/coach               P4 NEW
/(student)/preferences/affect              P6 NEW (3-tier)
/(student)/preferences/emergency-contact   P4 NEW
/(student)/help/emergency                  P4 NEW (always accessible)
```

### 2.4 SDT-aligned principles

Per [MOTIVATION_DESIGN.md](MOTIVATION_DESIGN.md):
- Always opt-in, easy revoke
- Mastery framing > score framing
- Counterfactual actionable suggestions
- No gamification creep

## 3. Lecturer

### 3.1 Existing capabilities (preserved)

- Login, profile
- View assigned classes
- Early warning dashboard
- Intervention CRUD
- Class overview

### 3.2 New capabilities

| Phase | New feature |
|---|---|
| P0 | MLflow access (read), causal experiment results |
| P1 | RiskScore breakdown view (5-dim) |
| P3 | Herd cluster view, fairness audit warnings |
| P4 | Counselor certification (sub-role), emergency response queue |
| P5 | Survival "tipping point" view, KG editor (per-course) |
| P6 | Instructor Co-pilot dashboard (auto-generate, grade, feedback drafts), XAI explanation for risk decisions |

### 3.3 UI surface

```
/(lecturer)/overview                      (existing, enhanced P1 RiskScore)
/(lecturer)/dashboard                     (existing)
/(lecturer)/classes/[id]                  (existing)
/(lecturer)/herd-clusters                 P3 NEW
/(lecturer)/survival                      P5 NEW — tipping point view
/(lecturer)/curriculum/edit-graph         P5 NEW — KG editor per course
/(lecturer)/copilot                       P6 NEW — Instructor Co-pilot
/(lecturer)/explain/risk/[student_id]     P6 NEW — XAI panel
/(lecturer)/emergency/[id]                P4 NEW (counselor only)
/(lecturer)/emergency/queue               P4 NEW (counselor only)
```

### 3.4 RBAC

Lecturer scope strict per [privacy-gate skill](../.ruler/skills/privacy-gate/SKILL.md):

```python
def get_queryset(self):
    if user.role == User.Role.LECTURER:
        return Model.objects.filter(
            student__classmembership__student_class__lecturerassignment__lecturer=user
        )
```

Counselor flag adds: access to emergency events for assigned students.

### 3.5 Counselor sub-role

Per [EMERGENCY_RESPONSE_TRAINING.md](EMERGENCY_RESPONSE_TRAINING.md). 8h training + certification quiz. Annual recertification.

Additional permissions:
- Read encrypted emergency event details (audit logged)
- Respond in counselor queue
- Trigger emergency_contact (audit logged)
- Schedule follow-up

## 4. Content Creator (NEW role, P6)

### 4.1 Purpose

Design + maintain curriculum content. Currently lecturer or admin does this — P6 splits into dedicated role for institutions có content team.

### 4.2 Capabilities

- Create/edit Courses, Concepts, MicroTasks
- Edit Knowledge Graph prerequisites (P5B)
- A/B test content variants (via P0 causal framework)
- View aggregated content effectiveness (which task best teaches concept X)
- (No access to individual student data)

### 4.3 UI surface

```
/(content-creator)/courses                P6 NEW
/(content-creator)/courses/[id]/concepts  P6 NEW
/(content-creator)/concepts/[id]/tasks    P6 NEW
/(content-creator)/curriculum/graph       P6 NEW (full KG editor, all courses)
/(content-creator)/ab-test                P6 NEW (causal framework UI)
/(content-creator)/effectiveness          P6 NEW (DP-protected aggregates)
```

### 4.4 RBAC

`accounts.User.role = "content_creator"` (new role enum value).

```python
class ContentCreatorPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.Role.CONTENT_CREATOR
    
    def has_object_permission(self, request, view, obj):
        # Content creator scoped to assigned courses (via new ContentCreatorAssignment)
        return obj.course in request.user.content_assignments.values_list("course", flat=True)
```

No access to student individual data — only aggregated, DP-protected.

### 4.5 Onboarding

Training course (4h):
- KG design principles
- Curriculum design + Cognitive Load Theory ([LEARNING_SCIENCE_FOUNDATIONS.md](LEARNING_SCIENCE_FOUNDATIONS.md) section 2.7)
- A/B test methodology + causal framework
- Privacy boundaries (no individual data)

## 5. Admin

### 5.1 Existing capabilities (preserved)

- User management (CRUD)
- Class management
- System config
- Privacy operations (consent, export, retention)
- Analytics dashboard

### 5.2 New capabilities

| Phase | New feature |
|---|---|
| P0 | MLflow + Feast + Evidently full access, model registry |
| P0 | Causal experiment management (admin-only endpoints) |
| P0 | Fairness audit reports + CI gate config |
| P1 | RiskScore weights config |
| P3 | Cohort + herd cluster review |
| P4 | Coach config (provider, budget, intent routing), emergency pipeline config, counselor certification |
| P5 | DKT model retrain + version control, bandit exploration cap config |
| P6 | XAI cache + epsilon budget management, FinOps dashboard, parent role assignment |

### 5.3 UI surface

```
/(admin)/dashboard                       (existing)
/(admin)/users                            (existing)
/(admin)/classes                          (existing)
/(admin)/analytics                        (existing, expanded)
/(admin)/mlops                            P0 NEW
/(admin)/causal/experiments               P0 NEW
/(admin)/fairness/reports                 P0 NEW
/(admin)/coach/config                     P4 NEW
/(admin)/emergency/config                 P4 NEW
/(admin)/finops                           P6 NEW
/(admin)/dkt/models                       P5 NEW
/(admin)/parent/approve-requests          P6 NEW
```

### 5.4 RBAC

Full access. Audit log every admin action (existing `AuditMiddleware` covers).

### 5.5 Privacy boundaries

Admin can access PII for ops purpose, but:
- Audit log mandatory
- Emergency event detail requires emergency-flag (not just admin)
- Annual access review — remove unnecessary admins

## 6. Parent/Sponsor (NEW role, P6)

### 6.1 Purpose

Awareness of student progress. Particularly valuable cho:
- Năm 1 sinh viên (parent involved transition)
- Sponsored students (sponsor follow ROI)

### 6.2 Capabilities

- View student aggregated progress (mastery composite, completion %, weekly goal completion)
- Receive milestone notifications (configurable: weekly summary, completion alerts)
- (No detail access: NO chat content, NO behavioral signals, NO emergency events, NO individual scores)

### 6.3 UI surface

```
/(parent)/dashboard                       P6 NEW
/(parent)/students/[id]/progress          P6 NEW (read-only aggregated)
/(parent)/notifications                   P6 NEW
/(parent)/preferences                     P6 NEW (notification freq, opt-out)
```

### 6.4 RBAC + 2-way consent

`accounts.User.role = "parent_sponsor"` (new role).

`accounts.ParentStudentLink` (new model):

```python
class ParentStudentLink(models.Model):
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="children_links")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="parent_links")
    
    class Status(models.TextChoices):
        PENDING_BOTH = "pending_both", "Cần cả 2 confirm"
        PENDING_PARENT = "pending_parent", "Đợi parent confirm"
        PENDING_STUDENT = "pending_student", "Đợi student confirm"
        ACTIVE = "active", "Active"
        REVOKED_PARENT = "revoked_parent", "Parent revoke"
        REVOKED_STUDENT = "revoked_student", "Student revoke"
    
    status = models.CharField(choices=Status.choices, max_length=30)
    student_consent_at = models.DateTimeField(null=True)
    parent_consent_at = models.DateTimeField(null=True)
    revoked_at = models.DateTimeField(null=True)
```

Activation requires both `student_consent_at` AND `parent_consent_at`. Revoke from either side terminates.

### 6.5 Data exposure (strict)

Parent view shows ONLY:

| Visible | Hidden |
|---|---|
| Mastery composite % (overall) | Per-concept mastery detail |
| Completion % weekly | Individual task scores |
| Weekly goal set/completed count | Goal content |
| Last login date | Behavioral signals |
| | Coach chat content |
| | Emergency events |
| | Calibration data |
| | Risk score |
| | Peer interactions |

If parent requests more detail, prompted: "Đây là privacy của con bạn. Hãy nói chuyện trực tiếp với con để biết thêm. PALP tôn trọng quyền riêng tư mỗi sinh viên."

### 6.6 Notification

Default: weekly summary email (Saturday 18:00 ICT).

```
"Báo cáo tuần [N] cho [STUDENT_NAME]:
- Hoàn thành: X / Y mục tiêu tuần
- Tiến độ tổng: 72% (tăng +3% so với tuần trước)
- Học X giờ tuần này

(Chi tiết bạn có thể trao đổi trực tiếp với con. PALP tôn trọng privacy mỗi sinh viên.)"
```

Parent có thể tắt notification anytime.

### 6.7 Anti-coercion safeguards

- Lecturer có thể flag suspected coercion (e.g., student forced to consent)
- Counselor outreach if flagged
- Sv revoke without parent notification
- Annual reminder cho student: "Bạn vẫn muốn parent xem progress?"

## 7. Cross-stakeholder workflows

### 7.1 Lecturer + Student communication

Existing intervention API ([dashboard/views.py](../backend/dashboard/views.py)). Enhanced P4 với CoachTrigger integration.

### 7.2 Content Creator + Lecturer

Lecturer can flag content effectiveness ("This task confused 80% of class") → Content Creator queue for revision.

### 7.3 Counselor + Emergency Contact

Per [EMERGENCY_RESPONSE_TRAINING.md](EMERGENCY_RESPONSE_TRAINING.md). Strict trigger.

### 7.4 Parent + Lecturer

Lecturer can request parent meeting via student (with consent). Parent can request lecturer meeting via formal channel.

### 7.5 Admin + ALL

Admin can assist any role with technical issues. Audit logged.

## 8. Onboarding by role

| Role | Onboarding length | Materials |
|---|---|---|
| Student | 5-15 min | [COLD_START_PLAYBOOK.md](COLD_START_PLAYBOOK.md) |
| Lecturer | 2 hours | LMS basics + intervention principles |
| Counselor (lecturer add-on) | 8 hours | [EMERGENCY_RESPONSE_TRAINING.md](EMERGENCY_RESPONSE_TRAINING.md) section 6 |
| Content Creator | 4 hours | KG design, CLT, A/B test |
| Admin | 4 hours | System architecture, ops, privacy |
| Parent | 30 min self-paced | Welcome video + privacy guide |

## 9. Migration from current state

### 9.1 Existing users

- All existing students/lecturers/admins keep current role
- New role assignments (counselor, content_creator) via admin manual
- Parent role: invite-only via student request

### 9.2 Backfill

`accounts/migrations/00XX_add_new_roles.py`:

```python
class Migration:
    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                max_length=30,
                choices=[
                    ("student", "Student"),
                    ("lecturer", "Lecturer"),
                    ("admin", "Admin"),
                    ("content_creator", "Content Creator"),  # P6 new
                    ("parent_sponsor", "Parent / Sponsor"),   # P6 new
                ],
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="counselor_certified",
            field=models.BooleanField(default=False),
        ),
    ]
```

## 10. Stakeholder voice in product

Each role has feedback channel:

- Student: in-app feedback widget, quarterly survey (IMI scale + qualitative)
- Lecturer: monthly office hours with PM, dashboard satisfaction NPS
- Counselor: monthly debrief with mental health team
- Content Creator: quarterly content effectiveness review
- Admin: tech debt + ops issues weekly sync
- Parent: optional annual survey

## 11. Skills + related docs

- [privacy-gate skill](../.ruler/skills/privacy-gate/SKILL.md) — RBAC for new roles
- [PRIVACY_V2_DPIA.md](PRIVACY_V2_DPIA.md) — consent for parent_sponsor_view
- [EMERGENCY_RESPONSE_TRAINING.md](EMERGENCY_RESPONSE_TRAINING.md) — counselor sub-role
- [instructor-copilot skill](../.ruler/skills/instructor-copilot/SKILL.md) — Lecturer P6 features

## 12. Living document

Update khi:
- New role added (e.g., teaching assistant)
- Permission scope adjustment
- Feedback reveals UX gap per role
