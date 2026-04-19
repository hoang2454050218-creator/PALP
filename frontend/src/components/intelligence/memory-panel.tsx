"use client";

import { Brain, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import type { MemoryRecallPayload } from "./types";

interface Props {
  enabled: boolean;
  data: MemoryRecallPayload | null;
  loading: boolean;
  onClear: () => Promise<void>;
}

function pct(value: number): number {
  return Math.round(value * 100);
}

function timestamp(value: string): string {
  try {
    return new Date(value).toLocaleString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
    });
  } catch {
    return value;
  }
}

export function CoachMemoryPanel({ enabled, data, loading, onClear }: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Brain
              className="h-4 w-4 text-muted-foreground"
              aria-hidden="true"
            />
            <CardTitle className="text-base">Coach nhớ gì về bạn</CardTitle>
          </div>
          {enabled ? (
            <Button
              size="sm"
              variant="ghost"
              onClick={onClear}
              className="gap-1.5 text-destructive hover:text-destructive"
              aria-label="Xoá toàn bộ trí nhớ của coach"
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              Xoá hết
            </Button>
          ) : null}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Bạn có thể xem & xoá toàn bộ trí nhớ bất cứ lúc nào — coach tôn
          trọng quyền &quot;to be forgotten&quot;
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {!enabled ? (
          <p className="text-sm text-muted-foreground">
            Tính năng này mặc định <strong>tắt</strong>. Khi bật, coach sẽ
            ghi nhớ bối cảnh học tập (mục tiêu, concept đã học, chiến lược
            hiệu quả) để gợi ý cá nhân hơn qua thời gian.
          </p>
        ) : loading ? (
          <p className="text-sm text-muted-foreground" role="status">
            Đang tải…
          </p>
        ) : !data || (!data.semantic.length && !data.episodic.length && !data.procedural.length) ? (
          <p className="text-sm text-muted-foreground">
            Coach chưa ghi nhớ gì cả — hãy chat thêm để memory hình thành.
          </p>
        ) : (
          <>
            {data.semantic.length > 0 ? (
              <section aria-labelledby="mem-semantic">
                <h3
                  id="mem-semantic"
                  className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                >
                  Sự thật về bạn
                </h3>
                <ul className="mt-2 space-y-1.5">
                  {data.semantic.map((s) => (
                    <li
                      key={s.key}
                      className="flex items-baseline justify-between gap-2 text-sm"
                    >
                      <span className="font-medium truncate">{s.key}</span>
                      <span className="text-muted-foreground tabular-nums shrink-0 text-xs">
                        confidence {pct(s.confidence)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {data.procedural.length > 0 ? (
              <section aria-labelledby="mem-procedural">
                <h3
                  id="mem-procedural"
                  className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                >
                  Chiến lược hiệu quả với bạn
                </h3>
                <ul className="mt-2 space-y-1.5">
                  {data.procedural.map((p) => (
                    <li
                      key={p.strategy_key}
                      className="flex items-baseline justify-between gap-2 text-sm"
                    >
                      <span className="truncate">{p.strategy_key}</span>
                      <span className="tabular-nums shrink-0 text-emerald-700 dark:text-emerald-300">
                        {pct(p.effectiveness_estimate)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {data.episodic.length > 0 ? (
              <section aria-labelledby="mem-episodic">
                <h3
                  id="mem-episodic"
                  className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                >
                  Sự kiện gần đây
                </h3>
                <ul className="mt-2 space-y-1.5">
                  {data.episodic.map((e, idx) => (
                    <li
                      key={`${e.kind}-${idx}`}
                      className="text-sm"
                    >
                      <p className="leading-snug">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mr-2">
                          {e.kind}
                        </span>
                        {e.summary}
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        {timestamp(e.occurred_at)}
                      </p>
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
