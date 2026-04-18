# ADR-001: JWT trong httpOnly cookie thay vì Authorization header

* Status: Accepted
* Date: 2026-04
* Deciders: Tech Lead, Security Lead
* Tags: security, authentication, frontend

## Context và Problem Statement

PALP cần lưu access + refresh token cho session người dùng (sinh viên, giảng
viên, admin). Hai lựa chọn phổ biến:

1. Lưu trong `localStorage`/`sessionStorage`, gửi qua header
   `Authorization: Bearer ...`.
2. Lưu trong cookie `HttpOnly` + `Secure` + `SameSite=Strict`, browser tự
   gửi kèm mỗi request cùng origin.

Yêu cầu chính:

* Bảo vệ chống XSS exfiltrate token (educational platform có nhiều input
  từ giảng viên qua admin / content authoring).
* Bảo vệ chống CSRF khi cookie được gửi tự động.
* UX mượt: refresh token tự động khi access token hết hạn.

## Decision

Lưu access + refresh token trong cookie `HttpOnly`, `Secure` (production),
`SameSite=Strict`, prefix `__Host-` cho production. Endpoint
`POST /api/auth/token/refresh/` đọc refresh từ cookie thay vì body.

CSRF được mitigate bằng:
1. SameSite=Strict ngăn cross-site request gửi kèm cookie.
2. CORS allowlist chỉ origin tin cậy.
3. CSRF middleware Django cho non-idempotent request từ same-origin.

## Consequences

### Positive

* JavaScript phía client không thể đọc token → chống XSS exfiltration hoàn toàn.
* Refresh token rotation + blacklist (`rest_framework_simplejwt`).
* UX không cần code lưu/đọc token trong frontend.

### Negative

* Không gửi được token cross-origin từ tool ngoài (Postman cần copy cookie).
  Mitigation: API docs Swagger UI dùng cookie auth helper.
* Mobile native app (phase 2) cần wrapper HTTP client biết handle cookie jar.

## Alternatives considered

* **Bearer token trong localStorage**: rủi ro XSS quá cao cho EdTech (nhiều
  content user-generated từ lecturer).
* **Sessionid cổ điển Django**: cần backend session store, không scale tốt
  với multi-instance + Celery worker.

## References

* OWASP cheatsheet: JWT for Java
* `backend/accounts/authentication.py` `CookieJWTAuthentication`
* `backend/accounts/views.py` `_set_auth_cookies` / `_clear_auth_cookies`
