import { AlertTriangle, AlertCircle, CheckCircle2, type LucideIcon } from "lucide-react";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || "PALP";

export const DIFFICULTY_LABELS: Record<number, string> = {
  1: "Dễ",
  2: "Trung bình",
  3: "Khó",
};

interface SeverityInfo {
  label: string;
  color: string;
  dot: string;
  icon: LucideIcon;
  description: string;
}

export const SEVERITY_CONFIG: Record<string, SeverityInfo> = {
  green: {
    label: "Ổn định",
    color: "bg-green-100 text-green-800",
    dot: "bg-green-500",
    icon: CheckCircle2,
    description: "Sinh viên đang tiến triển tốt, không cần can thiệp",
  },
  yellow: {
    label: "Cần theo dõi",
    color: "bg-yellow-100 text-yellow-800",
    dot: "bg-yellow-500",
    icon: AlertCircle,
    description: "Có dấu hiệu cần chú ý, nên theo dõi thêm",
  },
  red: {
    label: "Cần can thiệp",
    color: "bg-red-100 text-red-800",
    dot: "bg-red-500",
    icon: AlertTriangle,
    description: "Cần hành động ngay để hỗ trợ sinh viên",
  },
};

export const TRIGGER_LABELS: Record<string, string> = {
  inactivity: "Không hoạt động",
  retry_failure: "Gặp khó khăn nhiều lần",
  milestone_lag: "Cần thêm thời gian",
  low_mastery: "Cần bổ sung kiến thức",
};

export const ACTION_LABELS: Record<string, string> = {
  send_message: "Gửi tin nhắn",
  suggest_task: "Gợi ý bài tập",
  schedule_meeting: "Đặt lịch gặp",
};

export const MASTERY_LABELS: Record<string, string> = {
  high: "Đã nắm vững",
  medium: "Đang tiến bộ",
  low: "Cần bổ sung",
};

export function getMasteryLabel(p: number): string {
  if (p >= 0.85) return MASTERY_LABELS.high;
  if (p >= 0.6) return MASTERY_LABELS.medium;
  return MASTERY_LABELS.low;
}
