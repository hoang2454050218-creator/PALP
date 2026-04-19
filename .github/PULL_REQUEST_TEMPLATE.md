# Mô tả

<!-- Mô tả ngắn (1-3 câu) thay đổi và lý do (tập trung vào "why" hơn "what") -->

Closes #

## Loại thay đổi

- [ ] feat: tính năng mới
- [ ] fix: bug fix
- [ ] perf: cải thiện hiệu năng
- [ ] refactor: refactor không thay đổi behavior
- [ ] docs: chỉ tài liệu
- [ ] test: chỉ thêm/sửa test
- [ ] chore: maintenance, deps, config
- [ ] BREAKING CHANGE (giải thích migration trong section dưới)

## Definition of Done — D1-D12

(Đánh check khi xong, để trống nếu N/A nhưng giải thích lý do)

- [ ] **D1 Code review**: ≥1 approve + 0 unresolved comment
- [ ] **D2 Unit tests**: pass + coverage không giảm
- [ ] **D3 Integration tests**: pass cho flow liên quan
- [ ] **D4 Negative tests**: cho mọi input boundary
- [ ] **D5 Analytics events**: emitted nếu thay đổi UX
- [ ] **D6 Audit log**: cho action sensitive (PII, RBAC)
- [ ] **D7 UI states**: loading + empty + error + success đầy đủ
- [ ] **D8 Accessibility**: WCAG 2.1 AA min, AAA cho 3 page chính
- [ ] **D9 Monitoring**: metric + alert nếu critical path
- [ ] **D10 Documentation**: docstring + ADR nếu kiến trúc + README nếu cần
- [ ] **D11 PO sign-off**: cho user-facing change
- [ ] **D12 QA sign-off**: per `docs/QA_STANDARD.md`

## Test plan

<!-- Mô tả cách test PR này. Ví dụ:
1. just dev
2. Login với sv_test / testpass123
3. Click ... → expect ...
-->

## Screenshots / GIFs

<!-- Cho UI change, attach screenshot before/after hoặc GIF -->

## Database migration

- [ ] Có migration mới — đã `makemigrations --check` clean
- [ ] Migration backward-compatible (đọc `docs/MIGRATION_RUNBOOK.md`)
- [ ] Không drop column trong cùng release với code bỏ field

## Security & Privacy

- [ ] Không hardcode secret/key
- [ ] PII xử lý qua Fernet field (không plaintext)
- [ ] Authorization check ở backend (không chỉ frontend)
- [ ] Audit log cho action sensitive

## Breaking Changes

<!-- Nếu BREAKING CHANGE, giải thích: -->
<!-- - Field/endpoint nào bị remove/rename -->
<!-- - Migration step cho consumer -->
<!-- - Deprecation timeline nếu có -->

## AI Agent Rules (Ruler)

- [ ] Không sửa convention/architecture; HOẶC đã update `.ruler/*.md` tương ứng
- [ ] `npm run ruler:apply` đã chạy nếu sửa `.ruler/*` (CI `ruler-check.yml` enforce)
- [ ] Không sửa rule cấu trúc tuyệt đối (BKT params, Audit prefix, RBAC matrix) trừ khi có ADR

## Checklist

- [ ] Tựa đề PR tuân theo Conventional Commits format
- [ ] Branch rebase với master
- [ ] CI xanh (lint + tests + OpenAPI diff + security audit + ruler-check)
- [ ] Self-review xong, không có comment debug

## Additional notes

<!-- Bất cứ thông tin gì cho reviewer -->
