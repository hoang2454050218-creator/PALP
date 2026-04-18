"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Circle, Lock, ArrowRight, Route } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState } from "@/components/shared/error-state";
import { CardSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { difficultyLabel } from "@/lib/utils";
import { useCourseContext, useEnsureCourseContext } from "@/hooks/use-course-context";
import type { StudentPathway, Milestone, MilestoneDetail, Concept } from "@/types";
import Link from "next/link";

export default function PathwayPage() {
  const router = useRouter();
  useEnsureCourseContext("student");
  const courseId = useCourseContext((s) => s.courseId);
  const ctxLoading = useCourseContext((s) => s.loading);
  const [pathway, setPathway] = useState<StudentPathway | null>(null);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [milestoneConceptMap, setMilestoneConceptMap] = useState<Record<number, number[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  async function load(id: number) {
    setLoading(true);
    setError(false);
    try {
      const [p, mData, cData] = await Promise.all([
        api.get<StudentPathway>(`/adaptive/pathway/${id}/`),
        api.get<Milestone[] | { results: Milestone[] }>(`/curriculum/courses/${id}/milestones/`),
        api.get<Concept[] | { results: Concept[] }>(`/curriculum/courses/${id}/concepts/`),
      ]);
      setPathway(p);
      const milestoneList = Array.isArray(mData) ? mData : mData.results || [];
      setMilestones(milestoneList);
      setConcepts(Array.isArray(cData) ? cData : cData.results || []);

      const detailEntries = await Promise.all(
        milestoneList.map((m) =>
          api
            .get<MilestoneDetail>(`/curriculum/milestones/${m.id}/`)
            .then((d) => [m.id, d.concept_ids ?? []] as const)
            .catch(() => [m.id, [] as number[]] as const),
        ),
      );
      const map: Record<number, number[]> = {};
      detailEntries.forEach(([mid, ids]) => {
        map[mid] = ids;
      });
      setMilestoneConceptMap(map);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (courseId != null) load(courseId);
  }, [courseId]);

  if (error) {
    return (
      <div>
        <PageHeader title="Lộ trình học tập" />
        <ErrorState
          title="Không thể tải lộ trình"
          message="Vui lòng kiểm tra kết nối mạng hoặc hoàn thành đánh giá đầu vào trước."
          onRetry={() => courseId != null && load(courseId)}
          onBack={() => router.push("/dashboard")}
        />
      </div>
    );
  }

  if (loading || ctxLoading) {
    return (
      <div>
        <PageHeader title="Lộ trình học tập" description="Sức Bền Vật Liệu — Adaptive Pathway" />
        <CardSkeleton lines={3} />
        <div className="space-y-6 mt-6">
          <CardSkeleton lines={2} />
          <CardSkeleton lines={2} />
          <CardSkeleton lines={2} />
        </div>
      </div>
    );
  }

  if (!pathway && milestones.length === 0) {
    return (
      <div>
        <PageHeader title="Lộ trình học tập" />
        <Card>
          <CardContent className="py-12 text-center">
            <Route className="h-12 w-12 text-muted-foreground/40 mx-auto mb-4" aria-hidden="true" />
            <p className="font-medium text-lg mb-2">Chưa có lộ trình</p>
            <p className="text-muted-foreground mb-6">
              Hoàn thành đánh giá đầu vào để hệ thống tạo lộ trình học phù hợp với bạn.
            </p>
            <Link href="/assessment">
              <Button>Đi đến đánh giá đầu vào</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isConceptCompleted = (id: number) => pathway?.concepts_completed?.includes(id) ?? false;
  const isMilestoneCompleted = (id: number) => pathway?.milestones_completed?.includes(id) ?? false;

  return (
    <div>
      <PageHeader
        title="Lộ trình học tập"
        description="Sức Bền Vật Liệu — Adaptive Pathway"
      />

      {pathway && (
        <Card className="mb-8">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-muted-foreground">Tiến độ tổng thể</span>
              <span className="text-lg font-bold">{pathway.progress_pct}%</span>
            </div>
            <Progress
              value={pathway.progress_pct}
              className="h-4"
              aria-label={`Tiến độ tổng thể: ${pathway.progress_pct}%`}
            />
            <div className="flex flex-wrap items-center gap-4 mt-4 text-sm text-muted-foreground">
              <span>{pathway.concepts_completed?.length ?? 0} / {concepts.length} concepts</span>
              <span>Độ khó hiện tại: {difficultyLabel(pathway.current_difficulty)}</span>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-6">
        {milestones.map((milestone) => {
          const completed = isMilestoneCompleted(milestone.id);
          const isCurrent = pathway?.current_milestone === milestone.id;

          return (
            <Card key={milestone.id} className={isCurrent ? "ring-2 ring-primary" : ""}>
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    {completed ? (
                      <CheckCircle2 className="h-6 w-6 text-success mt-0.5 shrink-0" aria-hidden="true" />
                    ) : isCurrent ? (
                      <Circle className="h-6 w-6 text-primary fill-primary/20 mt-0.5 shrink-0" aria-hidden="true" />
                    ) : (
                      <Lock className="h-6 w-6 text-muted-foreground/40 mt-0.5 shrink-0" aria-hidden="true" />
                    )}
                    <div>
                      <CardTitle className="text-base">
                        {milestone.title}
                        <span className="sr-only">
                          {completed ? " — Đã hoàn thành" : isCurrent ? " — Đang thực hiện" : " — Chưa mở khóa"}
                        </span>
                      </CardTitle>
                      <p className="text-sm text-muted-foreground mt-1">{milestone.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant={completed ? "success" : isCurrent ? "default" : "secondary"}>
                      {completed ? "Hoàn thành" : isCurrent ? "Đang học" : `${milestone.task_count} bài`}
                    </Badge>
                    <Badge variant="outline">Tuần {milestone.target_week}</Badge>
                  </div>
                </div>
              </CardHeader>
              {(isCurrent || completed) && (
                <CardContent>
                  <div className="flex flex-wrap gap-2 mb-4">
                    {(milestoneConceptMap[milestone.id] ?? [])
                      .map((cid) => concepts.find((c) => c.id === cid))
                      .filter((c): c is Concept => Boolean(c))
                      .map((c) => (
                        <Badge
                          key={c.id}
                          variant={isConceptCompleted(c.id) ? "success" : "outline"}
                        >
                          {isConceptCompleted(c.id) && (
                            <CheckCircle2 className="h-3 w-3 mr-1" aria-hidden="true" />
                          )}
                          {c.name}
                        </Badge>
                      ))}
                  </div>
                  {isCurrent && (
                    <Link href="/task">
                      <Button size="sm">
                        Tiếp tục học <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
                      </Button>
                    </Link>
                  )}
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
