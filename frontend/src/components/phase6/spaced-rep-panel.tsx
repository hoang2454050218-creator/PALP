"use client";

import { Calendar, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import type { ReviewItem } from "./types";

interface Props {
  due: ReviewItem[];
  upcoming: ReviewItem[];
  loading: boolean;
  busy: boolean;
  onRate: (itemConceptId: number, rating: 1 | 2 | 3 | 4) => Promise<void>;
}

const RATING_LABEL: Record<number, string> = {
  1: "Quên hẳn",
  2: "Vất vả",
  3: "Tốt",
  4: "Dễ",
};

const RATING_VARIANT: Record<number, "destructive" | "outline" | "default" | "secondary"> = {
  1: "destructive",
  2: "outline",
  3: "default",
  4: "secondary",
};

function timestamp(value: string | null): string {
  if (!value) return "—";
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

export function SpacedRepPanel({
  due,
  upcoming,
  loading,
  busy,
  onRate,
}: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Calendar
            className="h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <CardTitle className="text-base">Bài ôn (FSRS)</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Lịch ôn được tự điều chỉnh theo trí nhớ — đánh giá thật để hệ
          thống căn nhịp ôn cho bạn (FSRS-4.5)
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <p className="text-sm text-muted-foreground" role="status">
            Đang tải…
          </p>
        ) : due.length === 0 && upcoming.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Chưa có thẻ ôn nào — sau khi hoàn thành bài tập, hệ thống sẽ
            tự đẩy concept vào lịch ôn.
          </p>
        ) : (
          <>
            {due.length > 0 ? (
              <section aria-labelledby="sr-due">
                <div className="flex items-center gap-1.5 mb-2">
                  <RefreshCcw
                    className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400"
                    aria-hidden="true"
                  />
                  <h3
                    id="sr-due"
                    className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                  >
                    Cần ôn ngay ({due.length})
                  </h3>
                </div>
                <ul className="space-y-3">
                  {due.slice(0, 5).map((item) => (
                    <li
                      key={item.id}
                      className="rounded-md border bg-card/50 p-3 space-y-2"
                    >
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="text-sm font-medium truncate">
                          {item.concept_name}
                        </span>
                        <span className="text-[11px] text-muted-foreground shrink-0 tabular-nums">
                          stability ~{item.stability_days.toFixed(1)}d
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground tabular-nums">
                        Hạn: {timestamp(item.due_at)} ·{" "}
                        {item.review_count} reviews · {item.lapse_count} lapses
                      </p>
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {[1, 2, 3, 4].map((r) => (
                          <Button
                            key={r}
                            size="sm"
                            variant={RATING_VARIANT[r]}
                            disabled={busy}
                            onClick={() =>
                              onRate(item.concept_id, r as 1 | 2 | 3 | 4)
                            }
                            aria-label={`Đánh giá ${RATING_LABEL[r]} cho ${item.concept_name}`}
                          >
                            {RATING_LABEL[r]}
                          </Button>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {upcoming.length > 0 ? (
              <section aria-labelledby="sr-upcoming">
                <h3
                  id="sr-upcoming"
                  className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2"
                >
                  Sắp tới ({upcoming.length})
                </h3>
                <ul className="space-y-1.5">
                  {upcoming.slice(0, 5).map((item) => (
                    <li
                      key={item.id}
                      className="flex items-baseline justify-between gap-2 text-sm"
                    >
                      <span className="truncate">{item.concept_name}</span>
                      <span className="text-[11px] text-muted-foreground tabular-nums shrink-0">
                        {timestamp(item.due_at)}
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
