"use client";

import { Activity, AlertTriangle, CheckCircle2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

import type { NorthStarPayload } from "./types";

interface Props {
  data: NorthStarPayload["performance"] | null;
}

const DRIFT_THRESHOLD = 0.4; // mirrors PALP_GOALS["DRIFT_THRESHOLD_PCT"]

export function PerformancePanel({ data }: Props) {
  const wg = data?.weekly_goal ?? null;
  const drift = data?.drift_pct_last_check ?? null;
  const driftPct = drift !== null ? Math.round(drift * 100) : null;
  const targetMin = wg?.target_minutes ?? 0;
  const actualMin =
    wg && drift !== null ? Math.max(0, Math.round(targetMin * (1 - drift))) : null;
  const progressPct =
    targetMin > 0 && actualMin !== null
      ? Math.min(100, (actualMin / targetMin) * 100)
      : 0;

  const lastCheckedLabel = wg?.drift_last_checked_at
    ? new Date(wg.drift_last_checked_at).toLocaleString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
        day: "2-digit",
        month: "2-digit",
      })
    : null;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <CardTitle className="text-base">Hiệu suất (Performance)</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          So sánh thực tế với cam kết tuần
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {wg ? (
          <>
            <section>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="text-muted-foreground">Tập trung tuần này</span>
                <span className="font-medium tabular-nums">
                  {actualMin ?? "—"} / {targetMin} phút
                </span>
              </div>
              <Progress
                value={progressPct}
                aria-label={`Tập trung: ${actualMin ?? 0} trên ${targetMin} phút`}
              />
              {lastCheckedLabel ? (
                <p className="text-[11px] text-muted-foreground mt-1.5">
                  Cập nhật lúc {lastCheckedLabel}
                </p>
              ) : null}
            </section>

            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Trạng thái
              </h3>
              {drift === null ? (
                <p className="text-sm text-muted-foreground mt-1.5">
                  Chưa đủ dữ liệu signals tuần này. Học vài buổi để hệ thống đo được.
                </p>
              ) : driftPct !== null && drift >= DRIFT_THRESHOLD ? (
                <div className="mt-2 flex items-start gap-2 rounded-md border border-yellow-500/30 bg-yellow-500/10 p-3 text-sm">
                  <AlertTriangle
                    className="h-4 w-4 mt-0.5 text-yellow-600 dark:text-yellow-400 shrink-0"
                    aria-hidden="true"
                  />
                  <div>
                    <p>
                      Bạn đang chậm{" "}
                      <span className="font-medium tabular-nums">{driftPct}%</span> so
                      với cam kết tuần.
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Đây là quan sát, không phải đánh giá. Bạn có thể điều chỉnh mục
                      tiêu nếu thấy không thực tế.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="mt-2 flex items-start gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm">
                  <CheckCircle2
                    className="h-4 w-4 mt-0.5 text-emerald-600 dark:text-emerald-400 shrink-0"
                    aria-hidden="true"
                  />
                  <p>Bạn đang đi đúng kế hoạch. Giữ nhịp.</p>
                </div>
              )}
            </section>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            Chưa có mục tiêu tuần để theo dõi. Đặt mục tiêu trước, sau đó signals sẽ
            đối chiếu.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
