# Contributing to PALP

Cảm ơn bạn quan tâm đến PALP. Tài liệu này mô tả cách đóng góp code, bug
report, hoặc tài liệu cho dự án.

## Quick Start

### Mở Codespace 1-click (khuyến nghị)

1. Click nút **Code** > **Codespaces** > **Create codespace on master**.
2. Chờ ~3 phút (lần đầu) hoặc ~30 giây (cache).
3. Stack tự động lên: backend `localhost:8000`, frontend `localhost:3000`.
4. Login test: `sv_test` / `testpass123`.

### Setup local

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate  # hoặc .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt

# Frontend
cd frontend
npm ci

# Stack đầy đủ
cd ..
docker compose up -d
docker exec cnhnha-backend-1 python manage.py migrate
docker exec -e SEED_PASSWORD=Pa55w0rd! cnhnha-backend-1 python /scripts/seed_data.py
```

Hoặc dùng `just` (cài [casey/just](https://github.com/casey/just) trước):

```bash
just dev    # docker compose up -d
just seed   # seed test data
just test   # run all tests
just lint   # ruff + eslint + tsc
```

## Workflow đóng góp

### 1. Mở issue trước khi code

* Bug report: dùng template `bug_report.yml`, kèm reproduction step.
* Feature request: dùng `feature_request.yml`, mô tả use case.
* Lớn hơn 200 LOC: discuss trong issue + ADR draft trước khi code.

### 2. Branch naming

* `feat/<short-desc>` — feature mới.
* `fix/<short-desc>` — bug fix.
* `docs/<short-desc>` — chỉ docs.
* `refactor/<short-desc>` — refactor không thay đổi behavior.
* `test/<short-desc>` — chỉ thêm/sửa test.
* `chore/<short-desc>` — bump dep, config, CI.

### 3. Commit message — Conventional Commits

Format: `type(scope): subject`. Type: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `style`, `ci`. Example:

```
feat(adaptive): add per-concept BKT param tuning
fix(privacy): consent dialog re-show on navigation
docs(adr): ADR-009 feature flags
```

Commit hook (Husky + commitlint) sẽ enforce format.

### 4. Pull Request

* Tựa đề mirror commit message format.
* Body fill template `.github/PULL_REQUEST_TEMPLATE.md` đầy đủ D1-D12 (Definition of Done).
* Link issue: `Closes #123`.
* Đảm bảo CI xanh trước khi request review.

### 5. Code review

* Reviewer: 1 reviewer + 1 approver bắt buộc, theo CODEOWNERS.
* Reviewer comment trong 24h. Approver merge sau khi resolve hết comment.
* Squash merge mặc định, commit body kept.

## Definition of Done (D1-D12)

Mỗi PR phải đạt 12 tiêu chí:

* **D1** Code review: ≥1 approve + 0 unresolved comment.
* **D2** Unit tests pass với coverage không giảm.
* **D3** Integration tests pass cho flow liên quan.
* **D4** Negative tests cho mọi input boundary.
* **D5** Analytics events emitted nếu thay đổi UX.
* **D6** Audit log cho action sensitive (PII, RBAC).
* **D7** UI states đầy đủ: loading + empty + error + success.
* **D8** Accessibility: WCAG 2.1 AA min, AAA cho 3 page chính.
* **D9** Monitoring: metric + alert nếu critical path.
* **D10** Documentation: docstring + README section nếu cần.
* **D11** PO sign-off cho user-facing change.
* **D12** QA sign-off với checklist (`docs/QA_STANDARD.md`).

## Coding Standards

### Backend Python

* Ruff (rules in `backend/pyproject.toml`) — auto-format + lint.
* Mypy strict cho `palp/` package.
* Test coverage: overall ≥80%, core modules (`adaptive`, `assessment`,
  `dashboard`, `accounts`) ≥85%, mutation score 3 modules ≥75%.
* Logger naming: `palp.<app>` ví dụ `palp.adaptive`, `palp.privacy`.
* Migration: backward-compatible only (xem `docs/MIGRATION_RUNBOOK.md`).

### Frontend TypeScript

* ESLint config Next.js + jsx-a11y rules.
* `tsc --noEmit` không error.
* Vitest tests cho `lib/`, `hooks/`, components quan trọng.
* Component có Storybook story nếu re-usable.

### Commits + branches

* Conventional commits (enforced bởi commitlint).
* Branch không quá 200 LOC nếu được; PR lớn split thành nhiều PR nhỏ.
* Rebase với `master` trước khi PR ready.

## Reporting Security Issues

Vui lòng KHÔNG mở public issue cho lỗ hổng bảo mật. Liên hệ qua
`security@palp.dau.edu.vn` (xem `SECURITY.md`).

## Giấy phép

Mọi đóng góp được license dưới Apache License 2.0 (xem `LICENSE`).
Bạn xác nhận có quyền đóng góp code và đồng ý license điều khoản.

## Liên hệ

* Maintainers: xem `GOVERNANCE.md`.
* Discussions: GitHub Discussions trong repo.
* Email: `palp@dau.edu.vn`.
