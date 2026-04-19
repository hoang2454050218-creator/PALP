"use client";

import { useEffect, useState } from "react";
import { BookOpen, CheckCircle2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

import type { NorthStarPayload, WeeklyGoal } from "./types";

interface Props {
  data: NorthStarPayload["reflection"] | null;
  weeklyGoal: WeeklyGoal | null;
  onSubmitted: () => void;
}

const PROMPTS = [
  {
    field: "learned_text",
    label: "Tuần này bạn học được gì?",
    placeholder: "Có thể là 1 khái niệm mới, 1 mẹo, hay đơn giản là kiên nhẫn hơn",
  },
  {
    field: "struggle_text",
    label: "Đâu là khó khăn lớn nhất?",
    placeholder: "Không sao nếu chỉ là 1 dòng — viết ra giúp bạn nhìn rõ hơn",
  },
  {
    field: "next_priority_text",
    label: "Tuần sau bạn ưu tiên điều gì?",
    placeholder: "Một việc nhỏ thực tế thôi cũng được",
  },
] as const;

type FieldName = (typeof PROMPTS)[number]["field"];

export function ReflectionPanel({ data, weeklyGoal, onSubmitted }: Props) {
  const latest = data?.latest ?? null;
  const isSubmitted = Boolean(latest?.submitted_at);
  // Prefer the explicit weekly_goal id from latest stub; fall back to the
  // active weekly goal so the submit button is always actionable when a
  // weekly goal exists, even before the Saturday cron has opened a stub.
  const targetWeeklyGoalId = latest?.weekly_goal ?? weeklyGoal?.id ?? null;

  const [draft, setDraft] = useState<Record<FieldName, string>>({
    learned_text: latest?.learned_text ?? "",
    struggle_text: latest?.struggle_text ?? "",
    next_priority_text: latest?.next_priority_text ?? "",
  });
  const [effort, setEffort] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Re-sync local draft when the parent reloads after a successful submit
  // so the user sees their own text echoed back in the "đã hoàn thành" view.
  useEffect(() => {
    setDraft({
      learned_text: latest?.learned_text ?? "",
      struggle_text: latest?.struggle_text ?? "",
      next_priority_text: latest?.next_priority_text ?? "",
    });
  }, [latest?.id, latest?.submitted_at, latest?.learned_text, latest?.struggle_text, latest?.next_priority_text]);

  const hasAnyText =
    draft.learned_text.trim().length > 0 ||
    draft.struggle_text.trim().length > 0 ||
    draft.next_priority_text.trim().length > 0;

  async function submit() {
    if (!targetWeeklyGoalId) {
      toast({
        variant: "info",
        title: "Cần đặt mục tiêu tuần trước",
        description: "Hãy đặt một WeeklyGoal trước khi reflection — vì reflection gắn với mục tiêu cụ thể.",
      });
      return;
    }
    if (!hasAnyText && effort === null) {
      toast({
        variant: "info",
        title: "Chưa có nội dung để lưu",
        description: "Hãy điền ít nhất 1 ô hoặc chấm điểm nỗ lực.",
      });
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/goals/reflection/", {
        weekly_goal_id: targetWeeklyGoalId,
        ...draft,
        effort_rating: effort,
      });
      toast({
        variant: "success",
        title: "Đã ghi reflection",
        description: "Cảm ơn bạn đã dành thời gian.",
      });
      onSubmitted();
    } catch {
      toast({
        variant: "error",
        title: "Không gửi được reflection",
        description: "Hãy thử lại sau.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <CardTitle className="text-base">Phản tỉnh (Self-Reflection)</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          3 câu hỏi cuối tuần — không có câu trả lời đúng/sai
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {isSubmitted ? (
          <div className="space-y-3">
            <div className="flex items-start gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm">
              <CheckCircle2 className="h-4 w-4 mt-0.5 text-emerald-600 dark:text-emerald-400 shrink-0" aria-hidden="true" />
              <div>
                <p>
                  Đã ghi reflection tuần{" "}
                  <span className="font-medium">{latest!.week_start}</span>.
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Bạn có thể chỉnh sửa lại — nội dung mới sẽ ghi đè bản cũ.
                </p>
              </div>
            </div>
            {PROMPTS.map((p) => {
              const value = draft[p.field];
              if (!value.trim()) return null;
              return (
                <div key={p.field}>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    {p.label}
                  </p>
                  <p className="mt-1 text-sm whitespace-pre-wrap">{value}</p>
                </div>
              );
            })}
            <Button
              variant="outline"
              size="sm"
              onClick={() => onSubmitted()}
              className="w-full"
            >
              Sửa lại reflection
            </Button>
          </div>
        ) : (
          <>
            {PROMPTS.map((p) => (
              <div key={p.field}>
                <label
                  htmlFor={`reflection-${p.field}`}
                  className="text-xs uppercase tracking-wide text-muted-foreground"
                >
                  {p.label}
                </label>
                <Textarea
                  id={`reflection-${p.field}`}
                  className="mt-1"
                  value={draft[p.field]}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, [p.field]: e.target.value }))
                  }
                  rows={3}
                  placeholder={p.placeholder}
                />
              </div>
            ))}

            <fieldset>
              <legend className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
                Tự chấm nỗ lực (1 = rất thấp, 5 = rất cao)
              </legend>
              <div
                role="radiogroup"
                aria-label="Mức nỗ lực"
                className="flex gap-2"
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <Button
                    key={n}
                    type="button"
                    size="sm"
                    variant={effort === n ? "default" : "outline"}
                    onClick={() => setEffort(effort === n ? null : n)}
                    aria-pressed={effort === n}
                    aria-label={`Mức nỗ lực ${n}`}
                    className="min-w-[2.5rem]"
                  >
                    {n}
                  </Button>
                ))}
              </div>
            </fieldset>

            <Button
              onClick={submit}
              disabled={submitting || !targetWeeklyGoalId}
              className="w-full"
            >
              {submitting ? "Đang gửi…" : "Lưu reflection"}
            </Button>
            {!targetWeeklyGoalId ? (
              <p className="text-xs text-muted-foreground text-center">
                Cần đặt mục tiêu tuần trước khi reflection.
              </p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
