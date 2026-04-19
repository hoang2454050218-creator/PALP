"use client";

import { useEffect, useState } from "react";
import { Sparkles, Wand2, FileCheck2 } from "lucide-react";

import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { CardSkeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { useCourseContext, useEnsureCourseContext } from "@/hooks/use-course-context";
import { api } from "@/lib/api";

import type { GeneratedExercise } from "@/components/phase6/types";
import type { Concept } from "@/types";

interface ConceptListResponse {
  results?: Concept[];
}

export default function CopilotPage() {
  const { user } = useAuth();
  useEnsureCourseContext("lecturer");
  const courseId = useCourseContext((s) => s.courseId);
  const ctxLoading = useCourseContext((s) => s.loading);

  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [exercises, setExercises] = useState<GeneratedExercise[]>([]);
  const [selectedConcept, setSelectedConcept] = useState<number | "">("");
  const [difficulty, setDifficulty] = useState<1 | 2 | 3>(2);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [actingId, setActingId] = useState<number | null>(null);
  const [error, setError] = useState(false);

  async function load() {
    if (courseId == null) return;
    setLoading(true);
    setError(false);
    try {
      const [conceptsResp, exercisesResp] = await Promise.all([
        api.get<Concept[] | ConceptListResponse>(
          `/curriculum/courses/${courseId}/concepts/`,
        ),
        api.get<{ exercises: GeneratedExercise[] }>(
          `/copilot/exercises/?course_id=${courseId}`,
        ),
      ]);
      const list = Array.isArray(conceptsResp)
        ? conceptsResp
        : conceptsResp.results || [];
      setConcepts(list);
      if (list.length > 0 && selectedConcept === "") {
        setSelectedConcept(list[0].id);
      }
      setExercises(exercisesResp.exercises);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  if (user && user.role !== "lecturer" && user.role !== "admin") {
    return null;
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Trợ lý giảng viên (Co-pilot)" />
        <ErrorState
          title="Không tải được dữ liệu"
          message="Hãy thử tải lại sau ít phút."
          onRetry={load}
        />
      </div>
    );
  }

  if (loading || !user || ctxLoading) {
    return (
      <div>
        <PageHeader title="Trợ lý giảng viên (Co-pilot)" />
        <div className="grid gap-6 lg:grid-cols-2">
          <CardSkeleton lines={5} />
          <CardSkeleton lines={5} />
        </div>
      </div>
    );
  }

  async function handleGenerate() {
    if (selectedConcept === "" || courseId == null) return;
    setGenerating(true);
    try {
      const created = await api.post<GeneratedExercise>(
        "/copilot/exercises/generate/",
        {
          course_id: courseId,
          concept_id: selectedConcept,
          difficulty,
        },
      );
      setExercises((prev) => [created, ...prev]);
    } catch {
      // ignore — error UI will surface on next refresh
    } finally {
      setGenerating(false);
    }
  }

  async function handleApprove(id: number) {
    setActingId(id);
    try {
      const updated = await api.post<GeneratedExercise>(
        `/copilot/exercises/${id}/approve/`,
        { notes: "auto-approved via UI" },
      );
      setExercises((prev) => prev.map((e) => (e.id === id ? updated : e)));
    } catch {
      // ignore
    } finally {
      setActingId(null);
    }
  }

  async function handleReject(id: number) {
    setActingId(id);
    try {
      const updated = await api.post<GeneratedExercise>(
        `/copilot/exercises/${id}/reject/`,
        { notes: "rejected via UI" },
      );
      setExercises((prev) => prev.map((e) => (e.id === id ? updated : e)));
    } catch {
      // ignore
    } finally {
      setActingId(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Trợ lý giảng viên (Co-pilot)"
        description="Sinh đề · phản hồi · tổng hợp — luôn cần GV duyệt trước khi xuất bản"
      >
        <span
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"
          aria-hidden="true"
        >
          <Wand2 className="h-5 w-5" />
        </span>
      </PageHeader>

      <section
        aria-label="Sinh đề bài"
        className="grid gap-6 lg:grid-cols-2 items-start"
      >
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sparkles
                className="h-4 w-4 text-muted-foreground"
                aria-hidden="true"
              />
              <CardTitle className="text-base">Sinh đề bài mới</CardTitle>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Template deterministic — không hallucination, không dùng LLM.
              Bạn chỉnh sửa rồi duyệt.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label
                htmlFor="copilot-concept"
                className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1"
              >
                Concept
              </label>
              <select
                id="copilot-concept"
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={selectedConcept}
                onChange={(e) =>
                  setSelectedConcept(
                    e.target.value === "" ? "" : Number(e.target.value),
                  )
                }
                aria-label="Chọn concept"
              >
                {concepts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <span
                id="copilot-difficulty-label"
                className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1"
              >
                Mức độ
              </span>
              <div
                className="flex gap-2"
                role="group"
                aria-labelledby="copilot-difficulty-label"
              >
                {[1, 2, 3].map((d) => (
                  <Button
                    key={d}
                    size="sm"
                    variant={difficulty === d ? "default" : "outline"}
                    onClick={() => setDifficulty(d as 1 | 2 | 3)}
                  >
                    {d === 1 ? "Dễ" : d === 2 ? "TB" : "Khó"}
                  </Button>
                ))}
              </div>
            </div>
            <Button
              onClick={handleGenerate}
              disabled={generating || selectedConcept === ""}
              className="gap-1.5"
            >
              <Wand2 className="h-4 w-4" aria-hidden="true" />
              {generating ? "Đang sinh…" : "Sinh đề mới"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileCheck2
                className="h-4 w-4 text-muted-foreground"
                aria-hidden="true"
              />
              <CardTitle className="text-base">Bản nháp gần đây</CardTitle>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Duyệt → tự động tạo MicroTask trong curriculum
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {exercises.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Chưa có bản nháp nào. Sinh thử 1 đề ở panel bên trái.
              </p>
            ) : (
              <ul className="space-y-3" aria-label="Danh sách bản nháp">
                {exercises.slice(0, 8).map((ex) => (
                  <li
                    key={ex.id}
                    className="rounded-md border bg-card/50 p-3 space-y-2"
                  >
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-sm font-medium truncate">
                        {ex.title}
                      </span>
                      <span
                        className={`text-[10px] font-semibold uppercase tracking-wide rounded px-1.5 py-0.5 ${
                          ex.status === "published"
                            ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                            : ex.status === "rejected"
                              ? "bg-red-500/10 text-red-700 dark:text-red-300"
                              : "bg-amber-500/10 text-amber-700 dark:text-amber-300"
                        }`}
                      >
                        {ex.status}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {ex.body.question}
                    </p>
                    {ex.status === "draft" ? (
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => handleApprove(ex.id)}
                          disabled={actingId === ex.id}
                        >
                          Duyệt & xuất bản
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleReject(ex.id)}
                          disabled={actingId === ex.id}
                        >
                          Từ chối
                        </Button>
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </section>

      <footer className="mt-10 border-t pt-6">
        <p className="text-xs text-muted-foreground text-center max-w-2xl mx-auto leading-relaxed">
          Co-pilot dùng template deterministic — không gọi LLM, không
          hallucination. Bạn vẫn là người duyệt cuối cùng trước khi đề lên
          curriculum thật.
        </p>
      </footer>
    </div>
  );
}
