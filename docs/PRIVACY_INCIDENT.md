# PALP Privacy Incident Response Policy

## SLA: 48 giờ

Mọi sự cố liên quan đến quyền riêng tư và dữ liệu cá nhân phải được phản hồi
trong vòng **48 giờ** kể từ thời điểm phát hiện hoặc báo cáo.

## Quy trình xử lý

### 1. Phát hiện & Báo cáo

- Sự cố được báo cáo qua API: `POST /api/privacy/incidents/`
- Hệ thống tự động tạo SLA deadline = created_at + 48h
- Celery task `privacy.check_incident_sla` kiểm tra mỗi 60 phút

### 2. Mức độ nghiêm trọng

| Severity | Mô tả | Phản hồi |
|----------|--------|----------|
| `low` | Lỗi hiển thị, không lộ PII | Ghi nhận, sửa trong sprint tiếp |
| `medium` | PII lộ trong log nội bộ, số lượng nhỏ | Xóa log, patch ngay |
| `high` | PII lộ ra bên ngoài, nhiều user bị ảnh hưởng | Isolate, notify users, patch |
| `critical` | Dữ liệu bị truy cập trái phép ở quy mô lớn | Incident commander, full response |

### 3. Các bước xử lý

1. **Isolate** - Ngắt nguồn lộ dữ liệu (disable endpoint, revoke token, v.v.)
2. **Assess** - Xác định phạm vi: bao nhiêu user, loại dữ liệu nào
3. **Notify** - Thông báo cho user bị ảnh hưởng (nếu severity >= high)
4. **Remediate** - Fix root cause, deploy patch
5. **Document** - Cập nhật `resolution` trong PrivacyIncident record
6. **Review** - Post-mortem, cập nhật quy trình nếu cần

### 4. Kiểm tra tự động

- **PIIScrubLogFilter**: Scrub email, phone, student_id khỏi log
- **Sentry before_send**: Scrub PII khỏi error reports
- **DRF exception handler**: Scrub PII khỏi API error responses
- **AuditLog**: Ghi lại mọi truy cập dữ liệu nhạy cảm

### 5. Audit Trail

Mọi sự cố tạo AuditLog entry với:
- `action = "incident"`
- `detail` chứa incident_id, severity, title
- IP address và request_id của người báo cáo

## API Reference

```
POST /api/privacy/incidents/
{
  "severity": "high",
  "title": "PII in error logs",
  "description": "Student emails found in Sentry breadcrumbs",
  "affected_user_count": 50,
  "affected_data_tiers": ["pii"]
}

GET /api/privacy/incidents/
```

Chỉ admin có quyền tạo và xem incident reports.
