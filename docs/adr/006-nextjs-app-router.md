# ADR-006: Next.js 14 App Router + standalone output

* Status: Accepted
* Date: 2026-04
* Deciders: Frontend Lead, UX Lead
* Tags: frontend, framework

## Context

PALP cần frontend SPA-like với:
* SEO cho landing page (mặc dù chủ yếu sau login).
* Server-side rendering cho dashboard có data lớn (giảm time-to-interactive).
* File-based routing đơn giản cho 12+ page.
* Type-safety + DX tốt cho team frontend nhỏ.

Lựa chọn:
1. **Next.js 14 App Router** (React Server Components + streaming).
2. **Vite + React Router 6** (CSR-only, đơn giản hơn).
3. **Remix** (server-first, similar Next).

## Decision

Sử dụng **Next.js 14 App Router + standalone output**:
* App Router: layout groups `(student)`, `(lecturer)`, `(auth)` cho RBAC.
* Server Components mặc định, client component opt-in với `"use client"`.
* Standalone output: production image chỉ cần `node server.js`, không cần
  `node_modules` runtime → image nhẹ ~150MB.
* Rewrites proxy `/api/*` → backend container qua `BACKEND_INTERNAL_URL`.

## Consequences

### Positive

* Layout groups tự động enforce RBAC qua route guards.
* Server Components giảm bundle size client (Recharts chỉ tải trên page có chart).
* Rewrites giải quyết CSP cross-origin issue (browser stays same-origin).
* Standalone output dễ deploy K8s phase 2.

### Negative

* Learning curve App Router cho dev mới (RSC mental model).
* `"use client"` boundary phải đặt cẩn thận, lỗi phổ biến.
* Hot reload đôi khi flaky với Server Components.
* Mitigation: code review checklist + Storybook stories cho client component.

## Alternatives considered

* **Vite + React Router**: bundle nhẹ hơn, đơn giản hơn nhưng mất SSR và
  streaming - dashboard load chậm hơn 200-500ms.
* **Remix**: server-first thực sự nhưng community Việt Nam ít, recruiting khó.

## References

* `frontend/next.config.js` (output: standalone, rewrites, CSP, skipTrailingSlashRedirect)
* `frontend/src/app/(student|lecturer|auth)/layout.tsx` (route guards)
* `frontend/Dockerfile.prod` (standalone runtime stage)
