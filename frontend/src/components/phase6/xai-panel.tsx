"use client";

import { Lightbulb, Sparkles } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import type { RiskExplanation } from "./types";

interface Props {
  data: RiskExplanation | null;
  loading: boolean;
}

const FEATURE_LABEL: Record<string, string> = {
  academic: "Học vụ",
  behavioral: "Hành vi",
  engagement: "Tương tác",
  psychological: "Tâm lý",
  metacognitive: "Metacognitive",
};

function pct(value: number): number {
  return Math.round(value * 100);
}

export function XaiPanel({ data, loading }: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Lightbulb
            className="h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <CardTitle className="text-base">Giải thích Risk (XAI)</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          SHAP-lite + counterfactual — minh bạch tại sao composite ở mức
          hiện tại và bạn có thể thay đổi gì để giảm risk
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <p className="text-sm text-muted-foreground" role="status">
            Đang tính toán…
          </p>
        ) : !data ? (
          <p className="text-sm text-muted-foreground">
            Chưa có dữ liệu risk để giải thích — học thêm vài buổi để hệ
            thống tính được composite.
          </p>
        ) : (
          <>
            <p className="text-sm leading-relaxed">{data.summary}</p>

            {data.contributions.length > 0 ? (
              <section aria-labelledby="xai-contrib">
                <h3
                  id="xai-contrib"
                  className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                >
                  Đóng góp của từng dimension
                </h3>
                <ul className="mt-2 space-y-2">
                  {data.contributions.map((c) => {
                    const positive = c.contribution > 0;
                    const labelText =
                      FEATURE_LABEL[c.feature_key] ?? c.feature_key;
                    return (
                      <li key={c.feature_key} className="text-sm">
                        <div className="flex items-baseline justify-between gap-2">
                          <span className="truncate">{labelText}</span>
                          <span
                            className={`tabular-nums shrink-0 ${
                              positive
                                ? "text-amber-700 dark:text-amber-300"
                                : "text-emerald-700 dark:text-emerald-300"
                            }`}
                          >
                            {positive ? "+" : ""}
                            {c.contribution.toFixed(1)} đ
                          </span>
                        </div>
                        <div className="mt-1 h-1 rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-1 ${
                              positive ? "bg-amber-500" : "bg-emerald-500"
                            }`}
                            style={{
                              width: `${Math.min(100, Math.abs(c.contribution) * 1.5)}%`,
                            }}
                          />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ) : null}

            {data.counterfactuals.length > 0 ? (
              <section aria-labelledby="xai-cf">
                <div className="flex items-center gap-1.5">
                  <Sparkles
                    className="h-3.5 w-3.5 text-primary"
                    aria-hidden="true"
                  />
                  <h3
                    id="xai-cf"
                    className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                  >
                    Bạn có thể làm gì
                  </h3>
                </div>
                <ul className="mt-2 space-y-3">
                  {data.counterfactuals.slice(0, 3).map((cf) => {
                    const labelText =
                      FEATURE_LABEL[cf.feature_key] ?? cf.feature_key;
                    return (
                      <li
                        key={cf.feature_key}
                        className="rounded-md border bg-card/50 p-3 space-y-2"
                      >
                        <div className="flex items-baseline justify-between gap-2 text-sm">
                          <span className="font-medium">{labelText}</span>
                          <span className="tabular-nums text-xs text-muted-foreground">
                            khả thi {pct(cf.feasibility)}%
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {cf.actionable_hint}
                        </p>
                        <p className="text-[11px] text-muted-foreground tabular-nums">
                          Δ dimension {pct(cf.current_value)}% → {pct(cf.target_value)}%
                          {" · "}
                          composite{" "}
                          <span
                            className={
                              cf.expected_delta < 0
                                ? "text-emerald-700 dark:text-emerald-300"
                                : "text-amber-700 dark:text-amber-300"
                            }
                          >
                            {cf.expected_delta.toFixed(1)} đ
                          </span>
                        </p>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
