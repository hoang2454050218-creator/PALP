---
name: privacy-gate
description: Workflow for adding or modifying any endpoint that touches PII. Enforces consent, audit, RBAC, encryption, and the 15-item security checklist before merge.
---

# Privacy Gate — PII Endpoint Workflow

## When to use

- Adding any new endpoint under `/api/auth/`, `/api/dashboard/`, `/api/analytics/`, `/api/assessment/profile/`, `/api/adaptive/student/`, `/api/events/student/`, `/api/auth/classes/`, `/api/auth/export/`
- Modifying user profile, mastery export, lecturer dashboard data
- Adding a new model field that stores PII (name, email, phone, address, IP, identifiers)
- Reviewing PRs that touch `backend/privacy/` or `backend/accounts/`

## Mandatory steps (in order)

### 1. Identify PII

Anything that can identify a natural person directly or indirectly:
- Direct: name, email, phone, student_id, IP address
- Indirect (with combinations): mastery sequence + class + timestamp

If yes -> all 5 sub-steps below are mandatory.

### 2. Add consent check

`ConsentGateMiddleware` (`backend/privacy/middleware.py`) blocks the request if user hasn't consented to current `PALP_PRIVACY.CONSENT_VERSION`. Verify your endpoint URL is **not** in the consent middleware's exempt list. If you must exempt (e.g. consent endpoint itself), document why in code comment.

### 3. Encrypt at rest (Fernet)

```python
from privacy.fields import EncryptedTextField

class Profile(models.Model):
    full_name = EncryptedTextField()  # never plaintext
    email = EncryptedTextField()
```

Key: `PII_ENCRYPTION_KEY` env var (32-byte base64). Never log decrypted values. Never put PII in error responses.

### 4. Add to `AUDIT_SENSITIVE_PREFIXES`

Edit `backend/palp/settings/base.py`:

```python
AUDIT_SENSITIVE_PREFIXES = [
    ...,
    "/api/your-new-prefix/",
]
```

`AuditMiddleware` will then log every access with user_id, IP (hashed), method, path, status, and `request_id`.

### 5. Enforce RBAC in queryset

```python
def get_queryset(self):
    role = self.request.user.role
    if role == User.Role.STUDENT:
        return Model.objects.filter(student=self.request.user)
    elif role == User.Role.LECTURER:
        return Model.objects.filter(
            student__classmembership__student_class__lecturerassignment__lecturer=self.request.user
        )
    return Model.objects.none()  # default deny
```

Cross-user access leak = **P0 security bug**. Test with `student_b` fixture in `backend/conftest.py`.

## Test matrix (mandatory for every PII endpoint)

```python
class TestEndpointAccess:
    def test_owner_can_access(self, student_api): ...
    def test_other_student_cannot_access(self, student_b, student_api): ...      # 403
    def test_lecturer_assigned_class_can_access(self, lecturer_api): ...
    def test_lecturer_unassigned_class_cannot_access(self, lecturer_api): ...    # 403
    def test_admin_can_access(self, admin_api): ...
    def test_anon_cannot_access(self, anon_api): ...                              # 401
    def test_no_consent_returns_403(self, student_api): ...
    def test_response_does_not_leak_other_user_pii(self, student_api): ...
```

Mark with `@pytest.mark.security`.

## 15-item Security Checklist (review before merge)

1. [ ] PII encrypted at rest
2. [ ] TLS enforced (production)
3. [ ] JWT in httpOnly cookies only — not URL/localStorage
4. [ ] RBAC matrix tested for new endpoint
5. [ ] No SQL injection vectors — use ORM, never raw SQL with user input
6. [ ] XSS prevention — CSP headers configured in Next.js
7. [ ] CSRF protection active
8. [ ] Rate limiting via throttle scope
9. [ ] Error response does not leak internals (stack traces, ORM errors)
10. [ ] `bandit` clean on new code
11. [ ] No secrets in repo (`detect-secrets` baseline updated if needed)
12. [ ] Audit trail emits for sensitive access
13. [ ] CORS restricted via `CORS_ALLOWED_ORIGINS`
14. [ ] `DEBUG=False` honored in production
15. [ ] Consent checked before PII access

## After deploy

- Verify in Grafana: `palp_audit_log_total` increments for new prefix
- Verify in `backend/privacy/admin.py`: AuditEntry rows appear with correct `user_id`, hashed IP, status
