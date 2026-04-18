"use client";

import { useEffect, useState } from "react";
import { MessageSquare, BookOpen, Calendar, X, CheckCircle2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState } from "@/components/shared/error-state";
import { AlertCardSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { SEVERITY_CONFIG, TRIGGER_LABELS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";
import { useCourseContext, useEnsureCourseContext } from "@/hooks/use-course-context";
import type { Alert } from "@/types";

export default function AlertsPage() {
  useEnsureCourseContext("lecturer");
  const classId = useCourseContext((s) => s.classId);
  const ctxLoading = useCourseContext((s) => s.loading);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [filter, setFilter] = useState<"all" | "red" | "yellow">("all");
  const [dismissingId, setDismissingId] = useState<number | null>(null);
  const [dismissNote, setDismissNote] = useState("");

  useEffect(() => {
    loadAlerts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [classId]);

  const loadAlerts = async () => {
    setLoading(true);
    setError(false);
    try {
      const qs = classId ? `?class_id=${classId}&status=active` : "?status=active";
      const data = await api.get<Alert[] | { results: Alert[] }>(`/dashboard/alerts/${qs}`);
      const list = Array.isArray(data) ? data : data.results || [];
      setAlerts(list);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const dismissAlert = async (alertId: number) => {
    try {
      await api.post(`/dashboard/alerts/${alertId}/dismiss/`, {
        dismiss_note: dismissNote,
      });
      setDismissingId(null);
      setDismissNote("");
      loadAlerts();
      toast({ variant: "success", title: "Đã bỏ qua cảnh báo", description: "Cảnh báo đã được ghi nhận và bỏ qua." });
    } catch {
      toast({ variant: "error", title: "Không thể bỏ qua", description: "Đã xảy ra lỗi. Vui lòng thử lại." });
    }
  };

  const createIntervention = async (alert: Alert, actionType: string) => {
    try {
      await api.post("/dashboard/interventions/", {
        alert_id: alert.id,
        action_type: actionType,
        target_student_ids: [alert.student],
        message: "",
      });
      const actionLabels: Record<string, string> = {
        send_message: "Đã gửi tin nhắn",
        suggest_task: "Đã gợi ý bài tập",
        schedule_meeting: "Đã đặt lịch gặp",
      };
      toast({
        variant: "success",
        title: actionLabels[actionType] || "Đã tạo can thiệp",
        description: `Hành động cho ${alert.student_name} đã được ghi nhận.`,
      });
      loadAlerts();
    } catch {
      toast({ variant: "error", title: "Không thể tạo can thiệp", description: "Đã xảy ra lỗi. Vui lòng thử lại." });
    }
  };

  const filtered = filter === "all" ? alerts : alerts.filter((a) => a.severity === filter);

  if (error) {
    return (
      <div>
        <PageHeader title="Cảnh báo sớm" />
        <ErrorState
          title="Không thể tải cảnh báo"
          message="Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối và thử lại."
          onRetry={loadAlerts}
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Cảnh báo sớm"
        description={loading ? undefined : `${alerts.length} cảnh báo đang mở`}
      />

      <div className="flex flex-wrap gap-2 mb-6" role="group" aria-label="Lọc cảnh báo theo mức độ">
        <Button
          variant={filter === "all" ? "default" : "outline"} size="sm"
          onClick={() => setFilter("all")}
          aria-pressed={filter === "all"}
        >
          Tất cả ({alerts.length})
        </Button>
        <Button
          variant={filter === "red" ? "destructive" : "outline"} size="sm"
          onClick={() => setFilter("red")}
          aria-pressed={filter === "red"}
        >
          Cần can thiệp ({alerts.filter((a) => a.severity === "red").length})
        </Button>
        <Button
          variant={filter === "yellow" ? "warning" : "outline"} size="sm"
          onClick={() => setFilter("yellow")}
          aria-pressed={filter === "yellow"}
        >
          Cần theo dõi ({alerts.filter((a) => a.severity === "yellow").length})
        </Button>
      </div>

      <div className="space-y-4" aria-live="polite">
        {loading || ctxLoading ? (
          <>
            <AlertCardSkeleton />
            <AlertCardSkeleton />
            <AlertCardSkeleton />
          </>
        ) : filtered.length > 0 ? (
          filtered.map((alert) => {
            const config = SEVERITY_CONFIG[alert.severity];
            const SeverityIcon = config.icon;
            return (
              <Card key={alert.id} className={alert.severity === "red" ? "border-danger/40" : ""}>
                <CardContent className="pt-6">
                  <div className="flex items-start gap-4">
                    <div className="mt-0.5 shrink-0" aria-hidden="true">
                      <SeverityIcon className={`h-5 w-5 ${alert.severity === "red" ? "text-danger" : alert.severity === "yellow" ? "text-warning" : "text-success"}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className="font-semibold">{alert.student_name}</span>
                        <Badge className={config.color}>
                          {config.label}
                        </Badge>
                        <Badge variant="outline">{TRIGGER_LABELS[alert.trigger_type] || alert.trigger_type}</Badge>
                      </div>
                      <p className="text-sm mb-2">{alert.reason}</p>
                      {alert.concept_name && (
                        <p className="text-xs text-muted-foreground">Concept: {alert.concept_name}</p>
                      )}
                      {alert.suggested_action && (
                        <div className="mt-3 rounded-md bg-info/10 border border-info/30 p-3">
                          <p className="text-xs font-medium text-info-foreground">Hành động gợi ý:</p>
                          <p className="text-xs text-info-foreground/80 mt-1">{alert.suggested_action}</p>
                        </div>
                      )}

                      <div className="flex flex-wrap items-center gap-2 mt-4">
                        <Button
                          size="sm" variant="default"
                          onClick={() => createIntervention(alert, "send_message")}
                        >
                          <MessageSquare className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" /> Gửi tin
                        </Button>
                        <Button
                          size="sm" variant="secondary"
                          onClick={() => createIntervention(alert, "suggest_task")}
                        >
                          <BookOpen className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" /> Gợi ý bài
                        </Button>
                        <Button
                          size="sm" variant="secondary"
                          onClick={() => createIntervention(alert, "schedule_meeting")}
                        >
                          <Calendar className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" /> Đặt lịch
                        </Button>
                        <Button
                          size="sm" variant="ghost"
                          onClick={() => setDismissingId(alert.id)}
                        >
                          <X className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" /> Bỏ qua
                        </Button>
                      </div>

                      {dismissingId === alert.id && (
                        <div className="mt-3 flex gap-2">
                          <div className="flex-1">
                            <label htmlFor={`dismiss-note-${alert.id}`} className="sr-only">
                              Lý do bỏ qua cảnh báo
                            </label>
                            <Input
                              id={`dismiss-note-${alert.id}`}
                              placeholder="Lý do bỏ qua (tùy chọn)..."
                              value={dismissNote}
                              onChange={(e) => setDismissNote(e.target.value)}
                            />
                          </div>
                          <Button size="sm" onClick={() => dismissAlert(alert.id)}>
                            Xác nhận
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setDismissingId(null)}>
                            Hủy
                          </Button>
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0 hidden sm:block">
                      {formatDate(alert.created_at)}
                    </span>
                  </div>
                </CardContent>
              </Card>
            );
          })
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <CheckCircle2 className="mx-auto h-12 w-12 text-success/60 mb-4" aria-hidden="true" />
              <p className="font-medium text-lg mb-1">Tất cả sinh viên đang ổn định</p>
              <p className="text-sm text-muted-foreground">
                {filter !== "all"
                  ? "Không có cảnh báo nào trong bộ lọc hiện tại. Thử chọn \"Tất cả\" để xem toàn bộ."
                  : "Hiện không có cảnh báo nào cần xử lý. Hệ thống sẽ tự động tạo cảnh báo khi phát hiện sinh viên cần hỗ trợ."}
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
