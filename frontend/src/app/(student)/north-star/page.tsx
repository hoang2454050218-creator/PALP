"use client";

import { useEffect, useState } from "react";
import { Compass } from "lucide-react";

import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { CardSkeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { displayName } from "@/lib/utils";

import { ForethoughtPanel } from "@/components/north-star/forethought-panel";
import { PerformancePanel } from "@/components/north-star/performance-panel";
import { ReflectionPanel } from "@/components/north-star/reflection-panel";
import { DailyPlanCard } from "@/components/north-star/daily-plan-card";
import type { DailyPlan, NorthStarPayload } from "@/components/north-star/types";

export default function NorthStarPage() {
  const { user } = useAuth();
  const [data, setData] = useState<NorthStarPayload | null>(null);
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  async function load() {
    setLoading(true);
    setError(false);
    try {
      const [ns, today] = await Promise.all([
        api.get<NorthStarPayload>("/goals/north-star/"),
        api.get<DailyPlan>("/goals/today/"),
      ]);
      setData(ns);
      setPlan(today);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  // Only fetch when we know the caller is actually a student. The
  // (student) layout will redirect non-student roles, but this guard
  // prevents the brief "không tải được" error flicker from showing while
  // the redirect is in flight.
  useEffect(() => {
    if (user?.role === "student") {
      load();
    }
  }, [user?.role]);

  const greeting = user ? `Định hướng của ${displayName(user)}` : "Định hướng";
  const description = "Bạn đang ở đâu · Đi về đâu · Hôm nay làm gì";

  // Non-student callers will be redirected by the layout — render nothing
  // in the meantime so the redirect happens silently instead of flashing
  // an error state.
  if (user && user.role !== "student") {
    return null;
  }

  if (error) {
    return (
      <div>
        <PageHeader title={greeting} description={description} />
        <ErrorState
          title="Không tải được dữ liệu định hướng"
          message="Hãy thử tải lại sau ít phút."
          onRetry={load}
        />
      </div>
    );
  }

  if (loading || !user) {
    return (
      <div>
        <PageHeader title={greeting} description={description} />
        <div className="mb-6">
          <CardSkeleton lines={3} />
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <CardSkeleton lines={4} />
          <CardSkeleton lines={4} />
          <CardSkeleton lines={4} />
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title={greeting} description={description}>
        <span
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"
          aria-hidden="true"
        >
          <Compass className="h-5 w-5" />
        </span>
      </PageHeader>

      <section aria-labelledby="today-section" className="mb-6">
        <h2 id="today-section" className="sr-only">Hôm nay</h2>
        <DailyPlanCard plan={plan} onChanged={load} />
      </section>

      <section
        aria-label="Chu trình SRL: Forethought, Performance, Self-Reflection"
        className="grid gap-6 lg:grid-cols-3 items-start"
      >
        <ForethoughtPanel data={data?.forethought ?? null} onChanged={load} />
        <PerformancePanel data={data?.performance ?? null} />
        <ReflectionPanel
          data={data?.reflection ?? null}
          weeklyGoal={data?.forethought?.weekly_goal ?? null}
          onSubmitted={load}
        />
      </section>

      <footer className="mt-10 border-t pt-6">
        <p className="text-xs text-muted-foreground text-center max-w-2xl mx-auto leading-relaxed">
          Trang này không dùng điểm thưởng, huy hiệu, streak, hay xếp hạng —
          theo nguyên tắc Self-Determination Theory để bảo vệ động lực nội tại
          của bạn. Mọi gợi ý chỉ là gương soi, bạn vẫn là người quyết định.
        </p>
      </footer>
    </div>
  );
}
