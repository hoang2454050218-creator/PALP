# PALP - API Reference

Base URL: `http://localhost:8000/api`

All authenticated endpoints require: `Authorization: Bearer <access_token>`

## Authentication

### POST /auth/login/
Login and receive JWT tokens.

**Request:**
```json
{ "username": "sv001", "password": "student123" }
```

**Response (200):**
```json
{ "access": "eyJ...", "refresh": "eyJ..." }
```

### POST /auth/token/refresh/
Refresh access token.

**Request:**
```json
{ "refresh": "eyJ..." }
```

### POST /auth/register/
Register new user. **Public**

### GET /auth/profile/
Get current user profile.

### PUT /auth/profile/
Update current user profile.

### POST /auth/consent/
Update privacy consent status.

**Request:**
```json
{ "consent_given": true }
```

### GET /auth/classes/
List student classes. **Lecturer/Admin**

### GET /auth/classes/{class_id}/students/
List students in a class. **Lecturer/Admin**

---

## Assessment

### GET /assessment/
List available assessments.

### GET /assessment/{id}/questions/
Get assessment questions (without correct answers).

### POST /assessment/{id}/start/
Start an assessment session. **Student**

**Response (201):**
```json
{
  "id": 1,
  "assessment": 1,
  "status": "in_progress",
  "started_at": "2026-04-16T10:00:00Z"
}
```

### POST /assessment/sessions/{session_id}/answer/
Submit an answer. **Student**

**Request:**
```json
{
  "question_id": 1,
  "answer": "qL/2",
  "time_taken_seconds": 30
}
```

### POST /assessment/sessions/{session_id}/complete/
Complete assessment and generate LearnerProfile. **Student**

**Response:**
```json
{
  "session": { "total_score": 70.0, "status": "completed" },
  "profile": {
    "overall_score": 70.0,
    "strengths": [1, 3],
    "weaknesses": [5, 8],
    "initial_mastery": { "1": 0.8, "2": 0.5 }
  }
}
```

### GET /assessment/profile/{course_id}/
Get own learner profile. **Student**

### GET /assessment/profile/{course_id}/student/{student_id}/
Get a student's profile. **Lecturer/Admin**

---

## Curriculum

### GET /curriculum/courses/
List active courses.

### GET /curriculum/courses/{id}/
Course detail.

### GET /curriculum/courses/{course_id}/concepts/
List concepts (knowledge graph nodes) for a course.

### GET /curriculum/courses/{course_id}/milestones/
List milestones for a course.

### GET /curriculum/milestones/{id}/
Milestone detail with tasks.

### GET /curriculum/tasks/
List micro-tasks. Filters: `?milestone=1&concept=2`

### POST /curriculum/tasks/
Create micro-task. **Lecturer/Admin**

### GET /curriculum/concepts/{concept_id}/content/
List supplementary content for a concept.

### GET /curriculum/my-enrollments/
List current user's enrollments. **Student**

---

## Adaptive Engine

### GET /adaptive/mastery/?course=1
Get own mastery states. **Student**

### POST /adaptive/submit/
Submit a task attempt and get adaptive feedback. **Student**

**Request:**
```json
{
  "task_id": 1,
  "answer": "qL/2",
  "duration_seconds": 120,
  "hints_used": 0
}
```

**Response:**
```json
{
  "attempt": {
    "score": 100, "is_correct": true, "attempt_number": 1
  },
  "mastery": {
    "p_mastery": 0.72, "attempt_count": 3
  },
  "pathway": {
    "action": "continue",
    "difficulty_adjustment": 0,
    "p_mastery": 0.72,
    "message": "Tiếp tục luyện tập để củng cố kiến thức."
  }
}
```

### GET /adaptive/pathway/{course_id}/
Get own pathway state. **Student**

### GET /adaptive/attempts/?task=1
Get own task attempts. **Student**

### GET /adaptive/interventions/
Get own content interventions. **Student**

### GET /adaptive/student/{student_id}/mastery/
Get a student's mastery. **Lecturer/Admin**

---

## Dashboard (Lecturer)

### GET /dashboard/class/{class_id}/overview/
Class overview statistics. **Lecturer/Admin**

**Response:**
```json
{
  "total_students": 30,
  "on_track": 22,
  "needs_attention": 5,
  "needs_intervention": 3,
  "active_alerts": 8,
  "avg_mastery": 0.65,
  "avg_completion_pct": 45.0
}
```

### GET /dashboard/alerts/?class_id=1&severity=red&status=active
List alerts. **Lecturer/Admin**

### POST /dashboard/alerts/{id}/dismiss/
Dismiss an alert with optional note. **Lecturer/Admin**

**Request:**
```json
{ "dismiss_note": "SV nghỉ ốm, đã liên hệ" }
```

### POST /dashboard/interventions/
Create an intervention action. **Lecturer/Admin**

**Request:**
```json
{
  "alert_id": 1,
  "action_type": "send_message",
  "target_student_ids": [5, 12],
  "message": "Hãy hoàn thành bài tập tuần này nhé!"
}
```

### GET /dashboard/interventions/history/
Intervention history. **Lecturer/Admin**

### PATCH /dashboard/interventions/{id}/follow-up/
Update follow-up status. **Lecturer/Admin**

---

## Events

### POST /events/track/
Track a single event.

**Request:**
```json
{
  "event_name": "session_started",
  "properties": { "page": "/dashboard" },
  "session_id": "abc123",
  "device": "desktop"
}
```

### POST /events/batch/
Track multiple events.

### GET /events/my/
Get own event history.

### GET /events/student/{student_id}/
Get student events. **Lecturer/Admin**

---

## Wellbeing

### POST /wellbeing/check/
Check if a wellbeing nudge should be shown.

**Request:**
```json
{ "continuous_minutes": 55 }
```

**Response:**
```json
{
  "should_nudge": true,
  "nudge": { "id": 1, "nudge_type": "break_reminder" },
  "message": "Bạn đã học liên tục hơn 50 phút..."
}
```

### POST /wellbeing/nudge/{id}/respond/
Record nudge response.

### GET /wellbeing/my/
Get own nudge history.

---

## Analytics

### GET /analytics/kpi/{class_id}/?week=4
Get KPI snapshot. **Lecturer/Admin**

### GET /analytics/reports/
List pilot reports. **Lecturer/Admin**

### GET /analytics/reports/{id}/
Report detail. **Lecturer/Admin**

### GET /analytics/data-quality/
Data quality logs. **Lecturer/Admin**

---

## Health Check

### GET /health/
System health status. **Public**

**Response:**
```json
{ "status": "ok" }
```

---

## Pagination

All list endpoints return paginated results:
```json
{
  "count": 100,
  "next": "http://localhost:8000/api/.../?page=2",
  "previous": null,
  "results": [...]
}
```

## Error Format

```json
{
  "detail": "Error message"
}
```

HTTP status codes: 400 (validation), 401 (unauthorized), 403 (forbidden), 404 (not found), 500 (server error).
