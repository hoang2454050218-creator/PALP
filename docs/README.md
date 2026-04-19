# Tài liệu PALP

Điểm vào chính của dự án giờ nằm ở [`../README.md`](../README.md). File này đóng vai trò **documentation index** để điều hướng sang tài liệu chuyên sâu theo từng mảng.

## Bắt đầu từ đâu?

- Muốn hiểu nhanh hệ thống, kiến trúc, cách chạy local, API surface và module map: đọc [`../README.md`](../README.md)
- Muốn đi sâu vào kiến trúc và data model: bắt đầu với `ARCHITECTURE.md` và `DATA_MODEL.md`
- Muốn chạy test, release, migration, hoặc xử lý sự cố: xem nhóm tài liệu vận hành bên dưới

## 1. Kiến trúc và thiết kế hệ thống

| Tài liệu | Nội dung |
|---------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Kiến trúc tổng thể, boundary giữa frontend/backend/infra |
| [DATA_MODEL.md](DATA_MODEL.md) | Mô hình dữ liệu chính và quan hệ domain |
| [API.md](API.md) | Tài liệu API ở mức tổng quan |
| [API_CONTRACT.md](API_CONTRACT.md) | Contract, ràng buộc và nguyên tắc tránh breaking change |
| [adr/README.md](adr/README.md) | Chỉ mục ADR và các quyết định kỹ thuật quan trọng |

## 2. Chất lượng, test và bàn giao

| Tài liệu | Nội dung |
|---------|----------|
| [TESTING.md](TESTING.md) | Hướng dẫn chạy test local/CI, markers, coverage, E2E |
| [QA_STANDARD.md](QA_STANDARD.md) | Chuẩn chất lượng, gating, release quality bar |
| [TEST_TRACEABILITY.md](TEST_TRACEABILITY.md) | Mapping giữa yêu cầu và test coverage |
| [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) | Checklist DoD cho ticket/PR |
| [UAT_SCRIPT.md](UAT_SCRIPT.md) | Kịch bản UAT |
| [HANDOVER_REPORT.md](HANDOVER_REPORT.md) | Tài liệu handover |

## 3. Release, migration và vận hành

| Tài liệu | Nội dung |
|---------|----------|
| [DEPLOYMENT.md](DEPLOYMENT.md) | Triển khai môi trường |
| [RELEASE_RUNBOOK.md](RELEASE_RUNBOOK.md) | Quy trình release chi tiết |
| [RELEASE_GATE_QUICKREF.md](RELEASE_GATE_QUICKREF.md) | Tóm tắt nhanh release gate |
| [MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md) | Quy trình migration an toàn |
| [PRIVACY_INCIDENT.md](PRIVACY_INCIDENT.md) | Xử lý sự cố liên quan privacy |

## 4. Product, planning và bối cảnh dự án

| Tài liệu | Nội dung |
|---------|----------|
| [PRD.md](PRD.md) | Product requirements |
| [SPRINT_PLAN.md](SPRINT_PLAN.md) | Kế hoạch sprint |
| [POST_PILOT_ROADMAP.md](POST_PILOT_ROADMAP.md) | Hướng phát triển sau pilot |
| [NOTEBOOKLM_SYSTEM_OVERVIEW.md](NOTEBOOKLM_SYSTEM_OVERVIEW.md) | Tóm tắt hệ thống phục vụ trao đổi/triển khai |

## 5. ADR đang có

Thư mục [`adr/`](adr/) hiện bao gồm các quyết định sau:

- JWT trong httpOnly cookie
- BKT vs DKT
- Celery vs Kafka
- Fernet vs pgcrypto
- Docker Compose pilot vs Kubernetes phase 2
- Next.js App Router
- Spectacular + oasdiff
- PgBouncer transaction pooling

## 6. Nguyên tắc dùng bộ tài liệu này

- `README.md` ở root là nơi mô tả **trạng thái hệ thống hiện tại**
- `docs/` là nơi chứa **tài liệu chuyên đề**
- Khi behavior hệ thống thay đổi, hãy ưu tiên cập nhật root README trước, sau đó cập nhật tài liệu chuyên sâu liên quan
