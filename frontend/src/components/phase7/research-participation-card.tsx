"use client";

import { useEffect, useState } from "react";
import { FlaskConical, Users, ShieldCheck, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import type {
  ResearchParticipation,
  ResearchProtocol,
} from "./types";

type ProtocolListResponse = ResearchProtocol[] | { results: ResearchProtocol[] };
type ParticipationListResponse =
  | ResearchParticipation[]
  | { results: ResearchParticipation[] };

function unwrap<T>(payload: T[] | { results: T[] }): T[] {
  return Array.isArray(payload) ? payload : payload.results;
}

export function ResearchParticipationCard() {
  const [protocols, setProtocols] = useState<ResearchProtocol[]>([]);
  const [participations, setParticipations] = useState<ResearchParticipation[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyCode, setBusyCode] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [p, mine] = await Promise.all([
        api.get<ProtocolListResponse>("/research/protocols/"),
        api.get<ParticipationListResponse>("/research/me/participations/"),
      ]);
      setProtocols(unwrap(p));
      setParticipations(unwrap(mine));
    } catch {
      // Read-only card: silently fall back to empty.
      setProtocols([]);
      setParticipations([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const stateFor = (code: string) =>
    participations.find((row) => row.protocol.code === code)?.state;

  async function decide(code: string, action: "opt-in" | "withdraw" | "decline") {
    setBusyCode(code);
    try {
      await api.post(`/research/protocols/${code}/${action}/`, {});
      toast({
        variant: "success",
        title: "Đã cập nhật",
        description:
          action === "opt-in"
            ? "Cảm ơn bạn đã đồng ý tham gia nghiên cứu."
            : action === "withdraw"
              ? "Bạn đã rút khỏi nghiên cứu. Dữ liệu của bạn sẽ bị loại khỏi các bản xuất tiếp theo."
              : "Bạn đã từ chối tham gia.",
      });
      await load();
    } catch {
      toast({
        variant: "error",
        title: "Không thể cập nhật",
        description: "Vui lòng thử lại sau.",
      });
    } finally {
      setBusyCode(null);
    }
  }

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <FlaskConical className="h-5 w-5" aria-hidden="true" />
          Tham gia nghiên cứu khoa học
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border border-dashed bg-muted/30 p-3 text-xs text-muted-foreground">
          <p className="flex items-start gap-2">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>
              Mọi đề cương được hội đồng đạo đức (IRB) phê duyệt, dữ liệu xuất ra
              đều được ẩn danh theo k-anonymity. Bạn có thể rút khỏi bất cứ lúc
              nào — dữ liệu sẽ bị loại khỏi các bản xuất tiếp theo.
            </span>
          </p>
        </div>

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Đang tải các đề cương đang mở...
          </div>
        ) : protocols.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Hiện chưa có đề cương nghiên cứu nào đang mở.
          </p>
        ) : (
          <div className="space-y-3">
            {protocols.map((proto) => {
              const state = stateFor(proto.code);
              const busy = busyCode === proto.code;
              return (
                <div
                  key={proto.code}
                  className="rounded-lg border p-3 space-y-2"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="space-y-1">
                      <p className="text-sm font-medium">{proto.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {proto.code}
                        {proto.irb_number ? ` · IRB ${proto.irb_number}` : ""}
                        {proto.pi_name ? ` · PI: ${proto.pi_name}` : ""}
                      </p>
                    </div>
                    {state === "opted_in" ? (
                      <Badge variant="success">
                        <Users className="h-3 w-3 mr-1" aria-hidden="true" />
                        Đang tham gia
                      </Badge>
                    ) : state === "withdrawn" ? (
                      <Badge variant="secondary">Đã rút</Badge>
                    ) : state === "declined" ? (
                      <Badge variant="outline">Đã từ chối</Badge>
                    ) : (
                      <Badge variant="outline">Đang mở</Badge>
                    )}
                  </div>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {proto.description}
                  </p>
                  <div className="flex flex-wrap gap-2 pt-1">
                    {state !== "opted_in" && (
                      <Button
                        size="sm"
                        onClick={() => decide(proto.code, "opt-in")}
                        disabled={busy}
                      >
                        Đồng ý tham gia
                      </Button>
                    )}
                    {state === "opted_in" && (
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => decide(proto.code, "withdraw")}
                        disabled={busy}
                      >
                        Rút khỏi
                      </Button>
                    )}
                    {!state && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => decide(proto.code, "decline")}
                        disabled={busy}
                      >
                        Từ chối
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
