"use client";

import { Sparkles } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import type { NorthStarPayload } from "./types";

const STRATEGY_LABELS: Record<string, string> = {
  spaced_practice: "Học dãn cách",
  deep_focus_blocks: "Khối tập trung sâu",
  peer_teaching: "Dạy bạn / được bạn dạy",
  worked_examples: "Đọc lời giải mẫu",
  self_explanation: "Tự giải thích bằng lời",
  retrieval_practice: "Truy hồi kiến thức",
  other: "Chiến lược khác",
};

const CAREER_CATEGORY_LABELS: Record<string, string> = {
  software_backend: "Backend dev",
  software_frontend: "Frontend dev",
  software_fullstack: "Full-stack dev",
  data: "Data / Analytics",
  ai_ml: "AI / ML",
  devops: "DevOps / SRE",
  security: "Cybersecurity",
  engineering: "Kỹ thuật khác",
  academia: "Sau đại học / Nghiên cứu",
  other: "Khác",
};

interface Props {
  data: NorthStarPayload["forethought"] | null;
  onChanged: () => void;
}

export function ForethoughtPanel({ data }: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <CardTitle className="text-base">Định hướng (Forethought)</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Bạn muốn đi về đâu, và tuần này bạn cam kết gì
        </p>
      </CardHeader>
      <CardContent className="space-y-5 divide-y divide-border/50">
        <section className="pt-0">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Mục tiêu nghề nghiệp
          </h3>
          {data?.career_goal ? (
            <div className="mt-1.5">
              <p className="font-medium leading-tight">{data.career_goal.label}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {CAREER_CATEGORY_LABELS[data.career_goal.category] ?? data.career_goal.category}{" "}
                · tầm nhìn {data.career_goal.horizon_months} tháng
              </p>
            </div>
          ) : (
            <p className="mt-1.5 text-sm text-muted-foreground">
              Chưa đặt — không bắt buộc, nhưng giúp coach gợi ý đúng hơn.
            </p>
          )}
        </section>

        <section className="pt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Mục tiêu học kỳ
          </h3>
          {data?.semester_goals && data.semester_goals.length > 0 ? (
            <ul className="mt-1.5 space-y-3">
              {data.semester_goals.map((g) => (
                <li key={g.id} className="text-sm">
                  <p>
                    Mastery mục tiêu{" "}
                    <span className="font-medium">{Math.round(g.mastery_target * 100)}%</span>
                    {" · "}
                    hoàn thành{" "}
                    <span className="font-medium">{g.completion_target_pct}%</span>{" "}
                    milestones
                  </p>
                  {g.intent ? (
                    <p className="mt-1 text-xs text-muted-foreground italic">
                      &ldquo;{g.intent}&rdquo;
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-1.5 text-sm text-muted-foreground">
              Chưa đặt mục tiêu cho học kỳ này.
            </p>
          )}
        </section>

        <section className="pt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Tuần này
          </h3>
          {data?.weekly_goal ? (
            <div className="mt-1.5 text-sm">
              <p>
                Cam kết{" "}
                <span className="font-medium">{data.weekly_goal.target_minutes} phút</span>{" "}
                tập trung và{" "}
                <span className="font-medium">{data.weekly_goal.target_micro_task_count}</span>{" "}
                micro-task.
              </p>
              {data.weekly_goal.strategy_plans.length > 0 ? (
                <p className="mt-1 text-xs text-muted-foreground">
                  Chiến lược thử:{" "}
                  {data.weekly_goal.strategy_plans
                    .map((s) => STRATEGY_LABELS[s.strategy] ?? s.strategy)
                    .join(", ")}
                </p>
              ) : null}
            </div>
          ) : (
            <p className="mt-1.5 text-sm text-muted-foreground">
              Bạn chưa đặt mục tiêu tuần — đặt 1 mục tiêu nhỏ giúp dễ duy trì hơn.
            </p>
          )}
        </section>
      </CardContent>
    </Card>
  );
}
