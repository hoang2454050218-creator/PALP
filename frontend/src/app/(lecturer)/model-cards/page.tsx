"use client";

import { useEffect, useState } from "react";
import { ScrollText, BookOpen, ShieldCheck, FileJson } from "lucide-react";

import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { CardSkeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";

import type { ModelCardSummary } from "@/components/phase7/types";

type ModelCardListResponse =
  | ModelCardSummary[]
  | { results: ModelCardSummary[] };

function unwrap<T>(payload: T[] | { results: T[] }): T[] {
  return Array.isArray(payload) ? payload : payload.results;
}

function statusBadge(status: ModelCardSummary["status"]) {
  switch (status) {
    case "published":
      return <Badge variant="success">Đã xuất bản</Badge>;
    case "reviewed":
      return <Badge>Đã review</Badge>;
    default:
      return <Badge variant="outline">Bản nháp</Badge>;
  }
}

function formatPerformance(perf: ModelCardSummary["performance"]): string {
  if (!perf || typeof perf !== "object") {
    return "Chưa có metric";
  }
  const benchmark = (perf as Record<string, unknown>).benchmark as
    | Record<string, number>
    | undefined;
  if (benchmark) {
    return Object.entries(benchmark)
      .map(([k, v]) => `${k}: ${typeof v === "number" ? v.toFixed(3) : v}`)
      .join("  ·  ");
  }
  const metrics = (perf as Record<string, unknown>).metrics as
    | Record<string, number>
    | undefined;
  if (metrics) {
    return Object.entries(metrics)
      .map(([k, v]) => `${k}: ${typeof v === "number" ? v.toFixed(3) : v}`)
      .join("  ·  ");
  }
  return "Chưa có metric";
}

export default function ModelCardsPage() {
  const { user } = useAuth();

  const [cards, setCards] = useState<ModelCardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  async function load() {
    setLoading(true);
    setError(false);
    try {
      const resp = await api.get<ModelCardListResponse>(
        "/publication/model-cards/",
      );
      setCards(unwrap(resp));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (user && user.role !== "lecturer" && user.role !== "admin") {
    return null;
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Model Cards" />
        <ErrorState
          title="Không thể tải Model Cards"
          message="Vui lòng kiểm tra kết nối và thử lại."
          onRetry={load}
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div>
        <PageHeader
          title="Model Cards"
          description="Báo cáo minh bạch về các mô hình đang chạy"
        />
        <CardSkeleton lines={6} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Model Cards"
        description="Báo cáo minh bạch (theo Mitchell et al. 2019) về các mô hình ML đang chạy trong hệ thống."
      />

      <Card className="mb-6 border-dashed bg-muted/30">
        <CardContent className="py-4 text-sm text-muted-foreground">
          <p className="flex items-start gap-2">
            <ShieldCheck
              className="mt-0.5 h-4 w-4 shrink-0"
              aria-hidden="true"
            />
            <span>
              Mỗi Model Card mô tả phạm vi sử dụng, dữ liệu huấn luyện, hiệu năng
              đã đo, và các vấn đề đạo đức cần lưu ý. Sinh viên chỉ nhìn thấy
              các bản đã xuất bản; lecturer / admin nhìn thấy thêm các bản nháp.
            </span>
          </p>
        </CardContent>
      </Card>

      {cards.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            Chưa có Model Card nào. Vào Django admin →
            <span className="font-mono text-xs"> publication/modelcard </span>
            để tạo bản nháp đầu tiên.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {cards.map((card) => (
            <Card key={card.id}>
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <CardTitle className="text-base flex items-center gap-2">
                      <ScrollText className="h-4 w-4" aria-hidden="true" />
                      {card.title}
                    </CardTitle>
                    <p className="text-xs text-muted-foreground font-mono">
                      {card.model_label} · {card.licence}
                    </p>
                  </div>
                  {statusBadge(card.status)}
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <section>
                  <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                    Phạm vi sử dụng
                  </p>
                  <p>{card.intended_use}</p>
                </section>
                {card.out_of_scope_uses?.length > 0 && (
                  <section>
                    <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                      Không phù hợp cho
                    </p>
                    <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
                      {card.out_of_scope_uses.map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                  </section>
                )}
                <section>
                  <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                    Hiệu năng đã đo
                  </p>
                  <p className="font-mono text-xs">
                    {formatPerformance(card.performance)}
                  </p>
                </section>
                {card.ethical_considerations && (
                  <section>
                    <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                      Lưu ý đạo đức
                    </p>
                    <p className="text-muted-foreground">
                      {card.ethical_considerations}
                    </p>
                  </section>
                )}
                {card.caveats && (
                  <section>
                    <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                      Cảnh báo
                    </p>
                    <p className="text-muted-foreground">{card.caveats}</p>
                  </section>
                )}
                <section className="flex flex-wrap items-center gap-3 pt-2 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <BookOpen className="h-3 w-3" aria-hidden="true" />
                    {card.authors?.length || 0} tác giả
                  </span>
                  <span className="flex items-center gap-1">
                    <FileJson className="h-3 w-3" aria-hidden="true" />
                    Phiên bản: {card.updated_at?.slice(0, 10) || "—"}
                  </span>
                </section>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
