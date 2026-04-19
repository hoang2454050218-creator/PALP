"use client";

import { useState } from "react";
import { ArrowLeftRight, Handshake, UserPlus, Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";

import type { PeerConsentPayload, PeerMatch } from "./types";

interface Props {
  consent: PeerConsentPayload | null;
  matches: PeerMatch[];
  loading: boolean;
  onToggleConsent: (granted: boolean) => Promise<void>;
  onFindMatch: () => Promise<void>;
  onRespond: (
    matchId: number,
    action: "accept" | "decline" | "archive",
  ) => Promise<void>;
}

const STATUS_LABEL: Record<PeerMatch["status"], string> = {
  pending: "Đang chờ bạn đồng ý",
  active: "Đang hoạt động",
  archived: "Đã lưu trữ",
  declined: "Đã từ chối",
};

const STATUS_COLOR: Record<PeerMatch["status"], string> = {
  pending: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
  active: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  archived: "bg-muted text-muted-foreground",
  declined: "bg-muted text-muted-foreground",
};

export function BuddyPanel({
  consent,
  matches,
  loading,
  onToggleConsent,
  onFindMatch,
  onRespond,
}: Props) {
  const enabled = !!consent?.peer_teaching;
  const [findingMatch, setFindingMatch] = useState(false);

  async function handleFind() {
    setFindingMatch(true);
    try {
      await onFindMatch();
    } finally {
      setFindingMatch(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Handshake
              className="h-4 w-4 text-muted-foreground"
              aria-hidden="true"
            />
            <CardTitle className="text-base">Buddy dạy nhau</CardTitle>
          </div>
          <Switch
            checked={enabled}
            onCheckedChange={onToggleConsent}
            disabled={loading}
            aria-label="Bật ghép cặp dạy nhau"
          />
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Ghép với 1 bạn — mỗi người dạy bên kia 1 concept mạnh-yếu chéo
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {!enabled ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Tính năng này mặc định <strong>tắt</strong>. Khi bật, hệ thống tìm
              1 bạn cùng cohort sao cho cả hai có thể dạy nhau (không phải bạn
              dạy 1 chiều).
            </p>
            <div className="rounded-md border border-border/60 bg-muted/40 p-3 flex items-start gap-2 text-xs text-muted-foreground">
              <Lock className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden="true" />
              <span>
                Bạn quyết định có gặp hay không sau khi xem profile match. Mọi
                phiên dạy nhau đều có thể huỷ trước khi bắt đầu.
              </span>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {matches.length === 0 ? (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Bạn chưa có match nào. Bấm bên dưới để hệ thống tìm thử.
                </p>
                <Button
                  onClick={handleFind}
                  disabled={findingMatch}
                  className="gap-2"
                >
                  <UserPlus className="h-4 w-4" aria-hidden="true" />
                  {findingMatch ? "Đang tìm…" : "Tìm bạn ghép"}
                </Button>
              </div>
            ) : (
              <ul className="space-y-3" aria-label="Danh sách match">
                {matches.map((m) => (
                  <li
                    key={m.id}
                    className="rounded-lg border bg-card/50 p-3 space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-medium truncate">
                          {m.partner.display_name}
                        </p>
                        <p
                          className={`inline-block text-[10px] font-semibold uppercase tracking-wide rounded px-1.5 py-0.5 mt-1 ${STATUS_COLOR[m.status]}`}
                        >
                          {STATUS_LABEL[m.status]}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <ArrowLeftRight
                        className="h-3.5 w-3.5 text-muted-foreground"
                        aria-hidden="true"
                      />
                      <span className="text-muted-foreground">
                        Bạn dạy:{" "}
                        <span className="font-medium text-foreground">
                          {m.you_teach.name}
                        </span>
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <ArrowLeftRight
                        className="h-3.5 w-3.5 text-muted-foreground rotate-180"
                        aria-hidden="true"
                      />
                      <span className="text-muted-foreground">
                        Bạn học:{" "}
                        <span className="font-medium text-foreground">
                          {m.you_learn.name}
                        </span>
                      </span>
                    </div>
                    {m.status === "pending" ? (
                      <div className="flex gap-2 pt-1">
                        <Button
                          size="sm"
                          onClick={() => onRespond(m.id, "accept")}
                        >
                          Đồng ý
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onRespond(m.id, "decline")}
                        >
                          Từ chối
                        </Button>
                      </div>
                    ) : m.status === "active" ? (
                      <div className="flex gap-2 pt-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onRespond(m.id, "archive")}
                        >
                          Lưu trữ
                        </Button>
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
