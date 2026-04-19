"use client";

import { Brain, TrendingDown, TrendingUp } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

import type { DKTPrediction } from "./types";

interface Props {
  predictions: DKTPrediction[];
  loading: boolean;
}

function pct(value: number): number {
  return Math.round(value * 100);
}

function colorFor(p: number): string {
  if (p >= 0.7) return "text-emerald-700 dark:text-emerald-300";
  if (p >= 0.4) return "text-amber-700 dark:text-amber-300";
  return "text-red-700 dark:text-red-300";
}

export function DKTPanel({ predictions, loading }: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Brain
            className="h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <CardTitle className="text-base">Dự đoán DKT</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Mô hình SAKT-style ước lượng xác suất bạn làm đúng tiếp theo cho
          mỗi concept — sắp xếp theo concept yếu nhất
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <p className="text-sm text-muted-foreground" role="status">
            Đang tính toán…
          </p>
        ) : predictions.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Chưa có dữ liệu attempt — làm vài bài để DKT có lịch sử dự đoán.
          </p>
        ) : (
          <ul className="space-y-3" aria-label="Danh sách dự đoán DKT">
            {predictions.slice(0, 5).map((p) => {
              const probabilityPct = pct(p.p_correct_next);
              const trending =
                p.p_correct_next >= 0.5 ? (
                  <TrendingUp
                    className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400"
                    aria-hidden="true"
                  />
                ) : (
                  <TrendingDown
                    className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400"
                    aria-hidden="true"
                  />
                );
              return (
                <li
                  key={p.id}
                  className="rounded-md border bg-card/50 p-3 space-y-2"
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-sm font-medium truncate">
                      {p.concept_name}
                    </span>
                    <span
                      className={`text-sm font-medium tabular-nums ${colorFor(p.p_correct_next)}`}
                    >
                      {probabilityPct}%
                    </span>
                  </div>
                  <Progress
                    value={probabilityPct}
                    aria-label={`Xác suất làm đúng: ${probabilityPct}%`}
                  />
                  <p className="text-[11px] text-muted-foreground inline-flex items-center gap-1.5">
                    {trending}
                    {p.sequence_length} attempts trong lịch sử · model{" "}
                    {p.model_family}@{p.model_semver}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
