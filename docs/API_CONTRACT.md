# PALP API Contract Catalog

> Every endpoint in this catalog specifies the **8 mandatory fields** required by
> the PALP API Standard (Section 13.1 of the competition doc).
>
> **Breaking-change rule**: Removing an endpoint, changing response types,
> adding required request fields, or changing HTTP method requires a versioned
> deprecation cycle and OpenAPI diff CI check.

## Error Envelope (all endpoints)

```json
{
  "error": {
    "code":       "VALIDATION_ERROR",
    "message":    "Dữ liệu không hợp lệ.",
    "details":    { "task_id": ["This field is required."] },
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Standard Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `VALIDATION_ERROR` | 400 | Request body / params invalid |
| `AUTHENTICATION_REQUIRED` | 401 | Missing or expired token |
| `AUTHENTICATION_FAILED` | 401 | Wrong credentials |
| `TOKEN_EXPIRED` | 401 | JWT access token expired |
| `PERMISSION_DENIED` | 403 | Role / object-level access denied |
| `NOT_FOUND` | 404 | Resource does not exist |
| `METHOD_NOT_ALLOWED` | 405 | Wrong HTTP method |
| `CONFLICT` | 409 | Concurrent idempotency collision |
| `DUPLICATE_REQUEST` | 409 | Idempotency key replay |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Wrong Content-Type |
| `THROTTLED` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Unhandled server error (no detail leaked) |

---

## 1. Authentication (`/api/auth/`)

### 1.1 POST /auth/login/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/auth/login/` |
| **Auth** | `AllowAny` |
| **Request schema** | `{ username: string, password: string }` |
| **Response schema (200)** | `{ access: string, refresh: string }` |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_FAILED` (401), `THROTTLED` (429) |
| **Idempotency** | Not applicable (auth endpoint) |
| **Audit** | No |

### 1.2 POST /auth/logout/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/auth/logout/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | `{ refresh?: string }` (also reads cookie `palp_refresh`) |
| **Response schema (200)** | `{ detail: string }` |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | Not applicable |
| **Audit** | No |

### 1.3 POST /auth/token/refresh/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/auth/token/refresh/` |
| **Auth** | `AllowAny` |
| **Request schema** | `{ refresh?: string }` (also reads cookie `palp_refresh`) |
| **Response schema (200)** | `{ access: string, refresh: string }` |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_FAILED` (401) |
| **Idempotency** | Not applicable |
| **Audit** | No |

### 1.4 POST /auth/register/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/auth/register/` |
| **Auth** | `AllowAny` |
| **Request schema** | `{ username: string, email: string, password: string(min=8), first_name: string, last_name: string, student_id: string, phone?: string }` |
| **Response schema (201)** | `{ id: int, username: string, email: string, first_name: string, last_name: string, student_id: string }` |
| **Error codes** | `VALIDATION_ERROR` (400), `THROTTLED` (429) |
| **Idempotency** | Not applicable (creates unique user; DB unique constraint on username) |
| **Audit** | No |

### 1.5 GET /auth/profile/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/auth/profile/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | `{ id, username, email, role, first_name, last_name, student_id, phone, consent_given, consent_given_at }` |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware — sensitive prefix) |

### 1.6 PUT /auth/profile/

| Field | Value |
|-------|-------|
| **Method** | `PUT` |
| **Path** | `/api/auth/profile/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | `{ first_name: string, last_name: string, email: string, phone?: string }` |
| **Response schema (200)** | Same as GET /auth/profile/ |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | Naturally idempotent (PUT semantics) |
| **Audit** | Yes (AuditMiddleware) |

### 1.7 POST /auth/consent/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/auth/consent/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | `{ consent_given: boolean }` |
| **Response schema (200)** | User profile object |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | Naturally idempotent (sets flag) |
| **Audit** | No (legacy; use /api/privacy/consent/ for audited consent) |

### 1.8 GET /auth/classes/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/auth/classes/` |
| **Auth** | `IsLecturerOrAdmin` |
| **Request schema** | None |
| **Response schema (200)** | Paginated `{ count, next, previous, results: [{ id, name, academic_year }] }` |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware) |

### 1.9 GET /auth/classes/{class_id}/students/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/auth/classes/{class_id}/students/` |
| **Auth** | `IsLecturerOrAdmin` + `IsClassMember` |
| **Request schema** | None |
| **Response schema (200)** | Paginated list of user objects |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware) |

### 1.10 GET /auth/export/my-data/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/auth/export/my-data/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | Export JSON |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `THROTTLED` (429) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware + ExportThrottle) |

### 1.11 GET /auth/export/class/{class_id}/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/auth/export/class/{class_id}/` |
| **Auth** | `IsLecturerOrAdmin` |
| **Request schema** | None |
| **Response schema (200)** | Export JSON |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403), `THROTTLED` (429) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes |

### 1.12 POST /auth/delete-my-data/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/auth/delete-my-data/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | `{}` |
| **Response schema (200)** | `{ detail: string }` |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | Naturally idempotent (delete is re-entrant) |
| **Audit** | Yes |

---

## 2. Assessment (`/api/assessment/`)

### 2.1 GET /assessment/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/assessment/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | Query params: `?page=N` |
| **Response schema (200)** | Paginated `{ count, next, previous, results: [{ id, title, course, time_limit_minutes, is_active }] }` |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 2.2 GET /assessment/{id}/questions/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/assessment/{id}/questions/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | Paginated list of questions (without `correct_answer`) |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `NOT_FOUND` (404) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 2.3 POST /assessment/{id}/start/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/assessment/{id}/start/` |
| **Auth** | `IsAuthenticated` + `IsStudent` |
| **Request schema** | None (empty body) |
| **Response schema (201)** | `{ id, assessment, status, started_at, answered_question_ids, server_now }` |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404) |
| **Idempotency** | **Required** (`Idempotency-Key` header, 24h TTL). Existing in-progress session is returned as 200. |
| **Audit** | Yes (emits `assess_resumed` on re-entry) |

### 2.4 POST /assessment/sessions/{session_id}/answer/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/assessment/sessions/{session_id}/answer/` |
| **Auth** | `IsAuthenticated` + `IsStudent` |
| **Request schema** | `{ question_id: int, answer: string, time_taken_seconds: int, client_version?: int }` |
| **Response schema (200)** | `{ is_correct: boolean, response_id: int, version: int }` |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404), `THROTTLED` (429) |
| **Idempotency** | **Required** (`Idempotency-Key` header, 24h TTL) |
| **Audit** | No |

### 2.5 POST /assessment/sessions/{session_id}/complete/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/assessment/sessions/{session_id}/complete/` |
| **Auth** | `IsAuthenticated` + `IsStudent` |
| **Request schema** | None |
| **Response schema (200)** | `{ session: {...}, profile: {...} }` |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404) |
| **Idempotency** | **Required** (`Idempotency-Key` header, 24h TTL) |
| **Audit** | Yes (assessment_completed event) |

### 2.6 GET /assessment/my-sessions/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/assessment/my-sessions/` |
| **Auth** | `IsAuthenticated` + `IsStudent` |
| **Request schema** | None |
| **Response schema (200)** | Paginated list of assessment sessions |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 2.7 GET /assessment/profile/{course_id}/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/assessment/profile/{course_id}/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | `{ overall_score, strengths, weaknesses, initial_mastery }` |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `NOT_FOUND` (404) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware) |

### 2.8 GET /assessment/profile/{course_id}/student/{student_id}/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/assessment/profile/{course_id}/student/{student_id}/` |
| **Auth** | `IsLecturerOrAdmin` + `IsStudentInLecturerClass` |
| **Request schema** | None |
| **Response schema (200)** | Same as 2.7 |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware) |

---

## 3. Curriculum (`/api/curriculum/`)

### 3.1 GET /curriculum/courses/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/curriculum/courses/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | Paginated course list |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 3.2 GET /curriculum/courses/{id}/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/curriculum/courses/{id}/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | Course detail object |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `NOT_FOUND` (404) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 3.3 GET /curriculum/courses/{course_id}/concepts/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/curriculum/courses/{course_id}/concepts/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | List of concept objects |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 3.4 GET /curriculum/courses/{course_id}/milestones/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/curriculum/courses/{course_id}/milestones/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | List of milestone objects |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 3.5 GET /curriculum/milestones/{id}/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/curriculum/milestones/{id}/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | Milestone detail with tasks |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `NOT_FOUND` (404) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 3.6 GET /curriculum/tasks/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/curriculum/tasks/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | Query params: `?milestone=N&concept=N` |
| **Response schema (200)** | Paginated task list |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 3.7 POST /curriculum/tasks/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/curriculum/tasks/` |
| **Auth** | `IsLecturerOrAdmin` |
| **Request schema** | `{ milestone: int, concept: int, title: string, difficulty: int, estimated_minutes: int, content: json }` |
| **Response schema (201)** | Task object |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | Optional (`Idempotency-Key` header) |
| **Audit** | No |

### 3.8 GET /curriculum/concepts/{concept_id}/content/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/curriculum/concepts/{concept_id}/content/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | List of supplementary content objects |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 3.9 GET /curriculum/my-enrollments/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/curriculum/my-enrollments/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | List of enrollment objects |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

---

## 4. Adaptive Engine (`/api/adaptive/`)

### 4.1 GET /adaptive/mastery/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/adaptive/mastery/` |
| **Auth** | `IsAuthenticated` + `IsStudent` |
| **Request schema** | Query: `?course=N` |
| **Response schema (200)** | Paginated `[{ id, concept, p_mastery, attempt_count, correct_count }]` |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 4.2 POST /adaptive/submit/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/adaptive/submit/` |
| **Auth** | `IsAuthenticated` + `IsStudent` |
| **Request schema** | `{ task_id: int, answer: json, duration_seconds: int(>=0), hints_used: int(>=0, default=0) }` |
| **Response schema (200)** | `{ attempt: {...}, mastery: {...}, pathway: {...} }` |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404), `THROTTLED` (429) |
| **Idempotency** | **Required** (`Idempotency-Key` header, 24h TTL) |
| **Audit** | Yes (emits `micro_task_completed` event with request_id) |

### 4.3 GET /adaptive/pathway/{course_id}/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/adaptive/pathway/{course_id}/` |
| **Auth** | `IsAuthenticated` + `IsStudent` |
| **Request schema** | None |
| **Response schema (200)** | Pathway state object |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 4.4 GET /adaptive/next-task/{course_id}/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/adaptive/next-task/{course_id}/` |
| **Auth** | `IsAuthenticated` + `IsStudent` |
| **Request schema** | None |
| **Response schema (200)** | Task object or `{ detail: string, completed: true }` |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 4.5 GET /adaptive/attempts/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/adaptive/attempts/` |
| **Auth** | `IsAuthenticated` + `IsStudent` |
| **Request schema** | Query: `?task=N` |
| **Response schema (200)** | List of attempt objects (max 50) |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 4.6 GET /adaptive/interventions/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/adaptive/interventions/` |
| **Auth** | `IsAuthenticated` + `IsStudent` |
| **Request schema** | None |
| **Response schema (200)** | List of content intervention objects (max 20) |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 4.7 GET /adaptive/student/{student_id}/mastery/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/adaptive/student/{student_id}/mastery/` |
| **Auth** | `IsLecturerOrAdmin` + `IsStudentInLecturerClass` |
| **Request schema** | None |
| **Response schema (200)** | Paginated mastery list |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware — sensitive prefix) |

---

## 5. Dashboard (`/api/dashboard/`)

### 5.1 GET /dashboard/class/{class_id}/overview/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/dashboard/class/{class_id}/overview/` |
| **Auth** | `IsLecturerOrAdmin` + object-level `_verify_class_access` |
| **Request schema** | None |
| **Response schema (200)** | `{ total_students, on_track, needs_attention, needs_intervention, active_alerts, avg_mastery, avg_completion_pct, data_sufficient }` |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware) |

### 5.2 GET /dashboard/alerts/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/dashboard/alerts/` |
| **Auth** | `IsLecturerOrAdmin` |
| **Request schema** | Query: `?class_id=N&severity=red&status=active` |
| **Response schema (200)** | Paginated alert list |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware) |

### 5.3 POST /dashboard/alerts/{id}/dismiss/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/dashboard/alerts/{id}/dismiss/` |
| **Auth** | `IsLecturerOrAdmin` + object-level `_verify_class_access` |
| **Request schema** | `{ dismiss_reason_code: string, dismiss_note?: string }` |
| **Response schema (200)** | Alert object |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404) |
| **Idempotency** | Optional (`Idempotency-Key` header, 24h TTL) |
| **Audit** | Yes (explicit `audit_log` call — `alert_dismissed`) |

### 5.4 POST /dashboard/interventions/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/dashboard/interventions/` |
| **Auth** | `IsLecturerOrAdmin` + object-level `_verify_class_access` |
| **Request schema** | `{ alert_id: int, action_type: ChoiceField, target_student_ids: [int], message?: string }` |
| **Response schema (201)** | InterventionAction object |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404) |
| **Idempotency** | **Required** (`Idempotency-Key` header, 24h TTL) |
| **Audit** | Yes (explicit `audit_log` — `intervention_created`) |

### 5.5 GET /dashboard/interventions/history/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/dashboard/interventions/history/` |
| **Auth** | `IsLecturerOrAdmin` |
| **Request schema** | Query: `?class_id=N` |
| **Response schema (200)** | Paginated intervention list |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware) |

### 5.6 PATCH /dashboard/interventions/{id}/follow-up/

| Field | Value |
|-------|-------|
| **Method** | `PATCH` |
| **Path** | `/api/dashboard/interventions/{id}/follow-up/` |
| **Auth** | `IsLecturerOrAdmin` + object-level `_verify_class_access` |
| **Request schema** | `{ follow_up_status: ChoiceField }` |
| **Response schema (200)** | InterventionAction object |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404) |
| **Idempotency** | Naturally idempotent (PATCH sets field value) |
| **Audit** | Yes (AuditMiddleware) |

---

## 6. Events (`/api/events/`)

### 6.1 POST /events/track/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/events/track/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | `{ event_name: string, properties?: object, session_id?: string, device_type?: string, source_page?: string, idempotency_key?: string, ... }` |
| **Response schema (201)** | EventLog object |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401), `INTERNAL_ERROR` (500) |
| **Idempotency** | Built-in via `idempotency_key` field (DB unique constraint + emitter dedup) |
| **Audit** | No (is itself an audit trail) |

### 6.2 POST /events/batch/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/events/batch/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | `{ events: [{ event_name, ... }] }` |
| **Response schema (201)** | `{ tracked: int, errors: [int] }` |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | Built-in per event via `idempotency_key` |
| **Audit** | No |

### 6.3 GET /events/my/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/events/my/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | Query: `?event_name=X` |
| **Response schema (200)** | List of event objects (max 100) |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 6.4 GET /events/student/{student_id}/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/events/student/{student_id}/` |
| **Auth** | `IsLecturerOrAdmin` + `IsStudentInLecturerClass` |
| **Request schema** | None |
| **Response schema (200)** | List of event objects (max 100, filtered by LECTURER_VISIBLE_EVENTS for lecturers) |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware — sensitive prefix) |

---

## 7. Wellbeing (`/api/wellbeing/`)

### 7.1 POST /wellbeing/check/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/wellbeing/check/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | `{ continuous_minutes: int }` |
| **Response schema (200)** | `{ should_nudge: boolean, nudge?: object, message?: string }` |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | Optional (`Idempotency-Key` header, 24h TTL) |
| **Audit** | Yes (emits `wellbeing_nudge` event when nudge shown) |

### 7.2 POST /wellbeing/nudge/{id}/respond/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/wellbeing/nudge/{id}/respond/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | `{ response: ChoiceField }` |
| **Response schema (200)** | Nudge object |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401), `NOT_FOUND` (404) |
| **Idempotency** | Optional (`Idempotency-Key` header). Naturally idempotent (sets response field). |
| **Audit** | Yes (emits nudge accepted/dismissed event) |

### 7.3 GET /wellbeing/my/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/wellbeing/my/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | List of nudge objects (max 20) |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

---

## 8. Analytics (`/api/analytics/`)

### 8.1 GET /analytics/kpi/{class_id}/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/analytics/kpi/{class_id}/` |
| **Auth** | `IsLecturerOrAdmin` + `IsClassMember` |
| **Request schema** | Query: `?week=N` |
| **Response schema (200)** | KPI snapshot object |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware) |

### 8.2 GET /analytics/reports/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/analytics/reports/` |
| **Auth** | `IsAdminUser` |
| **Request schema** | None |
| **Response schema (200)** | Paginated report list |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware) |

### 8.3 GET /analytics/reports/{id}/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/analytics/reports/{id}/` |
| **Auth** | `IsAdminUser` |
| **Request schema** | None |
| **Response schema (200)** | Report detail object |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (AuditMiddleware) |

### 8.4 GET /analytics/data-quality/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/analytics/data-quality/` |
| **Auth** | `IsAdminUser` |
| **Request schema** | None |
| **Response schema (200)** | Paginated data quality log list |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

---

## 9. Privacy (`/api/privacy/`)

### 9.1 GET /privacy/consent/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/privacy/consent/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | List of consent status objects |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 9.2 POST /privacy/consent/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/privacy/consent/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | `{ consents: [{ purpose: string, granted: boolean }], version?: string }` |
| **Response schema (200)** | List of consent status objects |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | Naturally idempotent (creates records; safe to re-submit) |
| **Audit** | Yes (explicit `log_audit` — `consent_change`) |

### 9.3 GET /privacy/consent/history/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/privacy/consent/history/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | List of consent records (max 100) |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 9.4 GET /privacy/export/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/privacy/export/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | Query: `?user_id=N` (admin only) |
| **Response schema (200)** | `{ meta: {...}, data: {...} }` |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404) |
| **Idempotency** | N/A (read) |
| **Audit** | Yes (explicit `log_audit` — `export`) |

### 9.5 POST /privacy/delete/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/privacy/delete/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | `{ tiers: [string] }` |
| **Response schema (200)** | `{ detail: string, request: {...}, summary: {...} }` |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | **Required** (`Idempotency-Key` header, 24h TTL) |
| **Audit** | Yes (via `delete_user_data` internal audit) |

### 9.6 GET /privacy/delete/requests/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/privacy/delete/requests/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | None |
| **Response schema (200)** | List of deletion request objects (max 50) |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 9.7 GET /privacy/audit-log/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/privacy/audit-log/` |
| **Auth** | `IsAuthenticated` |
| **Request schema** | Query: `?user_id=N` (admin only) |
| **Response schema (200)** | List of audit log objects (max 100) |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401) |
| **Idempotency** | N/A (read) |
| **Audit** | No (is itself the audit trail) |

### 9.8 GET /privacy/incidents/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/privacy/incidents/` |
| **Auth** | `IsAdminUser` |
| **Request schema** | None |
| **Response schema (200)** | List of incident objects (max 50) |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 9.9 POST /privacy/incidents/

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/api/privacy/incidents/` |
| **Auth** | `IsAdminUser` |
| **Request schema** | `{ severity: ChoiceField, title: string, description: string, affected_user_count?: int, affected_data_tiers?: [string] }` |
| **Response schema (201)** | Incident object |
| **Error codes** | `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | Optional (`Idempotency-Key` header) |
| **Audit** | Yes (explicit `log_audit` — `incident`) |

---

## 10. Health (`/api/health/`)

### 10.1 GET /health/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/health/` |
| **Auth** | `AllowAny` |
| **Request schema** | None |
| **Response schema (200)** | `{ status: "ok" }` |
| **Error codes** | None |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 10.2 GET /health/ready/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/health/ready/` |
| **Auth** | `AllowAny` |
| **Request schema** | None |
| **Response schema (200)** | `{ status: "ok", checks: {...} }` |
| **Error codes** | `INTERNAL_ERROR` (503 — degraded) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

### 10.3 GET /health/deep/

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/health/deep/` |
| **Auth** | `IsAdminUser` |
| **Request schema** | None |
| **Response schema (200)** | Detailed health object |
| **Error codes** | `AUTHENTICATION_REQUIRED` (401), `PERMISSION_DENIED` (403) |
| **Idempotency** | N/A (read) |
| **Audit** | No |

---

## Appendix A: Idempotency Policy Summary

| Endpoint | Idempotency-Key | Policy |
|----------|----------------|--------|
| POST /adaptive/submit/ | **Required** | 24h TTL, Redis-cached response |
| POST /assessment/{id}/start/ | **Required** | 24h TTL |
| POST /assessment/sessions/{id}/answer/ | **Required** | 24h TTL |
| POST /assessment/sessions/{id}/complete/ | **Required** | 24h TTL |
| POST /dashboard/interventions/ | **Required** | 24h TTL |
| POST /privacy/delete/ | **Required** | 24h TTL |
| POST /dashboard/alerts/{id}/dismiss/ | Optional | 24h TTL |
| POST /wellbeing/check/ | Optional | 24h TTL |
| POST /wellbeing/nudge/{id}/respond/ | Optional | 24h TTL |
| POST /events/track/ | Built-in | `idempotency_key` field in body |
| POST /events/batch/ | Built-in | Per-event `idempotency_key` |
| POST /auth/login/ | N/A | Auth endpoint |
| POST /auth/register/ | N/A | DB unique constraint |
| POST /auth/logout/ | N/A | Auth endpoint |
| POST /auth/token/refresh/ | N/A | Auth endpoint |
| POST /auth/consent/ | N/A | Naturally idempotent |
| POST /privacy/consent/ | N/A | Naturally idempotent |
| POST /curriculum/tasks/ | Optional | Content management |
| POST /privacy/incidents/ | Optional | Admin only |

## Appendix B: Retry Safety

All endpoints with **Required** or **Optional** idempotency are safe to retry
with the same `Idempotency-Key` header. The cached response (status + body)
is returned verbatim for the TTL window (24 hours by default).

For endpoints without idempotency support:
- `GET`, `HEAD`, `OPTIONS` are always safe to retry.
- `PUT`, `PATCH` are safe if the request body is identical (last-write-wins).
- `DELETE` is safe (deleting an already-deleted resource returns 404).
