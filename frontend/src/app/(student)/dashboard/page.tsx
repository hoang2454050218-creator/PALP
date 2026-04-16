"use client";

import { useEffect, useState } from "react";
import { BookOpen, Target, TrendingUp, Clock, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { ErrorState } from "@/components/shared/error-state";
import { StatCardSkeleton, CardSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { getMasteryLabel } from "@/lib/constants";
import { masteryColor, masteryBg } from "@/lib/utils";
import type { StudentPathway, MasteryState, LearnerProfile } from "@/types";
import Link from "next/link";

export default function StudentDashboard() {
  const { user } = useAuth();
  const [pathway, setPathway] = useState<StudentPathway | null>(null);
  const [mastery, setMastery] = useState<MasteryState[]>([]);
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  async function load() {
    setLoading(true);
    setError(false);
    try {
      const [p, m] = await Promise.all([
        api.get<StudentPathway>("/adaptive/pathway/1/").catch(() => null),
        api.get<MasteryState[]>("/adaptive/mastery/?course=1").catch(() => []),
      ]);
      setPathway(p);
      if (Array.isArray(m)) setMastery(m);
      else if (m && "results" in (m as any)) setMastery((m as any).results);

      const prof = await api.get<LearnerProfile>("/assessment/profile/1/").catch(() => null);
      setProfile(prof);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (error) {
    return (
      <div>
        <PageHeader title={`Xin chào, ${user?.last_name} ${user?.first_name}`} />
        <ErrorState
          title="Không thể tải dữ liệu"
          message="Vui lòng kiểm tra kết nối mạng và thử lại."
          onRetry={load}
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div>
        <PageHeader
          title={`Xin chào, ${user?.last_name} ${user?.first_name}`}
          description="Sức Bền Vật Liệu — Pilot PALP"
        />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <CardSkeleton lines={4} />
          <CardSkeleton lines={4} />
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title={`Xin chào, ${user?.last_name} ${user?.first_name}`}
        description="Sức Bền Vật Liệu — Pilot PALP"
      />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatCard
          title="Tiến độ tổng"
          value={`${pathway?.progress_pct ?? 0}%`}
          subtitle="Concepts đã hoàn thành"
          icon={Target}
          trend="up"
        />
        <StatCard
          title="Mức nắm vững trung bình"
          value={mastery.length > 0
            ? `${(mastery.reduce((s, m) => s + m.p_mastery, 0) / mastery.length * 100).toFixed(0)}%`
            : "---"
          }
          subtitle={mastery.length > 0
            ? getMasteryLabel(mastery.reduce((s, m) => s + m.p_mastery, 0) / mastery.length)
            : "Chưa có dữ liệu"
          }
          icon={TrendingUp}
        />
        <StatCard
          title="Bài tập đã làm"
          value={mastery.reduce((s, m) => s + m.attempt_count, 0)}
          subtitle="Tổng số lần thử"
          icon={BookOpen}
        />
        <StatCard
          title="Điểm đánh giá đầu vào"
          value={profile ? `${profile.overall_score.toFixed(0)}%` : "Chưa làm"}
          subtitle={profile ? "Đã hoàn thành" : "Hãy bắt đầu"}
          icon={Clock}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Lộ trình hiện tại</CardTitle>
          </CardHeader>
          <CardContent>
            {pathway ? (
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-muted-foreground">Tiến độ tổng</span>
                    <span className="font-medium">{pathway.progress_pct}%</span>
                  </div>
                  <Progress value={pathway.progress_pct} aria-label={`Tiến độ: ${pathway.progress_pct}%`} />
                </div>
                {pathway.current_milestone_title && (
                  <div className="rounded-lg bg-primary/5 p-4">
                    <p className="text-sm text-muted-foreground">Milestone hiện tại</p>
                    <p className="font-medium mt-1">{pathway.current_milestone_title}</p>
                    {pathway.current_concept_name && (
                      <p className="text-sm text-muted-foreground mt-1">
                        Concept: {pathway.current_concept_name}
                      </p>
                    )}
                  </div>
                )}
                <Link href="/pathway">
                  <Button className="w-full">
                    Tiếp tục học <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="text-center py-8">
                <Target className="h-10 w-10 text-muted-foreground/40 mx-auto mb-4" aria-hidden="true" />
                <p className="font-medium mb-2">Chưa có lộ trình</p>
                <p className="text-sm text-muted-foreground mb-4">
                  Hoàn thành đánh giá đầu vào để hệ thống tạo lộ trình học phù hợp với bạn.
                </p>
                <Link href="/assessment">
                  <Button>Bắt đầu đánh giá</Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Mức nắm vững theo Concept</CardTitle>
          </CardHeader>
          <CardContent>
            {mastery.length > 0 ? (
              <div className="space-y-3">
                {mastery.map((m) => (
                  <div key={m.id} className="flex items-center gap-3">
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="truncate">{m.concept_name}</span>
                        <span className="flex items-center gap-1.5">
                          <span className={`font-medium ${masteryColor(m.p_mastery)}`}>
                            {(m.p_mastery * 100).toFixed(0)}%
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {getMasteryLabel(m.p_mastery)}
                          </span>
                        </span>
                      </div>
                      <Progress
                        value={m.p_mastery * 100}
                        indicatorClassName={masteryBg(m.p_mastery)}
                        aria-label={`${m.concept_name}: ${(m.p_mastery * 100).toFixed(0)}% — ${getMasteryLabel(m.p_mastery)}`}
                      />
                    </div>
                    <Badge variant={
                      m.p_mastery >= 0.85 ? "success" :
                      m.p_mastery >= 0.6 ? "warning" : "secondary"
                    }>
                      {m.attempt_count} lần
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6">
                <TrendingUp className="h-10 w-10 text-muted-foreground/40 mx-auto mb-3" aria-hidden="true" />
                <p className="text-muted-foreground">
                  Dữ liệu nắm vững sẽ xuất hiện sau khi bạn bắt đầu làm bài tập.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
