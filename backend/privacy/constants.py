# Consent contract version. Bump when the set of CONSENT_PURPOSES or
# their semantic scope changes — ConsentGateMiddleware compares this
# against the most recent ConsentRecord.version to trigger a re-consent
# flow on the frontend.
#
# Version history:
#   1.0 — initial taxonomy (academic, behavioral, inference)
#   1.1 — v3 roadmap Phase 1: behavioral_signals + cognitive_calibration
#   1.2 — v3 roadmap Phase 3: peer_comparison + peer_teaching
#   1.3 — v3 roadmap Phase 4: ai_coach_local + ai_coach_cloud + emergency_contact
#   1.4 — v3 roadmap Phase 5: agentic_memory
#   1.5 — v3 roadmap Phase 6: xai_telemetry + dp_aggregate_analytics
#   1.6 — v3 roadmap Phase 7: research_participation + affect_signals
CONSENT_VERSION = "1.6"

CONSENT_PURPOSES = {
    "academic": {
        "label": "Dữ liệu học vụ lịch sử",
        "description": (
            "Thu thập và lưu trữ kết quả assessment, điểm số, "
            "hồ sơ người học và đăng ký môn học."
        ),
    },
    "behavioral": {
        "label": "Dữ liệu hành vi học tập",
        "description": (
            "Theo dõi phiên học, thời gian làm bài, số lần thử, "
            "và tương tác với nội dung học tập."
        ),
    },
    "inference": {
        "label": "Dữ liệu suy luận",
        "description": (
            "Hệ thống ước tính mức mastery, phát hiện rủi ro, "
            "và đề xuất nội dung phù hợp dựa trên dữ liệu học tập."
        ),
    },
    # v3 roadmap — Phase 1
    "behavioral_signals": {
        "label": "Tín hiệu hành vi chi tiết (focus / idle / tab)",
        "description": (
            "Thu thập tín hiệu chi tiết về độ tập trung, thời gian nhàn "
            "rỗi, đổi tab, và các pattern thất vọng/bỏ cuộc để hệ thống "
            "phát hiện sớm khi bạn đang vật lộn. Bạn có thể tắt bất cứ "
            "lúc nào — hệ thống sẽ vẫn hoạt động nhưng kém tinh tế hơn."
        ),
        "default": False,
    },
    "cognitive_calibration": {
        "label": "Tự đánh giá độ tự tin (metacognitive)",
        "description": (
            "Trước khi nộp bài, bạn được hỏi mức độ tự tin (1-5). Hệ "
            "thống so sánh độ tự tin với kết quả thực tế để giúp bạn "
            "nhận ra over/under-confidence pattern qua thời gian."
        ),
        "default": False,
    },
    # v3 roadmap — Phase 3 (Peer Engine, anti-herd)
    "peer_comparison": {
        "label": "So sánh ẩn danh trong cohort cùng năng lực",
        "description": (
            "Hiển thị vị trí tương đối của bạn (ẩn danh, theo nhóm) so với "
            "các bạn cùng xuất phát điểm. Không có bảng xếp hạng, không hiện "
            "tên ai. Bạn có thể tắt bất cứ lúc nào — mặc định là TẮT."
        ),
        "default": False,
    },
    "peer_teaching": {
        "label": "Ghép cặp dạy nhau (reciprocal teaching)",
        "description": (
            "Cho phép hệ thống ghép bạn với 1 bạn khác để dạy nhau những "
            "concept hai bên mạnh-yếu chéo. Mỗi phiên ~60 phút, bạn có thể "
            "huỷ trước khi phiên bắt đầu. Mặc định là TẮT."
        ),
        "default": False,
    },
    # v3 roadmap — Phase 4 (AI Coach + Emergency Pipeline)
    "ai_coach_local": {
        "label": "Trợ lý AI nội bộ (Local LLM)",
        "description": (
            "Cho phép trò chuyện với coach AI chạy trên máy chủ nội bộ. "
            "Dữ liệu PII không bao giờ rời hệ thống. Mặc định BẬT — bạn có "
            "thể tắt ở mục Quyền riêng tư bất cứ lúc nào."
        ),
        "default": True,
    },
    "ai_coach_cloud": {
        "label": "Trợ lý AI bên ngoài (Cloud LLM)",
        "description": (
            "Cho phép coach gọi mô hình ngôn ngữ trên đám mây (Anthropic / "
            "OpenAI) cho câu hỏi không nhạy cảm. Tin nhắn được mã hoá PII "
            "trước khi gửi đi. Mặc định TẮT."
        ),
        "default": False,
    },
    "emergency_contact": {
        "label": "Liên hệ khẩn cấp",
        "description": (
            "Cho phép hệ thống liên hệ với người liên hệ khẩn cấp của bạn "
            "khi phát hiện rủi ro nghiêm trọng (ví dụ ý định tự tổn thương) "
            "và counselor không phản hồi trong 15 phút. Mặc định TẮT."
        ),
        "default": False,
    },
    # v3 roadmap — Phase 5 (Agentic memory)
    "agentic_memory": {
        "label": "Trí nhớ cá nhân hoá của coach",
        "description": (
            "Cho phép coach ghi nhớ ngữ cảnh học tập của bạn (mục tiêu, "
            "concept đã học, chiến lược nào hiệu quả) để hỗ trợ tốt hơn "
            "qua thời gian. Bạn có thể xem chi tiết hoặc xoá toàn bộ "
            "trí nhớ bất cứ lúc nào trong trang Coach. Mặc định TẮT."
        ),
        "default": False,
    },
    # v3 roadmap — Phase 6 (XAI + Differential Privacy)
    "xai_telemetry": {
        "label": "Đóng góp dữ liệu giải thích cho hệ thống",
        "description": (
            "Cho phép hệ thống ghi nhận bạn xem giải thích nào, click vào "
            "counterfactual nào — để cải thiện chất lượng giải thích cho "
            "tất cả sinh viên. Không lưu nội dung tin nhắn / câu trả lời. "
            "Mặc định TẮT."
        ),
        "default": False,
    },
    "dp_aggregate_analytics": {
        "label": "Cho phép phân tích tổng hợp đã thêm nhiễu (DP)",
        "description": (
            "Cho phép thống kê toàn lớp / toàn trường có dữ liệu của bạn ở "
            "dạng tổng hợp đã thêm nhiễu Laplace (ε-DP). Ngân sách ε được "
            "kiểm soát chặt — không thể truy xuất ngược cá nhân. Mặc định BẬT."
        ),
        "default": True,
    },
    # v3 roadmap — Phase 7 (Academic layer)
    "research_participation": {
        "label": "Tham gia nghiên cứu khoa học (đã ẩn danh)",
        "description": (
            "Cho phép dữ liệu học tập của bạn được sử dụng trong các nghiên "
            "cứu khoa học theo từng đề cương được hội đồng đạo đức (IRB) "
            "phê duyệt. Mọi dữ liệu xuất ra đều được ẩn danh, kiểm tra "
            "k-anonymity và bạn có thể RÚT bất cứ lúc nào — dữ liệu của bạn "
            "sẽ bị loại khỏi các bản xuất tiếp theo. Mặc định TẮT."
        ),
        "default": False,
    },
    "affect_signals": {
        "label": "Tín hiệu cảm xúc đa phương thức",
        "description": (
            "Cho phép hệ thống phân tích nhịp gõ phím (chỉ thống kê tổng "
            "hợp, không lưu nội dung gõ) và sắc thái cảm xúc trong các đoạn "
            "phản hồi bạn nhập, để phát hiện sớm sự bực bội hoặc mệt mỏi. "
            "Không sử dụng camera. Mặc định TẮT."
        ),
        "default": False,
    },
}

DATA_TIERS = {
    "pii": {
        "label": "Thông tin cá nhân (PII)",
        "sensitivity": "high",
        "retention_months": None,
        "delete_policy": "anonymize",
        "models": {
            "accounts.User": [
                "first_name", "last_name", "email",
                "student_id", "phone", "avatar_url",
            ],
        },
    },
    "academic": {
        "label": "Dữ liệu học vụ",
        "sensitivity": "high",
        "retention_months": 36,
        "delete_policy": "anonymize",
        "consent_purpose": "academic",
        "models": {
            "assessment.AssessmentSession": "__all__",
            "assessment.AssessmentResponse": "__all__",
            "assessment.LearnerProfile": "__all__",
            "curriculum.Enrollment": "__all__",
        },
    },
    "behavioral": {
        "label": "Dữ liệu hành vi",
        "sensitivity": "low",
        "retention_months": 12,
        "delete_policy": "hard_delete",
        "consent_purpose": "behavioral",
        "models": {
            "adaptive.TaskAttempt": "__all__",
            "events.EventLog": "__all__",
            "wellbeing.WellbeingNudge": "__all__",
        },
    },
    # Phase 1B/1E — high-resolution behavioural signals stored per-session
    # rollup. Shorter retention (3 months raw rollup) because the value is
    # in real-time adaptation, not long-term archives. Aggregated risk
    # snapshots stay on the longer ``inference`` tier below.
    "behavioral_signals": {
        "label": "Tín hiệu hành vi chi tiết",
        "sensitivity": "medium",
        "retention_months": 3,
        "delete_policy": "hard_delete",
        "consent_purpose": "behavioral_signals",
        "models": {
            "signals.SignalSession": "__all__",
            "signals.BehaviorScore": "__all__",
            "adaptive.MetacognitiveJudgment": "__all__",
        },
    },
    "inference": {
        "label": "Dữ liệu suy luận",
        "sensitivity": "medium",
        "retention_months": 12,
        "delete_policy": "hard_delete",
        "consent_purpose": "inference",
        "models": {
            "adaptive.MasteryState": "__all__",
            "adaptive.ContentIntervention": "__all__",
            "adaptive.StudentPathway": "__all__",
            "dashboard.Alert": "__all__",
        },
    },
}

LECTURER_VISIBLE_EVENTS = {
    "assessment_completed",
    "micro_task_completed",
    "session_started",
    "session_ended",
    "content_intervention",
    "retry_triggered",
}

LECTURER_MASTERY_FIELDS = (
    "id", "concept", "concept_name", "p_mastery",
    "attempt_count", "correct_count", "last_updated",
)

ALLOWED_INFERENCE_PURPOSES = {
    "mastery_estimation",
    "at_risk_detection",
    "content_recommendation",
    "difficulty_adjustment",
}

EXPORT_GLOSSARY = {
    "first_name": "Tên",
    "last_name": "Họ",
    "email": "Email",
    "student_id": "Mã sinh viên",
    "phone": "Số điện thoại",
    "role": "Vai trò",
    "consent_given": "Đã đồng ý điều khoản",
    "consent_given_at": "Thời điểm đồng ý",
    "created_at": "Ngày tạo tài khoản",
    "p_mastery": "Xác suất mastery (BKT)",
    "attempt_count": "Số lần thử",
    "correct_count": "Số lần đúng",
    "score": "Điểm",
    "max_score": "Điểm tối đa",
    "duration_seconds": "Thời gian làm bài (giây)",
    "hints_used": "Số gợi ý đã dùng",
    "is_correct": "Trả lời đúng",
    "total_score": "Tổng điểm",
    "total_time_seconds": "Tổng thời gian (giây)",
    "event_name": "Loại sự kiện",
    "properties": "Chi tiết sự kiện",
    "session_id": "Mã phiên",
    "severity": "Mức độ cảnh báo",
    "trigger_type": "Loại cảnh báo",
    "reason": "Lý do",
    "intervention_type": "Loại can thiệp",
    "nudge_type": "Loại nhắc nhở",
    "continuous_minutes": "Thời gian học liên tục (phút)",
    "current_difficulty": "Độ khó hiện tại",
    "concepts_completed": "Danh sách concept hoàn thành",
    "milestones_completed": "Danh sách milestone hoàn thành",
    "overall_score": "Điểm tổng quan",
    "strengths": "Điểm mạnh",
    "weaknesses": "Điểm yếu",
}

INCIDENT_SEVERITY_CHOICES = [
    ("low", "Thấp"),
    ("medium", "Trung bình"),
    ("high", "Cao"),
    ("critical", "Nghiêm trọng"),
]
