"use client";

import { ArrowRight, CheckCircle2, Clock, Lightbulb, Target } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";

import type { DailyPlan, DailyPlanItem } from "./types";

const ICONS: Record<DailyPlanItem["kind"], typeof Target> = {
  weak_concept: Lightbulb,
  milestone_task: Target,
  variety_review: CheckCircle2,
};

const KIND_LABEL: Record<DailyPlanItem["kind"], string> = {
  weak_concept: "Củng cố",
  milestone_task: "Tiến tới mục tiêu",
  variety_review: "Ôn để giữ kiến thức",
};

// Subtle per-kind tint so the eye can scan the row faster without
// crossing the gamification line — these are UI affordances, not
// rewards.
const KIND_ACCENT: Record<DailyPlanItem["kind"], string> = {
  weak_concept: "bg-amber-500/10 text-amber-600 dark:text-amber-300",
  milestone_task: "bg-primary/10 text-primary",
  variety_review: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-300",
};

interface Props {
  plan: DailyPlan | null;
  onChanged: () => void;
}

export function DailyPlanCard({ plan }: Props) {
  if (!plan || plan.items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Hôm nay</CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            Chưa đủ dữ liệu để gợi ý
          </p>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Hãy bắt đầu một micro-task ở trang Lộ trình để hệ thống có dữ liệu cá
            nhân hoá. Vài bài là đủ.
          </p>
          <div className="mt-4">
            <Link href="/pathway">
              <Button variant="outline" size="sm">Đến lộ trình</Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-baseline justify-between gap-2">
          <CardTitle className="text-lg">Hôm nay</CardTitle>
          <span className="text-xs text-muted-foreground">
            {plan.items.length} việc gợi ý
          </span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Bạn quyết định bắt đầu từ đâu — không bắt buộc làm theo thứ tự
        </p>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {plan.items.map((item, idx) => {
          const Icon = ICONS[item.kind];
          return (
            <article
              key={`${item.kind}-${idx}`}
              aria-labelledby={`plan-item-${idx}-title`}
              className="group flex flex-col rounded-lg border bg-card/50 p-4 transition-colors hover:bg-card hover:border-primary/40 motion-safe:transition-shadow hover:shadow-sm focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background"
            >
              <div className="flex items-start gap-3">
                <span
                  className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${KIND_ACCENT[item.kind]}`}
                  aria-hidden="true"
                >
                  <Icon className="h-4 w-4" />
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {KIND_LABEL[item.kind]}
                  </p>
                  <p
                    id={`plan-item-${idx}-title`}
                    className="font-medium mt-0.5 leading-snug"
                  >
                    {item.title}
                  </p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground mt-3 flex-1 leading-relaxed">
                {item.rationale}
              </p>
              <div className="mt-3 flex items-center justify-between gap-2 pt-3 border-t border-border/40">
                {item.estimated_minutes ? (
                  <span className="text-xs text-muted-foreground inline-flex items-center gap-1.5 tabular-nums">
                    <Clock className="h-3 w-3" aria-hidden="true" />
                    {item.estimated_minutes} phút
                  </span>
                ) : <span aria-hidden="true" />}
                {item.micro_task_id ? (
                  <Link
                    href={`/task?id=${item.micro_task_id}`}
                    aria-label={`Bắt đầu: ${item.title}`}
                    className="rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <Button size="sm" variant="ghost" className="gap-1.5">
                      Bắt đầu
                      <ArrowRight className="h-3.5 w-3.5 motion-safe:transition-transform motion-safe:group-hover:translate-x-0.5" aria-hidden="true" />
                    </Button>
                  </Link>
                ) : null}
              </div>
            </article>
          );
        })}
      </CardContent>
    </Card>
  );
}
