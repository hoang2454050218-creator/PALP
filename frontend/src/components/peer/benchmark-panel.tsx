"use client";

import { Info, Users, Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";

import type {
  BenchmarkBand,
  BenchmarkResult,
  PeerConsentPayload,
} from "./types";

interface Props {
  consent: PeerConsentPayload | null;
  benchmark: BenchmarkResult | null;
  loading: boolean;
  onToggleConsent: (granted: boolean) => Promise<void>;
}

const BAND_LABEL: Record<BenchmarkBand, string> = {
  top_25_pct: "Trong nhóm tiến nhanh nhất",
  above_median: "Trên trung vị cohort",
  below_median: "Dưới trung vị cohort",
  building_phase: "Đang xây nền tảng",
  "": "—",
};

const BAND_COLOR: Record<BenchmarkBand, string> = {
  top_25_pct: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
  above_median: "bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/30",
  below_median: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30",
  building_phase: "bg-primary/10 text-primary border-primary/30",
  "": "bg-muted text-muted-foreground border-border",
};

export function BenchmarkPanel({
  consent,
  benchmark,
  loading,
  onToggleConsent,
}: Props) {
  const enabled = !!consent?.peer_comparison;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Users
              className="h-4 w-4 text-muted-foreground"
              aria-hidden="true"
            />
            <CardTitle className="text-base">Cohort Benchmark</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              id="peer-comparison-toggle"
              checked={enabled}
              onCheckedChange={onToggleConsent}
              disabled={loading}
              aria-label="Bật so sánh ẩn danh trong cohort"
            />
          </div>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Vị trí ẩn danh trong nhóm cùng xuất phát điểm — không có bảng xếp
          hạng, không tên ai
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {!enabled ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Tính năng này mặc định <strong>tắt</strong>. Khi bật, hệ thống chỉ
              cho bạn biết bạn đang trong nhóm rộng nào (top 25% / trên trung vị
              / dưới trung vị / đang xây nền), không bao giờ hiển thị thứ hạng
              hay tên ai.
            </p>
            <div className="rounded-md border border-border/60 bg-muted/40 p-3 flex items-start gap-2 text-xs text-muted-foreground">
              <Lock className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden="true" />
              <span>
                Cohort được tách theo năng lực ban đầu (Marsh 1987 BFLPE) để
                tránh việc bạn bị đè bẹp bởi sinh viên khác cohort. Bạn có thể
                tắt bất cứ lúc nào.
              </span>
            </div>
          </div>
        ) : loading ? (
          <p className="text-sm text-muted-foreground" role="status">
            Đang tính toán…
          </p>
        ) : benchmark && benchmark.available && benchmark.band ? (
          <div className="space-y-3">
            <div
              className={`rounded-md border px-3 py-2 ${BAND_COLOR[benchmark.band]}`}
              role="status"
            >
              <p className="text-xs font-semibold uppercase tracking-wide">
                Vị trí của bạn
              </p>
              <p className="text-sm font-medium mt-0.5">
                {BAND_LABEL[benchmark.band]}
              </p>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {benchmark.safe_copy}
            </p>
            {benchmark.cohort_size ? (
              <p className="text-[11px] text-muted-foreground">
                Cohort {benchmark.cohort_size} người · cập nhật mỗi tuần
              </p>
            ) : null}
          </div>
        ) : (
          <div className="rounded-md border border-border/60 bg-muted/40 p-3 flex items-start gap-2 text-sm text-muted-foreground">
            <Info className="h-4 w-4 mt-0.5 shrink-0" aria-hidden="true" />
            <span>
              {benchmark?.safe_copy ||
                "Chưa đủ dữ liệu để xếp cohort. Học vài tuần để hệ thống có cơ sở so sánh."}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
