"use client";

import { useEffect, useMemo, useState } from "react";
import { Heart, Coffee, Droplet, Activity, Clock, Check, X, RefreshCcw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState } from "@/components/shared/error-state";
import { CardSkeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";
import { useApiCall } from "@/hooks/use-api-call";
import type { WellbeingNudge } from "@/types";
import { SpacedRepPanel } from "@/components/phase6/spaced-rep-panel";
import type {
  ReviewItem,
  ReviewItemsResponse,
  ReviewLogResponse,
} from "@/components/phase6/types";

const NUDGE_META: Record<
  WellbeingNudge["nudge_type"],
  { icon: typeof Coffee; label: string; description: string }
> = {
  break_reminder: {
    icon: Coffee,
    label: "Nhắc nghỉ giải lao",
    description: "Hệ thống phát hiện bạn đã học liên tục một thời gian dài.",
  },
  stretch: {
    icon: Activity,
    label: "Nhắc vận động",
    description: "Đứng dậy, vươn vai và đi lại một chút sẽ giúp não tỉnh táo hơn.",
  },
  hydrate: {
    icon: Droplet,
    label: "Nhắc uống nước",
    description: "Uống nước đều đặn giúp duy trì sự tập trung và sức khỏe lâu dài.",
  },
};

const RESPONSE_BADGE: Record<
  WellbeingNudge["response"],
  { variant: "default" | "secondary" | "success" | "warning" | "destructive"; label: string }
> = {
  shown: { variant: "secondary", label: "Đang chờ" },
  accepted: { variant: "success", label: "Đã nghỉ" },
  dismissed: { variant: "warning", label: "Đã bỏ qua" },
};

export default function WellbeingPage() {
  const { status, data, error, run, setData } = useApiCall<WellbeingNudge[]>({
    errorTitle: "Không thể tải lịch sử",
    treat404AsEmpty: true,
  });
  const [respondingId, setRespondingId] = useState<number | null>(null);
  const [dueItems, setDueItems] = useState<ReviewItem[]>([]);
  const [upcomingItems, setUpcomingItems] = useState<ReviewItem[]>([]);
  const [spacedRepLoading, setSpacedRepLoading] = useState(true);
  const [spacedRepBusy, setSpacedRepBusy] = useState(false);

  const load = () => run(() => api.get<WellbeingNudge[]>("/wellbeing/my/"));

  const loadSpacedRep = async () => {
    setSpacedRepLoading(true);
    try {
      const [dueResp, upcomingResp] = await Promise.all([
        api.get<ReviewItemsResponse>("/spacedrep/due/"),
        api.get<ReviewItemsResponse>("/spacedrep/upcoming/"),
      ]);
      setDueItems(dueResp.items);
      setUpcomingItems(upcomingResp.items);
    } catch {
      setDueItems([]);
      setUpcomingItems([]);
    } finally {
      setSpacedRepLoading(false);
    }
  };

  const rateItem = async (conceptId: number, rating: 1 | 2 | 3 | 4) => {
    setSpacedRepBusy(true);
    try {
      await api.post<ReviewLogResponse>("/spacedrep/review/", {
        concept_id: conceptId,
        rating,
      });
      await loadSpacedRep();
    } catch {
      // ignore — leave state as is
    } finally {
      setSpacedRepBusy(false);
    }
  };

  useEffect(() => {
    load();
    loadSpacedRep();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const nudges = useMemo(() => data ?? [], [data]);

  const stats = useMemo(() => {
    const total = nudges.length;
    const accepted = nudges.filter((n) => n.response === "accepted").length;
    const dismissed = nudges.filter((n) => n.response === "dismissed").length;
    const pending = nudges.filter((n) => n.response === "shown").length;
    const acceptanceRate = total > 0 ? Math.round((accepted / total) * 100) : 0;
    return { total, accepted, dismissed, pending, acceptanceRate };
  }, [nudges]);

  const respond = async (nudge: WellbeingNudge, response: "accepted" | "dismissed") => {
    setRespondingId(nudge.id);
    try {
      const updated = await api.post<WellbeingNudge>(
        `/wellbeing/nudge/${nudge.id}/respond/`,
        { response },
      );
      setData(nudges.map((n) => (n.id === nudge.id ? updated : n)));
      toast({
        variant: response === "accepted" ? "success" : "info",
        title: response === "accepted" ? "Đã ghi nhận nghỉ ngơi" : "Đã ghi nhận bỏ qua",
        description: response === "accepted"
          ? "Chúc bạn nạp lại năng lượng tốt!"
          : "Hãy nhớ nghỉ giải lao khi cần nhé.",
      });
    } catch (err) {
      toast({
        variant: "error",
        title: "Không thể cập nhật",
        description: err instanceof ApiError ? err.detail : "Vui lòng thử lại sau.",
      });
    } finally {
      setRespondingId(null);
    }
  };

  if (status === "error" && !data) {
    return (
      <div>
        <PageHeader title="Sức khỏe học tập" />
        <ErrorState
          title="Không thể tải lịch sử nhắc nhở"
          message={error?.detail ?? "Vui lòng kiểm tra kết nối và thử lại."}
          onRetry={load}
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Sức khỏe học tập"
        description="Theo dõi nhịp học, các lời nhắc giải lao và chăm sóc bản thân"
      >
        <Button variant="outline" size="sm" onClick={load} disabled={status === "loading"}>
          <RefreshCcw className="mr-2 h-4 w-4" aria-hidden="true" />
          Làm mới
        </Button>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <SummaryCard
          icon={Heart}
          tone="info"
          label="Tổng lời nhắc"
          value={stats.total}
          hint="Trong 20 lượt gần nhất"
        />
        <SummaryCard
          icon={Check}
          tone="success"
          label="Đã chấp nhận nghỉ"
          value={stats.accepted}
          hint={`${stats.acceptanceRate}% lượt nhắc`}
        />
        <SummaryCard
          icon={X}
          tone="warning"
          label="Đã bỏ qua"
          value={stats.dismissed}
          hint="Cân nhắc nghỉ thật khi mệt"
        />
        <SummaryCard
          icon={Clock}
          tone="muted"
          label="Đang chờ phản hồi"
          value={stats.pending}
          hint="Hãy phản hồi để cải thiện cá nhân hóa"
        />
      </div>

      <Card className="mb-6 bg-info/5 border-info/30">
        <CardContent className="flex items-start gap-4 py-4">
          <Coffee className="h-5 w-5 text-info mt-1 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">Nhắc bạn nhỏ về thói quen học tập</p>
            <p className="text-sm text-muted-foreground mt-1">
              PALP nhẹ nhàng nhắc bạn nghỉ ngơi sau mỗi 50 phút học liên tục. Phản hồi
              của bạn sẽ giúp hệ thống điều chỉnh nhịp nhắc phù hợp hơn theo thời gian.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Lịch sử nhắc nhở</CardTitle>
          <CardDescription>20 lời nhắc gần đây nhất</CardDescription>
        </CardHeader>
        <CardContent>
          {status === "loading" && nudges.length === 0 ? (
            <div className="space-y-3">
              <CardSkeleton lines={2} />
              <CardSkeleton lines={2} />
            </div>
          ) : nudges.length > 0 ? (
            <ul className="space-y-3" aria-label="Danh sách lời nhắc sức khỏe">
              {nudges.map((nudge) => {
                const meta = NUDGE_META[nudge.nudge_type] ?? NUDGE_META.break_reminder;
                const Icon = meta.icon;
                const badge = RESPONSE_BADGE[nudge.response];
                const isPending = nudge.response === "shown";
                const responding = respondingId === nudge.id;

                return (
                  <li
                    key={nudge.id}
                    className="rounded-lg border border-border bg-card p-4"
                  >
                    <div className="flex flex-wrap items-start gap-4">
                      <div className="rounded-full bg-info/10 p-3" aria-hidden="true">
                        <Icon className="h-5 w-5 text-info" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <span className="font-medium">{meta.label}</span>
                          <Badge variant={badge.variant}>{badge.label}</Badge>
                          <span className="text-xs text-muted-foreground">
                            sau {nudge.continuous_minutes} phút học
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">{meta.description}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatDate(nudge.created_at)}
                          {nudge.responded_at && (
                            <> · phản hồi {formatDate(nudge.responded_at)}</>
                          )}
                        </p>

                        {isPending && (
                          <div className="flex flex-wrap gap-2 mt-3">
                            <Button
                              size="sm"
                              variant="default"
                              onClick={() => respond(nudge, "accepted")}
                              disabled={responding}
                            >
                              <Check className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                              Mình sẽ nghỉ ngay
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => respond(nudge, "dismissed")}
                              disabled={responding}
                            >
                              <X className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                              Bỏ qua lần này
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="text-center py-12">
              <Heart className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" aria-hidden="true" />
              <p className="font-medium text-lg mb-1">Chưa có lời nhắc nào</p>
              <p className="text-sm text-muted-foreground">
                Khi bạn học liên tục lâu, PALP sẽ gửi lời nhắc giải lao tại đây.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <section
        aria-label="Bài ôn theo lịch FSRS"
        className="mt-6"
      >
        <SpacedRepPanel
          due={dueItems}
          upcoming={upcomingItems}
          loading={spacedRepLoading}
          busy={spacedRepBusy}
          onRate={rateItem}
        />
      </section>
    </div>
  );
}

interface SummaryCardProps {
  icon: typeof Coffee;
  tone: "info" | "success" | "warning" | "muted";
  label: string;
  value: number;
  hint: string;
}

function SummaryCard({ icon: Icon, tone, label, value, hint }: SummaryCardProps) {
  const toneClasses = {
    info: "bg-info/10 border-info/30 text-info",
    success: "bg-success/10 border-success/30 text-success",
    warning: "bg-warning/10 border-warning/30 text-warning",
    muted: "bg-muted border-border text-muted-foreground",
  } as const;

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-2">
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <span className={`rounded-lg border p-2 ${toneClasses[tone]}`} aria-hidden="true">
            <Icon className="h-4 w-4" />
          </span>
        </div>
        <p className="text-3xl font-bold">{value}</p>
        <p className="text-xs text-muted-foreground mt-1">{hint}</p>
      </CardContent>
    </Card>
  );
}
