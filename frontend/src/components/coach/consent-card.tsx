"use client";

import { Lock, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";

import type { CoachConsentPayload } from "./types";

interface Props {
  consent: CoachConsentPayload | null;
  busy?: boolean;
  onToggleLocal: (next: boolean) => Promise<void>;
  onToggleCloud: (next: boolean) => Promise<void>;
  onToggleEmergency: (next: boolean) => Promise<void>;
}

export function CoachConsentCard({
  consent,
  busy,
  onToggleLocal,
  onToggleCloud,
  onToggleEmergency,
}: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <ShieldCheck
            className="h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <CardTitle className="text-base">Quyền & ranh giới</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Bạn quyết định dữ liệu của bạn đi đâu — coach tôn trọng từng lựa
          chọn của bạn
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <Row
          title="Trợ lý AI nội bộ (Local)"
          description="Chạy trên máy chủ của trường — PII không bao giờ rời hệ thống."
          checked={!!consent?.ai_coach_local}
          disabled={busy}
          onToggle={onToggleLocal}
        />
        <Row
          title="Trợ lý AI bên ngoài (Cloud)"
          description="Cloud LLM (Anthropic / OpenAI). Mọi tin nhắn được mã hoá PII trước khi gửi đi."
          checked={!!consent?.ai_coach_cloud}
          disabled={busy}
          onToggle={onToggleCloud}
        />
        <Row
          title="Cho phép liên hệ khẩn cấp"
          description="Khi phát hiện rủi ro nghiêm trọng và counselor không phản hồi 15 phút, hệ thống sẽ liên hệ người bạn đặt làm liên hệ khẩn cấp."
          checked={!!consent?.share_emergency_contact}
          disabled={busy}
          onToggle={onToggleEmergency}
        />

        <div className="rounded-md border border-border/60 bg-muted/40 p-3 flex items-start gap-2 text-xs text-muted-foreground">
          <Lock className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden="true" />
          <span>
            Mọi tin nhắn được lưu mã hoá. Nội dung không bao giờ vào audit
            log; chỉ metadata an toàn (intent, provider, latency, refusal
            flag) được giữ để counselor + admin có thể debug.
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

function Row({
  title,
  description,
  checked,
  disabled,
  onToggle,
}: {
  title: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onToggle: (next: boolean) => Promise<void>;
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
          {description}
        </p>
      </div>
      <Switch
        checked={checked}
        onCheckedChange={onToggle}
        disabled={disabled}
        aria-label={`Bật/tắt: ${title}`}
      />
    </div>
  );
}

export function CoachCooldownBanner({
  consent,
}: {
  consent: CoachConsentPayload | null;
}) {
  if (!consent?.cooldown_until) return null;
  const until = new Date(consent.cooldown_until);
  if (Number.isNaN(until.getTime()) || until <= new Date()) return null;
  return (
    <div
      role="alert"
      className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm flex items-start gap-2"
    >
      <Lock
        className="h-4 w-4 mt-0.5 text-amber-700 dark:text-amber-300"
        aria-hidden="true"
      />
      <div>
        <p className="font-medium">Coach đang tạm khoá</p>
        <p className="text-xs text-muted-foreground mt-1">
          Hệ thống nhận thấy nhiều mẫu prompt-injection. Coach sẽ mở lại
          vào{" "}
          <span className="tabular-nums">
            {until.toLocaleString("vi-VN", {
              hour: "2-digit",
              minute: "2-digit",
              day: "2-digit",
              month: "2-digit",
            })}
          </span>
          .
        </p>
      </div>
    </div>
  );
}
