"use client";

import { Network, Sparkles } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import type { RootCausePayload } from "./types";

interface Props {
  data: RootCausePayload | null;
  loading: boolean;
}

function pct(value: number): number {
  return Math.round(value * 100);
}

export function RootCausePanel({ data, loading }: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Network
            className="h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <CardTitle className="text-base">Root-cause</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Nếu bạn yếu một concept, đôi khi gốc rễ là ở prerequisite trước
          đó. KG walker tìm prerequisite yếu nhất ảnh hưởng nhiều nhất.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <p className="text-sm text-muted-foreground" role="status">
            Đang phân tích…
          </p>
        ) : !data ? (
          <p className="text-sm text-muted-foreground">
            Chọn một concept yếu trên panel DKT để xem root-cause analysis.
          </p>
        ) : (
          <>
            <div className="rounded-md border border-primary/30 bg-primary/5 p-3">
              <div className="flex items-center gap-1.5">
                <Sparkles
                  className="h-3.5 w-3.5 text-primary"
                  aria-hidden="true"
                />
                <p className="text-xs font-semibold uppercase tracking-wide text-primary">
                  Đề xuất
                </p>
              </div>
              <p className="text-sm mt-2 leading-relaxed">
                {data.walk.recommendation}
              </p>
            </div>
            {data.walk.visited.length > 1 ? (
              <section aria-labelledby="rc-trace">
                <h3
                  id="rc-trace"
                  className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                >
                  Chuỗi prerequisite đã quét
                </h3>
                <ul className="mt-2 space-y-1.5">
                  {data.walk.visited.map((node) => (
                    <li
                      key={`${node.concept_id}-${node.depth}`}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="truncate pr-2">
                        <span className="text-muted-foreground mr-2">
                          {"·".repeat(node.depth) || "▪"}
                        </span>
                        {node.name}
                      </span>
                      <span
                        className={`tabular-nums shrink-0 ${
                          node.p_mastery < 0.3
                            ? "text-red-700 dark:text-red-300"
                            : node.p_mastery < 0.6
                              ? "text-amber-700 dark:text-amber-300"
                              : "text-emerald-700 dark:text-emerald-300"
                        }`}
                      >
                        mastery {pct(node.p_mastery)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            <p className="text-[11px] text-muted-foreground">
              Confidence: {pct(data.confidence)}%
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
