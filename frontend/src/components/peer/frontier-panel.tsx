"use client";

import { LineChart, Sparkles, TrendingUp } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

import type { FrontierSnapshot } from "./types";

interface Props {
  data: FrontierSnapshot | null;
  loading: boolean;
}

function pct(value: number): number {
  return Math.round(value * 100);
}

function colorForDelta(deltaPct: number) {
  if (deltaPct >= 5) return "text-emerald-600 dark:text-emerald-400";
  if (deltaPct <= -5) return "text-amber-600 dark:text-amber-400";
  return "text-muted-foreground";
}

export function FrontierPanel({ data, loading }: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <LineChart
            className="h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <CardTitle className="text-base">
            Bạn so với chính bạn (Frontier)
          </CardTitle>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          So sánh với chính bạn {data ? `${data.lookback_days} ngày trước` : "trước đây"}{" "}
          — không có ai khác trong dữ liệu này
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        {loading ? (
          <p className="text-sm text-muted-foreground" role="status">
            Đang tính toán…
          </p>
        ) : !data || data.current_avg_mastery === 0 ? (
          <p className="text-sm text-muted-foreground">
            Chưa có dữ liệu mastery. Học vài bài tập để hệ thống vẽ được biểu
            đồ tiến bộ riêng cho bạn.
          </p>
        ) : (
          <>
            <section aria-labelledby="frontier-current">
              <div className="flex items-baseline justify-between gap-2">
                <span
                  id="frontier-current"
                  className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                >
                  Mastery trung bình hiện tại
                </span>
                <span className="text-sm font-medium tabular-nums">
                  {pct(data.current_avg_mastery)}%
                </span>
              </div>
              <Progress
                value={pct(data.current_avg_mastery)}
                className="mt-2"
                aria-label={`Mastery hiện tại ${pct(data.current_avg_mastery)} phần trăm`}
              />
              <p
                className={`text-xs mt-1.5 ${colorForDelta(data.delta_pct)}`}
              >
                <TrendingUp
                  className="inline h-3 w-3 mr-1 align-[-1px]"
                  aria-hidden="true"
                />
                {data.delta >= 0 ? "+" : ""}
                {(data.delta * 100).toFixed(1)}đ so với {data.lookback_days} ngày
                trước ({data.delta_pct >= 0 ? "+" : ""}
                {data.delta_pct.toFixed(0)}%)
              </p>
            </section>

            {data.concepts_progressed.length > 0 ? (
              <section aria-labelledby="frontier-progress">
                <div className="flex items-center gap-1.5">
                  <Sparkles
                    className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400"
                    aria-hidden="true"
                  />
                  <h3
                    id="frontier-progress"
                    className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                  >
                    Bạn đã tiến bộ ở
                  </h3>
                </div>
                <ul className="mt-2 space-y-2">
                  {data.concepts_progressed.slice(0, 4).map((c) => (
                    <li
                      key={c.concept_id}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="truncate pr-2">{c.name}</span>
                      <span className="tabular-nums text-emerald-600 dark:text-emerald-400 shrink-0">
                        {pct(c.from)}% → {pct(c.to)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {data.concepts_regressed.length > 0 ? (
              <section aria-labelledby="frontier-regressed">
                <h3
                  id="frontier-regressed"
                  className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                >
                  Cần ôn lại
                </h3>
                <ul className="mt-2 space-y-2">
                  {data.concepts_regressed.slice(0, 3).map((c) => (
                    <li
                      key={c.concept_id}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="truncate pr-2">{c.name}</span>
                      <span className="tabular-nums text-amber-600 dark:text-amber-400 shrink-0">
                        {pct(c.from)}% → {pct(c.to)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
