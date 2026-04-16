# PALP - Product Requirements Document

## 1. Executive Summary

PALP (Personalized Adaptive Learning Platform) là pilot EdTech có kiểm soát tại ĐH Kiến trúc Đà Nẵng, tập trung vào môn Sức Bền Vật Liệu. Mục tiêu: chứng minh adaptive pathway giúp sinh viên duy trì học chủ động tốt hơn và dashboard cảnh báo sớm giúp giảng viên can thiệp đúng lúc.

**Phạm vi pilot**: 1 môn, 2-3 lớp, 60-90 SV, 10 tuần.
**Ngân sách**: 11-24 triệu (nội bộ) hoặc 45-65 triệu (có trả nhân công).

## 2. Problem Statement

| Vấn đề | Biểu hiện | Tác động |
|--------|-----------|----------|
| Suy giảm tập trung | SV khó theo kịp lý thuyết kỹ thuật kéo dài | Nền tảng kỹ thuật yếu |
| Lý thuyết - thực tiễn tách rời | Học công thức nhưng khó liên hệ bối cảnh công trình | Đồ án dễ sai chuẩn thực tế |
| Phát hiện khó khăn muộn | GV chỉ biết SV yếu khi chấm giữa/cuối kỳ | Mất cơ hội cứu vãn |
| Dữ liệu học vụ nhiễu | Missing values, điểm danh hộ, lỗi nhập liệu | Cá nhân hóa sai nếu dùng thô |

## 3. Personas

### Tân SV năm 1
- **Pain**: Khó tập trung >15-20 phút, thấy môn kỹ thuật khô khan
- **Need**: Micro-task 5-10 phút, phản hồi tức thì, hình ảnh trực quan
- **PALP provides**: Assessment, pathway, content bổ trợ, tiến trình rõ ràng

### SV năm cuối
- **Pain**: Áp lực đồ án, cần thấy ý nghĩa thực tế
- **Need**: Mô phỏng bối cảnh thật, retry không bị phạt
- **PALP provides**: Backward design, retry flow, scenario nghề nghiệp

### Giảng viên studio
- **Pain**: Quá tải và ít dữ liệu thời gian thực
- **Need**: Dashboard dễ hiểu, nhóm rủi ro rõ, action nhanh
- **PALP provides**: Early warning dashboard, action log, dismiss/override

### BGH / Phòng ĐT
- **Pain**: Cần pilot an toàn, đo được, không đội chi phí
- **Need**: Báo cáo KPI, decision gate, minh bạch dữ liệu
- **PALP provides**: Governance timeline, RACI, báo cáo tuần 4/10/16

## 4. Design Principles

1. **Learning before Gamification** - game hóa chỉ tồn tại nếu giúp học tốt hơn
2. **Human-in-the-loop** - GV luôn có quyền dismiss, override
3. **Explainable interventions** - mỗi cảnh báo phải giải thích được logic
4. **Privacy by design** - thu thập tối thiểu, pseudonymization, phân quyền
5. **MVP first, intelligence later** - rule-based + BKT trước ML nâng cao

## 5. Scope

### In-scope (MVP)
- 1 môn Sức Bền Vật Liệu, 2-3 lớp, 60-90 SV, 2-3 GV
- Assessment đầu vào
- Adaptive Pathway v1 (rule-based + BKT)
- Backward Design Dashboard (milestones + micro-tasks)
- Early Warning Dashboard
- Data cleaning tối thiểu
- Event tracking
- Digital wellbeing cơ bản
- Web responsive
- KPI reporting + decision gates

### Out-of-scope
- Cá nhân hóa đa môn / toàn trường
- LSTM, collaborative filtering, Kafka, deep learning
- Native mobile app
- Tự động chấm thiết kế
- Peer review gamified
- Authorship analysis
- Scale trước Decision Gate 3

## 6. Functional Requirements

### F1: Assessment đầu vào
- 15-20 câu, <=15 phút
- Lưu tiến độ dang dở
- Đo thời gian trả lời từng câu
- **AC**: >=90% SV hoàn thành không cần hỗ trợ

### F2: Adaptive Pathway v1
- P(mastery) < 0.60: chèn nội dung bổ trợ
- P(mastery) > 0.85: tăng độ khó
- Có guess probability
- **AC**: Response < 3s, không màn hình trắng, retry logic nhất quán

### F3: Micro-task & Milestone flow
- Đồ án chia 5-10 milestones, 3-5 micro-tasks mỗi milestone
- **AC**: 100% task hiển thị thời lượng ước tính, phản hồi tiến độ <1s

### F4: Wellbeing nudge
- Học liên tục >50 phút thì nhắc nhẹ
- **AC**: Không làm gãy flow, tỷ lệ chấp nhận được tracking

### F5: Early Warning Dashboard
- Tự động cập nhật theo lô
- Nhóm Xanh/Vàng/Đỏ
- Trigger: inactivity, retry failure, tiến độ milestone
- **AC**: Load <3s, GV đánh giá "dễ hiểu" trong UAT

### F6: Intervention action log
- 3 action nhanh: gửi tin, gợi ý task, đặt lịch
- Mọi action được ghi log
- **AC**: Action tạo event và hiển thị trạng thái follow-up

### F7: Data cleaning pipeline
- Phân loại missing data
- KNN imputation cho MAR
- Z-score/IQR cho outlier screening
- **AC**: Chạy end-to-end, data quality score >=70%

### F8: Pilot analytics & reporting
- Tổng hợp KPI, usage, CSAT, adoption, lessons learned
- **AC**: Có báo cáo tuần 4/10/16, số liệu đối chiếu được

## 7. Non-Functional Requirements

| Hạng mục | Target |
|----------|--------|
| Performance | Page load <3s, adaptive response <3s |
| Availability | >=99.5% trong giờ học |
| Security | PII encrypted AES-256, RBAC 3 roles, HTTPS |
| Scalability | 200 concurrent users |
| Testing | Unit + integration cho luồng chính, UAT 20-30 SV |

## 8. KPI Framework

| KPI | Baseline | Target | Owner |
|-----|----------|--------|-------|
| Active learning time/week | 2 tuần đầu | +20% | PO |
| Micro-task completion | 0% | >=70% | Tech Lead |
| CSAT | N/A | >=4.0/5 | PO |
| GV dashboard usage | 0 | >=2x/week | UX/PO |
| Time to detect struggling students | Cuối kỳ | -50% | PO + GV |

## 9. Decision Gates

- **Gate 1 (W4)**: Baseline data collected, assessment stable
- **Gate 2 (W10)**: Pilot results, KPI evaluation
- **Gate 3 (W16)**: Go/no-go for Phase 2 expansion
