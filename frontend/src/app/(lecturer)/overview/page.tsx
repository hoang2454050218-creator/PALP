"use client";

import { useEffect, useState } from "react";
import { Users, AlertTriangle, CheckCircle2, Eye, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { ErrorState } from "@/components/shared/error-state";
import { StatCardSkeleton, CardSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { SEVERITY_CONFIG } from "@/lib/constants";
import type { ClassOverview, Alert } from "@/types";
import Link from "next/link";

export default function LecturerOverview() {
  const [overview, setOverview] = useState<ClassOverview | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  async function load() {
    setLoading(true);
    setError(false);
    try {
      const [ov, alerts] = await Promise.all([
        api.get<ClassOverview>("/dashboard/class/1/overview/"),
        api.get<any>("/dashboard/alerts/?class_id=1&status=active"),
      ]);
      setOverview(ov);
      const alertList = Array.isArray(alerts) ? alerts : alerts.results || [];
      setRecentAlerts(alertList.slice(0, 5));
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
        <PageHeader title="Tổng quan lớp học" />
        <ErrorState
          title="Không thể tải dữ liệu lớp học"
          message="Vui lòng kiểm tra kết nối mạng và thử lại."
          onRetry={load}
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div>
        <PageHeader title="Tổng quan lớp học" description="Dashboard giảng viên — Sức Bền Vật Liệu" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <CardSkeleton lines={5} />
          <CardSkeleton lines={4} />
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Tổng quan lớp học"
        description="Dashboard giảng viên — Sức Bền Vật Liệu"
      >
        <Link href="/alerts">
          <Button variant="outline" size="sm">
            <AlertTriangle className="mr-2 h-4 w-4" aria-hidden="true" />
            Xem cảnh báo
          </Button>
        </Link>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatCard
          title="Tổng sinh viên"
          value={overview?.total_students ?? 0}
          icon={Users}
        />
        <StatCard
          title="Ổn định"
          value={overview?.on_track ?? 0}
          subtitle={overview ? `${Math.round((overview.on_track / Math.max(overview.total_students, 1)) * 100)}%` : "---"}
          icon={CheckCircle2}
          trend="up"
        />
        <StatCard
          title="Cần theo dõi"
          value={overview?.needs_attention ?? 0}
          icon={Eye}
          trend={overview && overview.needs_attention > 0 ? "down" : "neutral"}
        />
        <StatCard
          title="Cần can thiệp"
          value={overview?.needs_intervention ?? 0}
          icon={AlertTriangle}
          trend={overview && overview.needs_intervention > 0 ? "down" : "neutral"}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Sức khỏe cohort</CardTitle>
          </CardHeader>
          <CardContent>
            {overview ? (
              <div className="space-y-6">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>Mức nắm vững trung bình</span>
                    <span className="font-semibold">{(overview.avg_mastery * 100).toFixed(0)}%</span>
                  </div>
                  <Progress
                    value={overview.avg_mastery * 100}
                    aria-label={`Mức nắm vững trung bình: ${(overview.avg_mastery * 100).toFixed(0)}%`}
                  />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>Hoàn thành trung bình</span>
                    <span className="font-semibold">{overview.avg_completion_pct.toFixed(0)}%</span>
                  </div>
                  <Progress
                    value={overview.avg_completion_pct}
                    indicatorClassName="bg-green-500"
                    aria-label={`Hoàn thành trung bình: ${overview.avg_completion_pct.toFixed(0)}%`}
                  />
                </div>
                <div className="grid grid-cols-3 gap-4 pt-2">
                  <div className="text-center rounded-lg bg-green-50 p-3">
                    <CheckCircle2 className="h-4 w-4 text-green-600 mx-auto mb-1" aria-hidden="true" />
                    <p className="text-2xl font-bold text-green-700">{overview.on_track}</p>
                    <p className="text-xs text-green-600">Ổn định</p>
                  </div>
                  <div className="text-center rounded-lg bg-yellow-50 p-3">
                    <AlertCircle className="h-4 w-4 text-yellow-600 mx-auto mb-1" aria-hidden="true" />
                    <p className="text-2xl font-bold text-yellow-700">{overview.needs_attention}</p>
                    <p className="text-xs text-yellow-600">Theo dõi</p>
                  </div>
                  <div className="text-center rounded-lg bg-red-50 p-3">
                    <AlertTriangle className="h-4 w-4 text-red-600 mx-auto mb-1" aria-hidden="true" />
                    <p className="text-2xl font-bold text-red-700">{overview.needs_intervention}</p>
                    <p className="text-xs text-red-600">Can thiệp</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-6">
                <Users className="h-10 w-10 text-muted-foreground/40 mx-auto mb-3" aria-hidden="true" />
                <p className="text-muted-foreground">
                  Dữ liệu sẽ xuất hiện khi sinh viên bắt đầu sử dụng hệ thống.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Cảnh báo gần đây</CardTitle>
              <Link href="/alerts">
                <Button variant="ghost" size="sm">Xem tất cả</Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {recentAlerts.length > 0 ? (
              <div className="space-y-3">
                {recentAlerts.map((alert) => {
                  const config = SEVERITY_CONFIG[alert.severity];
                  const SeverityIcon = config.icon;
                  return (
                    <div key={alert.id} className="flex items-start gap-3 rounded-lg border p-3">
                      <SeverityIcon
                        className={`h-4 w-4 mt-0.5 shrink-0 ${
                          alert.severity === "red" ? "text-red-600" :
                          alert.severity === "yellow" ? "text-yellow-600" : "text-green-600"
                        }`}
                        aria-hidden="true"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm truncate">{alert.student_name}</span>
                          <Badge className={`text-[10px] ${config.color}`}>{config.label}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{alert.reason}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-6">
                <CheckCircle2 className="h-10 w-10 text-green-500/60 mx-auto mb-3" aria-hidden="true" />
                <p className="font-medium mb-1">Không có cảnh báo mới</p>
                <p className="text-sm text-muted-foreground">
                  Tất cả sinh viên đang tiến triển bình thường.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
