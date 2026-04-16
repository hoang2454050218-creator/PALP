CONSENT_VERSION = "1.0"

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
