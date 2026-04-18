"use client";

import { useEffect, useMemo, useState } from "react";
import { Network, Users, AlertTriangle, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState } from "@/components/shared/error-state";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useCourseContext, useEnsureCourseContext } from "@/hooks/use-course-context";

interface GraphNode {
  data: {
    id: string;
    code: string;
    label: string;
    order: number;
    avg_mastery: number | null;
    mastery_band: "low" | "medium" | "high" | "unknown";
    struggling_count: number;
    struggling_student_ids: number[];
  };
}

interface GraphEdge {
  data: {
    id: string;
    source: string;
    target: string;
  };
}

interface GraphPayload {
  course: { id: number; code: string; name: string };
  students_in_scope: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const BAND_STYLE: Record<string, { bg: string; ring: string; text: string; label: string }> = {
  low:    { bg: "bg-danger/10",  ring: "ring-danger/40",  text: "text-danger-foreground",  label: "Cần can thiệp" },
  medium: { bg: "bg-warning/10", ring: "ring-warning/40", text: "text-warning-foreground", label: "Cần theo dõi" },
  high:   { bg: "bg-success/10", ring: "ring-success/40", text: "text-success-foreground", label: "Tốt" },
  unknown:{ bg: "bg-muted",      ring: "ring-border",     text: "text-muted-foreground",   label: "Chưa có dữ liệu" },
};

export default function KnowledgeGraphPage() {
  useEnsureCourseContext("lecturer");
  const courseId = useCourseContext((s) => s.courseId);
  const classId = useCourseContext((s) => s.classId);
  const ctxLoading = useCourseContext((s) => s.loading);
  const [payload, setPayload] = useState<GraphPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selected, setSelected] = useState<GraphNode | null>(null);

  async function load(course: number, klass: number | null) {
    setLoading(true);
    setError(false);
    try {
      const qs = klass ? `?class_id=${klass}` : "";
      const data = await api.get<GraphPayload>(
        `/curriculum/courses/${course}/knowledge-graph/${qs}`,
      );
      setPayload(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (courseId != null) load(courseId, classId);
  }, [courseId, classId]);

  const layers = useMemo(() => topologicalLayers(payload), [payload]);

  if (loading || ctxLoading) {
    return (
      <div>
        <PageHeader
          title="Đồ thị kiến thức"
          description="Sơ đồ concept và mức nắm vững theo lớp"
        />
        <div className="flex items-center justify-center min-h-[300px] text-muted-foreground">
          <Loader2 className="h-6 w-6 motion-safe:animate-spin mr-2" aria-hidden="true" />
          Đang tải đồ thị...
        </div>
      </div>
    );
  }

  if (error || !payload) {
    return (
      <div>
        <PageHeader title="Đồ thị kiến thức" />
        <ErrorState
          title="Không thể tải đồ thị"
          message="Vui lòng kiểm tra kết nối và thử lại."
          onRetry={() => courseId != null && load(courseId, classId)}
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Đồ thị kiến thức"
        description={`${payload.course.code} – ${payload.course.name} · ${payload.students_in_scope} sinh viên trong phạm vi`}
      />

      <Card className="mb-6">
        <CardContent className="py-4 flex flex-wrap gap-4 text-sm">
          <Legend band="low" />
          <Legend band="medium" />
          <Legend band="high" />
          <Legend band="unknown" />
          <div className="ml-auto flex items-center gap-2 text-muted-foreground">
            <Network className="h-4 w-4" aria-hidden="true" />
            {payload.nodes.length} concept · {payload.edges.length} prerequisite
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Sơ đồ kiến thức theo lớp prerequisite</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <div
              className="relative grid gap-x-10 gap-y-4 min-w-max"
              style={{ gridTemplateColumns: `repeat(${Math.max(layers.length, 1)}, minmax(180px, 1fr))` }}
            >
              {layers.map((layer, idx) => (
                <div key={idx} className="space-y-3">
                  <div className="text-xs font-medium uppercase text-muted-foreground tracking-wide">
                    Tầng {idx + 1}
                  </div>
                  {layer.map(node => (
                    <button
                      key={node.data.id}
                      type="button"
                      onClick={() => setSelected(node)}
                      aria-pressed={selected?.data.id === node.data.id}
                      className={cn(
                        "w-full text-left rounded-lg border-2 p-3 transition-all",
                        "hover:shadow-md motion-safe:hover:scale-[1.02] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                        BAND_STYLE[node.data.mastery_band].bg,
                        BAND_STYLE[node.data.mastery_band].ring,
                        selected?.data.id === node.data.id ? "border-primary" : "border-transparent ring-1",
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className={cn("text-xs font-semibold", BAND_STYLE[node.data.mastery_band].text)}>
                            {node.data.code}
                          </div>
                          <div className="text-sm font-medium mt-0.5 line-clamp-2">{node.data.label}</div>
                        </div>
                        {node.data.avg_mastery !== null && (
                          <Badge variant={node.data.mastery_band === "high" ? "success" : node.data.mastery_band === "medium" ? "warning" : "destructive"}>
                            {Math.round(node.data.avg_mastery * 100)}%
                          </Badge>
                        )}
                      </div>
                      {node.data.struggling_count > 0 && (
                        <div className="flex items-center gap-1 mt-2 text-xs text-danger">
                          <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                          {node.data.struggling_count} SV đang khó khăn
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="self-start lg:sticky lg:top-4">
          <CardHeader>
            <CardTitle className="text-lg">
              {selected ? selected.data.label : "Chi tiết concept"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {selected ? (
              <>
                <div>
                  <div className="text-xs uppercase text-muted-foreground">Mã concept</div>
                  <div className="font-medium">{selected.data.code}</div>
                </div>
                <div>
                  <div className="text-xs uppercase text-muted-foreground">Mức nắm vững trung bình</div>
                  <div className="text-2xl font-bold">
                    {selected.data.avg_mastery !== null ? `${Math.round(selected.data.avg_mastery * 100)}%` : "Chưa có"}
                  </div>
                  <div className={cn("text-xs mt-1", BAND_STYLE[selected.data.mastery_band].text)}>
                    {BAND_STYLE[selected.data.mastery_band].label}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase text-muted-foreground flex items-center gap-1">
                    <Users className="h-3 w-3" aria-hidden="true" />
                    Sinh viên đang khó khăn
                  </div>
                  <div className="text-2xl font-bold text-danger">
                    {selected.data.struggling_count}
                  </div>
                  {selected.data.struggling_count > 0 && (
                    <p className="text-xs text-muted-foreground mt-1">
                      mastery &lt; 50% sau ≥ 3 lần thử
                    </p>
                  )}
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Chọn một concept trong sơ đồ để xem chi tiết.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Legend({ band }: { band: keyof typeof BAND_STYLE }) {
  return (
    <div className="flex items-center gap-2">
      <span className={cn("inline-block w-3 h-3 rounded ring-2", BAND_STYLE[band].bg, BAND_STYLE[band].ring)} aria-hidden="true" />
      <span className="text-xs text-muted-foreground">{BAND_STYLE[band].label}</span>
    </div>
  );
}

/**
 * Topological layering: assign each concept to the level = max(predecessor levels) + 1.
 * Concepts without prerequisites land in level 0. Falls back to ``order`` field on tie.
 */
function topologicalLayers(payload: GraphPayload | null): GraphNode[][] {
  if (!payload) return [];
  const nodes = payload.nodes;
  const edges = payload.edges;
  if (nodes.length === 0) return [];

  const incoming: Record<string, string[]> = {};
  const byId: Record<string, GraphNode> = {};
  nodes.forEach(n => {
    incoming[n.data.id] = [];
    byId[n.data.id] = n;
  });
  edges.forEach(e => {
    if (incoming[e.data.target]) incoming[e.data.target].push(e.data.source);
  });

  const level: Record<string, number> = {};
  const computeLevel = (id: string, seen: Set<string>): number => {
    if (level[id] !== undefined) return level[id];
    if (seen.has(id)) return 0; // break cycle defensively
    seen.add(id);
    const preds = incoming[id] || [];
    if (preds.length === 0) {
      level[id] = 0;
      return 0;
    }
    const maxPred = Math.max(...preds.map(p => computeLevel(p, seen)));
    level[id] = maxPred + 1;
    return level[id];
  };
  nodes.forEach(n => computeLevel(n.data.id, new Set()));

  const maxLevel = Math.max(0, ...Object.values(level));
  const layers: GraphNode[][] = Array.from({ length: maxLevel + 1 }, () => []);
  nodes.forEach(n => layers[level[n.data.id] || 0].push(n));
  layers.forEach(layer => layer.sort((a, b) => a.data.order - b.data.order));
  return layers;
}
