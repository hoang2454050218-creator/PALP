---
name: rbac-check
description: Lightweight RBAC validation playbook for any new view or queryset filter. Use when adding/modifying views in backend/<app>/views.py to ensure Student/Lecturer/Admin boundaries are enforced.
---

# RBAC Check — Per-Endpoint Validation

## When to use

- Adding a new `APIView` or `ViewSet` to any `backend/<app>/views.py`
- Changing `permission_classes` or `get_queryset()`
- Reviewing PR with new endpoint
- Investigating "user X seeing user Y's data" reports (P0)

## Roles (single source of truth)

`backend.accounts.models.User.Role`:

| Role | Code | Can access |
|------|------|------------|
| Student | `STUDENT` | Only own data — own mastery, pathway, submissions, events, profile |
| Lecturer | `LECTURER` | Only data from classes assigned via `LecturerClassAssignment` |
| Admin | `ADMIN` | Everything; manages users + system config; schema/docs in prod |

Cross-role access leak (student seeing other student's data, lecturer seeing unassigned class) is a **P0 security bug** — must be fixed before merge.

## Decision tree for new endpoint

```
Is the endpoint public (login, register, password reset)?
├─ YES -> permission_classes = [AllowAny] + add throttle scope
└─ NO -> Continue
   ├─ Is it admin-only (user mgmt, system config)?
   │   └─ permission_classes = [IsAuthenticated, IsAdminUser]
   ├─ Is it student data?
   │   ├─ Owner-only (mastery, profile)? -> filter queryset by request.user
   │   └─ Lecturer-readable (their assigned classes)?
   │       -> Use the canonical lecturer queryset (see below)
   ├─ Is it lecturer-only (early warning, intervention)?
   │   └─ permission_classes = [IsAuthenticated, IsLecturer]
   └─ Is it cross-role (e.g. /api/auth/profile/ for both)?
       -> permission_classes = [IsAuthenticated]
       -> queryset must include role check
```

## Canonical queryset patterns

### Student-owned data

```python
from accounts.models import User

def get_queryset(self):
    user = self.request.user
    if user.role == User.Role.STUDENT:
        return MasteryState.objects.filter(student=user)
    if user.role == User.Role.LECTURER:
        return MasteryState.objects.filter(
            student__classmembership__student_class__lecturerassignment__lecturer=user
        )
    if user.role == User.Role.ADMIN:
        return MasteryState.objects.all()
    return MasteryState.objects.none()  # default deny
```

### Lecturer-only data scoped to assigned classes

```python
def get_queryset(self):
    user = self.request.user
    if user.role != User.Role.LECTURER and user.role != User.Role.ADMIN:
        return EarlyWarning.objects.none()
    if user.role == User.Role.ADMIN:
        return EarlyWarning.objects.all()
    return EarlyWarning.objects.filter(
        student_class__lecturerassignment__lecturer=user
    )
```

### Permission-class shortcuts

`backend/accounts/permissions.py`:

```python
class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.STUDENT

class IsLecturer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.LECTURER
```

Combine: `permission_classes = [IsAuthenticated, IsLecturer]`.

## Mandatory test matrix per endpoint

```python
@pytest.mark.security
class TestEndpointRBAC:
    URL = "/api/dashboard/early-warnings/"

    def test_anon_returns_401(self, anon_api):
        assert anon_api.get(self.URL).status_code == 401

    def test_student_returns_403(self, student_api):
        assert student_api.get(self.URL).status_code == 403

    def test_lecturer_assigned_returns_200(self, lecturer_api, class_with_members):
        response = lecturer_api.get(self.URL)
        assert response.status_code == 200

    def test_lecturer_unassigned_sees_no_data(self, lecturer_api, other_class):
        response = lecturer_api.get(f"{self.URL}?class_id={other_class.id}")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert len(response.json()["results"]) == 0

    def test_admin_returns_200(self, admin_api):
        assert admin_api.get(self.URL).status_code == 200

    def test_owner_only_no_cross_user(self, student_api, student_b):
        response = student_api.get(f"{self.URL}{student_b.id}/")
        assert response.status_code in (403, 404)
```

Use existing fixtures: `anon_api`, `student_api`, `student_b`, `lecturer_api`, `admin_api`, `class_with_members` (in `backend/conftest.py`).

## Pre-merge checklist

- [ ] `permission_classes` set explicitly on view (not just global default)
- [ ] `get_queryset()` filters by `request.user` role
- [ ] Returns `Model.objects.none()` for unknown role (default deny)
- [ ] No raw SQL with user input — ORM only
- [ ] Test matrix covers anon / student / lecturer assigned / lecturer unassigned / admin / cross-user
- [ ] All RBAC tests marked `@pytest.mark.security`
- [ ] If endpoint accesses PII, also follow `privacy-gate` skill (consent + audit + encryption)

## Anti-patterns (P0 if shipped)

- Filtering only on frontend ("UI hides the button" -> attacker uses curl)
- `Model.objects.all()` returned to non-admin
- Trusting query param `?student_id=` without verifying ownership
- `self.request.user.is_staff` check (PALP uses `role`, not Django staff)
- Forgetting `permission_classes` -> falls back to global `IsAuthenticated`, may leak data
- Returning 404 instead of 403 for cross-user (info leak: confirms record exists)

## Debugging RBAC leaks

1. Reproduce: `pytest -m security -v -k <test_name>`
2. Add `print(user.role, queryset.query)` in `get_queryset()` to see the actual SQL
3. Check `AuditLog` table — was the request logged correctly?
4. File P0 issue with reproduction steps + ETA
5. Hotfix: tighten queryset, deploy, then write regression test
