"use client";

import { useEffect, useState } from "react";
import { History, MessageSquare, BookOpen, Calendar, CheckCircle2, Clock, XCircle, ClipboardList } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState } from "@/components/shared/error-state";
import { AlertCardSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { ACTION_LABELS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";
import type { InterventionAction } from "@/types";
import Link from "next/link";

const STATUS_CONFIG = {
  pending: { label: "Chờ phản hồi", variant: "warning" as const, icon: Clock },
  student_responded: { label: "SV đã phản hồi", variant: "success" as const, icon: CheckCircle2 },
  resolved: { label: "Đã xử lý", variant: "success" as const, icon: CheckCircle2 },
  no_response: { label: "Chưa phản hồi", variant: "secondary" as const, icon: XCircle },
};

const ACTION_ICONS = {
  send_message: MessageSquare,
  suggest_task: BookOpen,
  schedule_meeting: Calendar,
};

export default function InterventionHistoryPage() {
  const [actions, setActions] = useState<InterventionAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  async function load() {
    setLoading(true);
    setError(false);
    try {
      const data = await api.get<any>("/dashboard/interventions/history/");
      const list = Array.isArray(data) ? data : data.results || [];
      setActions(list);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const updateStatus = async (actionId: number, newStatus: string) => {
    try {
      await api.patch(`/dashboard/interventions/${actionId}/follow-up/`, {
        follow_up_status: newStatus,
      });
      setActions((prev) =>
        prev.map((a) => (a.id === actionId ? { ...a, follow_up_status: newStatus } : a))
      );
      const statusLabels: Record<string, string> = {
        student_responded: "Đã ghi nhận phản hồi",
        resolved: "Đã đánh dấu xử lý xong",
        no_response: "Đã ghi nhận chưa phản hồi",
      };
      toast({ variant: "success", title: statusLabels[newStatus] || "Đã cập nhật" });
    } catch {
      toast({ variant: "error", title: "Không thể cập nhật", description: "Vui lòng thử lại." });
    }
  };

  if (error) {
    return (
      <div>
        <PageHeader title="Lịch sử can thiệp" />
        <ErrorState
          title="Không thể tải lịch sử"
          message="Vui lòng kiểm tra kết nối mạng và thử lại."
          onRetry={load}
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Lịch sử can thiệp"
        description="Theo dõi kết quả các hành động can thiệp"
      />

      <div className="space-y-4">
        {loading ? (
          <>
            <AlertCardSkeleton />
            <AlertCardSkeleton />
            <AlertCardSkeleton />
          </>
        ) : actions.length > 0 ? (
          actions.map((action) => {
            const statusConfig = STATUS_CONFIG[action.follow_up_status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.pending;
            const ActionIcon = ACTION_ICONS[action.action_type as keyof typeof ACTION_ICONS] || MessageSquare;
            const StatusIcon = statusConfig.icon;

            return (
              <Card key={action.id}>
                <CardContent className="pt-6">
                  <div className="flex items-start gap-4">
                    <div className="rounded-lg bg-primary/10 p-2.5" aria-hidden="true">
                      <ActionIcon className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className="font-medium">
                          {ACTION_LABELS[action.action_type] || action.action_type}
                        </span>
                        <Badge variant={statusConfig.variant}>
                          <StatusIcon className="mr-1 h-3 w-3" aria-hidden="true" />
                          {statusConfig.label}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        bởi {action.lecturer_name} — {formatDate(action.created_at)}
                      </p>
                      {action.message && (
                        <p className="mt-2 text-sm bg-muted rounded-md p-3">{action.message}</p>
                      )}

                      {action.follow_up_status === "pending" && (
                        <div className="flex flex-wrap gap-2 mt-3">
                          <Button
                            size="sm" variant="success"
                            onClick={() => updateStatus(action.id, "student_responded")}
                          >
                            SV đã phản hồi
                          </Button>
                          <Button
                            size="sm" variant="outline"
                            onClick={() => updateStatus(action.id, "resolved")}
                          >
                            Đã xử lý
                          </Button>
                          <Button
                            size="sm" variant="ghost"
                            onClick={() => updateStatus(action.id, "no_response")}
                          >
                            Chưa phản hồi
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <ClipboardList className="mx-auto h-12 w-12 text-muted-foreground/30 mb-4" aria-hidden="true" />
              <p className="font-medium text-lg mb-2">Chưa có lịch sử can thiệp</p>
              <p className="text-sm text-muted-foreground mb-6">
                Lịch sử sẽ xuất hiện sau khi bạn thực hiện hành động can thiệp từ trang Cảnh báo.
              </p>
              <Link href="/alerts">
                <Button variant="outline">Xem cảnh báo</Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
