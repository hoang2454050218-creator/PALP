"use client";

import { useEffect, useState, useCallback } from "react";
import { CheckCircle2, Clock, ArrowRight, RotateCcw, ClipboardCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState } from "@/components/shared/error-state";
import { CardSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import type { Assessment, AssessmentQuestion, AssessmentSession, LearnerProfile } from "@/types";

type Phase = "intro" | "quiz" | "result";

export default function AssessmentPage() {
  const [phase, setPhase] = useState<Phase>("intro");
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [questions, setQuestions] = useState<AssessmentQuestion[]>([]);
  const [session, setSession] = useState<AssessmentSession | null>(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [startTime, setStartTime] = useState(0);
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [answeredCount, setAnsweredCount] = useState(0);

  useEffect(() => {
    api.get<{ results?: Assessment[] } | Assessment[]>("/assessment/")
      .then((data) => {
        const list = Array.isArray(data) ? data : data.results || [];
        setAssessments(list);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const startAssessment = async (assessmentId: number) => {
    try {
      const s = await api.post<AssessmentSession>(`/assessment/${assessmentId}/start/`);
      setSession(s);
      const qData = await api.get<AssessmentQuestion[] | { results?: AssessmentQuestion[] }>(
        `/assessment/${assessmentId}/questions/`
      );
      const qList = Array.isArray(qData) ? qData : (qData as any).results || [];
      setQuestions(qList);
      setPhase("quiz");
      setCurrentQ(0);
      setStartTime(Date.now());
      setAnsweredCount(0);
    } catch {
      toast({ variant: "error", title: "Không thể bắt đầu", description: "Vui lòng thử lại sau." });
    }
  };

  const submitAnswer = async () => {
    if (!session || !selectedAnswer) return;
    const timeTaken = Math.round((Date.now() - startTime) / 1000);

    try {
      await api.post(`/assessment/sessions/${session.id}/answer/`, {
        question_id: questions[currentQ].id,
        answer: selectedAnswer,
        time_taken_seconds: timeTaken,
      });

      const newCount = answeredCount + 1;
      setAnsweredCount(newCount);
      setSelectedAnswer(null);
      setStartTime(Date.now());

      if (currentQ + 1 < questions.length) {
        setCurrentQ(currentQ + 1);
      } else {
        const result = await api.post<{ session: AssessmentSession; profile: LearnerProfile }>(
          `/assessment/sessions/${session.id}/complete/`
        );
        setSession(result.session);
        setProfile(result.profile);
        setPhase("result");
        toast({
          variant: "success",
          title: "Hoàn thành đánh giá!",
          description: `Điểm của bạn: ${result.profile.overall_score.toFixed(0)}%`,
        });
      }
    } catch {
      toast({ variant: "error", title: "Không thể lưu câu trả lời", description: "Vui lòng thử lại." });
    }
  };

  if (phase === "intro") {
    if (loading) {
      return (
        <div>
          <PageHeader title="Đánh giá đầu vào" description="Xác định năng lực nền trước khi bắt đầu lộ trình học" />
          <div className="max-w-2xl mx-auto">
            <CardSkeleton lines={3} />
          </div>
        </div>
      );
    }

    return (
      <div>
        <PageHeader title="Đánh giá đầu vào" description="Xác định năng lực nền trước khi bắt đầu lộ trình học" />
        <div className="max-w-2xl mx-auto">
          {assessments.length > 0 ? (
            assessments.map((a) => (
              <Card key={a.id} className="mb-4">
                <CardHeader>
                  <CardTitle>{a.title}</CardTitle>
                  <CardDescription>{a.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 mb-6 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-4 w-4" aria-hidden="true" />{a.time_limit_minutes} phút
                    </span>
                    <span>{a.question_count} câu hỏi</span>
                  </div>
                  <Button onClick={() => startAssessment(a.id)} className="w-full">
                    Bắt đầu đánh giá
                  </Button>
                </CardContent>
              </Card>
            ))
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <ClipboardCheck className="h-12 w-12 text-muted-foreground/40 mx-auto mb-4" aria-hidden="true" />
                <p className="font-medium text-lg mb-2">Chưa có bài đánh giá</p>
                <p className="text-muted-foreground">
                  Giảng viên chưa tạo bài đánh giá cho khóa học này. Vui lòng liên hệ giảng viên.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    );
  }

  if (phase === "quiz" && questions.length > 0) {
    const q = questions[currentQ];
    const progressPct = ((currentQ) / questions.length) * 100;

    return (
      <div>
        <PageHeader title="Đánh giá đầu vào" />
        <div className="max-w-2xl mx-auto">
          <div className="mb-6">
            <div className="flex justify-between text-sm text-muted-foreground mb-2">
              <span>Câu {currentQ + 1} / {questions.length}</span>
              <span>{Math.round(progressPct)}%</span>
            </div>
            <Progress value={progressPct} aria-label={`Tiến độ: ${Math.round(progressPct)}%`} />
          </div>

          <Card>
            <CardContent className="pt-6">
              <p className="text-lg font-medium mb-6" id="assessment-question">{q.text}</p>
              <fieldset aria-labelledby="assessment-question">
                <legend className="sr-only">Chọn đáp án cho câu {currentQ + 1}</legend>
                <div className="space-y-3" role="radiogroup" aria-label="Các đáp án">
                  {q.options.map((opt, idx) => (
                    <button
                      key={idx}
                      role="radio"
                      aria-checked={selectedAnswer === opt}
                      onClick={() => setSelectedAnswer(opt)}
                      className={`w-full text-left rounded-lg border p-4 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
                        selectedAnswer === opt
                          ? "border-primary bg-primary/5 ring-2 ring-primary"
                          : "border-border hover:border-primary/50 hover:bg-accent"
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
              <Button
                onClick={submitAnswer}
                disabled={!selectedAnswer}
                className="w-full mt-6"
              >
                {currentQ + 1 < questions.length ? (
                  <>Tiếp theo <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" /></>
                ) : (
                  <>Hoàn thành <CheckCircle2 className="ml-2 h-4 w-4" aria-hidden="true" /></>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (phase === "result" && profile) {
    return (
      <div>
        <PageHeader title="Kết quả đánh giá" />
        <div className="max-w-2xl mx-auto">
          <Card className="mb-6">
            <CardContent className="pt-6 text-center">
              <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
                <CheckCircle2 className="h-10 w-10 text-primary" aria-hidden="true" />
              </div>
              <h2 className="text-3xl font-bold">{profile.overall_score.toFixed(0)}%</h2>
              <p className="text-muted-foreground mt-2">Điểm đánh giá đầu vào</p>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 mb-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600" aria-hidden="true" />
                  Nắm vững
                </CardTitle>
              </CardHeader>
              <CardContent>
                {profile.strengths.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {profile.strengths.map((id) => (
                      <Badge key={id} variant="success">Concept #{id}</Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Chưa xác định</p>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <ArrowRight className="h-4 w-4 text-blue-600" aria-hidden="true" />
                  Cần bổ sung
                </CardTitle>
              </CardHeader>
              <CardContent>
                {profile.weaknesses.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {profile.weaknesses.map((id) => (
                      <Badge key={id} variant="warning">Concept #{id}</Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Không có</p>
                )}
              </CardContent>
            </Card>
          </div>

          <Button onClick={() => window.location.href = "/pathway"} className="w-full">
            Bắt đầu lộ trình học
          </Button>
        </div>
      </div>
    );
  }

  return null;
}
