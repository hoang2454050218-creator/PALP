## Ticket / issue

- Closes: <!-- ví dụ #123 -->
- Loại: <!-- feature | bugfix | chore | infra -->

## Mô tả ngắn

<!-- Mục đích thay đổi, phạm vi, rủi ro -->

## Definition of Done (PALP)

> Mỗi dòng phải được tick `[x]` **hoặc** ghi `N/A — lý do` trước khi merge (trừ khi policy team khác).

- [ ] **D1** Code review: ít nhất 1 approval; comment bắt buộc đã resolve / có follow-up ID
- [ ] **D2** Unit test pass (CI xanh cho phần thay đổi)
- [ ] **D3** Integration test pass (nếu ticket chạm luồng đa lớp / DB / API)
- [ ] **D4** Negative test (401/403/404/400, validation, RBAC sai — không chỉ happy path)
- [ ] **D5** Analytics event đã gắn theo taxonomy — hoặc `N/A`
- [ ] **D6** Audit log đã gắn nếu cần (PII / sensitive) — hoặc `N/A`
- [ ] **D7** Copy/UI: empty / loading / error / success đầy đủ — hoặc `N/A` (backend-only)
- [ ] **D8** Accessibility cơ bản — hoặc `N/A` (non-UI)
- [ ] **D9** Monitoring hook (log `request_id` / Sentry / error boundary) phù hợp
- [ ] **D10** Docs đã cập nhật (API / ARCHITECTURE / DATA_MODEL nếu đổi hợp đồng) — hoặc `N/A`
- [ ] **D11** PO sign-off trên staging — hoặc `N/A` (theo policy)
- [ ] **D12** QA sign-off — hoặc `N/A` (theo policy)

### Exemptions (nếu có)

<!-- PO/Tech Lead: waive item nào, lý do, follow-up ticket -->

## Ghi chú reviewer

<!-- Điểm cần chú ý: migration, feature flag, rollback -->
