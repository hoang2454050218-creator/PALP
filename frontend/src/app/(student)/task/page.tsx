"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Clock, CheckCircle2, XCircle, RotateCcw, ArrowRight, Lightbulb, Trophy, BookOpen } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState } from "@/components/shared/error-state";
import { CardSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { difficultyLabel, formatDuration } from "@/lib/utils";
import { getMasteryLabel } from "@/lib/constants";
import { toast } from "@/hooks/use-toast";
import { useCourseContext, useEnsureCourseContext } from "@/hooks/use-course-context";
import { useStudySessionPing } from "@/hooks/use-study-session-ping";
import type { MicroTask, MicroTaskContent, TaskAttempt, PathwayAction } from "@/types";
import Link from "next/link";

export default function TaskPage() {
  const router = useRouter();
  useEnsureCourseContext("student");
  useStudySessionPing(true);
  const courseId = useCourseContext((s) => s.courseId);
  const ctxLoading = useCourseContext((s) => s.loading);
  const [currentTask, setCurrentTask] = useState<MicroTask | null>(null);
  const [allCompleted, setAllCompleted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [result, setResult] = useState<{
    attempt: TaskAttempt;
    pathway: PathwayAction;
  } | null>(null);
  const [startTime, setStartTime] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  const fetchNextTask = useCallback((id: number) => {
    setLoading(true);
    setError(false);
    api.get<MicroTask & { completed?: boolean }>(`/adaptive/next-task/${id}/`)
      .then((data) => {
        if ((data as MicroTask & { completed?: boolean }).completed) {
          setCurrentTask(null);
          setAllCompleted(true);
        } else {
          setCurrentTask(data);
          setStartTime(Date.now());
          setElapsed(0);
          setAllCompleted(false);
        }
      })
      .catch(() => {
        setCurrentTask(null);
        setError(true);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (courseId != null) fetchNextTask(courseId);
  }, [courseId, fetchNextTask]);

  useEffect(() => {
    if (!currentTask || result) return;
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [currentTask, startTime, result]);

  const submitTask = async () => {
    if (!currentTask || !selectedAnswer) return;
    const duration = Math.floor((Date.now() - startTime) / 1000);

    try {
      const res = await api.post<{
        attempt: TaskAttempt;
        mastery: unknown;
        pathway: PathwayAction;
      }>("/adaptive/submit/", {
        task_id: currentTask.id,
        answer: selectedAnswer,
        duration_seconds: duration,
        hints_used: 0,
      });

      setResult({ attempt: res.attempt, pathway: res.pathway });
      toast({
        variant: res.attempt.is_correct ? "success" : "info",
        title: res.attempt.is_correct ? "Chính xác!" : "Chưa đúng, hãy thử lại",
        description: `Mức nắm vững: ${(res.pathway.p_mastery * 100).toFixed(0)}% — ${getMasteryLabel(res.pathway.p_mastery)}`,
      });
    } catch {
      toast({
        variant: "error",
        title: "Không thể nộp bài",
        description: "Đã xảy ra lỗi khi nộp bài. Vui lòng thử lại.",
      });
    }
  };

  const nextTask = () => {
    setSelectedAnswer(null);
    setResult(null);
    if (courseId != null) fetchNextTask(courseId);
  };

  const retryTask = () => {
    setSelectedAnswer(null);
    setResult(null);
    setStartTime(Date.now());
    setElapsed(0);
  };

  if (loading || ctxLoading) {
    return (
      <div>
        <PageHeader title="Bài tập" />
        <div className="max-w-3xl mx-auto">
          <CardSkeleton lines={6} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Bài tập" />
        <ErrorState
          title="Không thể tải bài tập"
          message="Vui lòng kiểm tra kết nối mạng hoặc hoàn thành đánh giá đầu vào trước."
          onRetry={() => courseId != null && fetchNextTask(courseId)}
          onBack={() => router.push("/dashboard")}
        />
      </div>
    );
  }

  if (allCompleted) {
    return (
      <div>
        <PageHeader title="Bài tập" />
        <Card>
          <CardContent className="py-12 text-center">
            <Trophy className="h-12 w-12 text-warning mx-auto mb-4" aria-hidden="true" />
            <p className="text-lg font-semibold mb-2">Hoàn thành tất cả bài tập!</p>
            <p className="text-muted-foreground mb-6">
              Bạn đã hoàn thành tất cả bài tập hiện có. Hãy quay lại sau để xem nội dung mới.
            </p>
            <Link href="/dashboard">
              <Button>Về trang tổng quan</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!currentTask) {
    return (
      <div>
        <PageHeader title="Bài tập" />
        <Card>
          <CardContent className="py-12 text-center">
            <BookOpen className="h-12 w-12 text-muted-foreground/40 mx-auto mb-4" aria-hidden="true" />
            <p className="font-medium text-lg mb-2">Chưa có bài tập</p>
            <p className="text-muted-foreground mb-6">
              Bạn cần hoàn thành đánh giá đầu vào để hệ thống tạo lộ trình học phù hợp.
            </p>
            <Link href="/assessment">
              <Button>Đi đến đánh giá đầu vào</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const taskContent = currentTask.content as MicroTaskContent | undefined;
  const options = taskContent?.options ?? [];
  const questionText = taskContent?.question ?? "Hoàn thành bài tập bên dưới.";

  return (
    <div>
      <PageHeader title="Bài tập" description={currentTask.concept_name} />

      <div className="max-w-3xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div className="flex items-center gap-3">
            <Badge variant="outline">{difficultyLabel(currentTask.difficulty)}</Badge>
            <Badge variant="secondary">{currentTask.estimated_minutes} phút</Badge>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground" aria-atomic="true">
            <Clock className="h-4 w-4" aria-hidden="true" />
            <span aria-label={`Thời gian đã trôi qua: ${formatDuration(elapsed)}`}>
              {formatDuration(elapsed)}
            </span>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{currentTask.title}</CardTitle>
            {currentTask.description && (
              <CardDescription>{currentTask.description}</CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {!result ? (
              <div>
                <p className="text-base mb-6" id="task-question">{questionText}</p>
                <fieldset aria-labelledby="task-question" className="mb-6">
                  <legend className="sr-only">Chọn đáp án</legend>
                  <div className="space-y-3" role="radiogroup" aria-label="Các đáp án">
                    {options.map((opt: string, idx: number) => (
                      <button
                        key={idx}
                        role="radio"
                        aria-checked={selectedAnswer === opt}
                        onClick={() => setSelectedAnswer(opt)}
                        className={`w-full text-left rounded-lg border p-4 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
                          selectedAnswer === opt
                            ? "border-primary bg-primary/5 ring-2 ring-primary"
                            : "border-border hover:border-primary/50"
                        }`}
                      >
                        <span className="font-medium text-muted-foreground mr-3" aria-hidden="true">
                          {String.fromCharCode(65 + idx)}.
                        </span>
                        <span className="sr-only">Đáp án {String.fromCharCode(65 + idx)}: </span>
                        {opt}
                      </button>
                    ))}
                  </div>
                </fieldset>
                <Button onClick={submitTask} disabled={!selectedAnswer} className="w-full">
                  Nộp bài
                </Button>
              </div>
            ) : (
              <div className="space-y-6">
                <div
                  className={`flex items-center gap-4 rounded-lg p-5 border ${
                    result.attempt.is_correct
                      ? "bg-success/10 border-success/30"
                      : "bg-warning/10 border-warning/30"
                  }`}
                  role="status"
                >
                  {result.attempt.is_correct ? (
                    <CheckCircle2 className="h-8 w-8 text-success" aria-hidden="true" />
                  ) : (
                    <XCircle className="h-8 w-8 text-warning" aria-hidden="true" />
                  )}
                  <div>
                    <p className="font-semibold text-lg">
                      {result.attempt.is_correct ? "Chính xác!" : "Chưa đúng — hãy thử cách khác"}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Thời gian: {formatDuration(result.attempt.duration_seconds)}
                    </p>
                  </div>
                </div>

                <div className="rounded-lg bg-info/10 border border-info/30 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Lightbulb className="h-4 w-4 text-info" aria-hidden="true" />
                    <span className="font-medium text-info-foreground">Lộ trình tiếp theo</span>
                  </div>
                  <p className="text-sm text-info-foreground">{result.pathway.message}</p>
                  <p className="text-xs text-info-foreground/80 mt-1">
                    Mức nắm vững: {(result.pathway.p_mastery * 100).toFixed(0)}% — {getMasteryLabel(result.pathway.p_mastery)}
                  </p>
                </div>

                {result.pathway.supplementary_content && (
                  <Card className="border-warning/30 bg-warning/10">
                    <CardContent className="pt-4">
                      <p className="font-medium text-warning-foreground mb-2">
                        Tài liệu bổ trợ: {(result.pathway.supplementary_content as { title?: string }).title}
                      </p>
                      <p className="text-sm text-warning-foreground/80">
                        {(result.pathway.supplementary_content as { body?: string }).body}
                      </p>
                    </CardContent>
                  </Card>
                )}

                <div className="flex gap-3">
                  {!result.attempt.is_correct && (
                    <Button variant="outline" onClick={retryTask} className="flex-1">
                      <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" /> Thử lại
                    </Button>
                  )}
                  <Button onClick={nextTask} className="flex-1">
                    Bài tiếp <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
