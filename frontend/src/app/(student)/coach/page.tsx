"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Bot } from "lucide-react";

import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { CardSkeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { ApiError, api } from "@/lib/api";
import { displayName } from "@/lib/utils";

import { CoachComposer } from "@/components/coach/composer";
import {
  CoachConsentCard,
  CoachCooldownBanner,
} from "@/components/coach/consent-card";
import { CoachMessageBubble } from "@/components/coach/message-bubble";
import type {
  CoachConsentPayload,
  CoachConversationDetail,
  CoachMessageResponse,
} from "@/components/coach/types";
import { CoachMemoryPanel } from "@/components/intelligence/memory-panel";
import type { MemoryRecallPayload } from "@/components/intelligence/types";

export default function CoachPage() {
  const { user } = useAuth();
  const [consent, setConsent] = useState<CoachConsentPayload | null>(null);
  const [conversation, setConversation] =
    useState<CoachConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [consentBusy, setConsentBusy] = useState(false);
  const [warning, setWarning] = useState<string>("");
  const [memory, setMemory] = useState<MemoryRecallPayload | null>(null);
  const [memoryLoading, setMemoryLoading] = useState(false);
  const [memoryEnabled, setMemoryEnabled] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadConsent = useCallback(async () => {
    const c = await api.get<CoachConsentPayload>("/coach/consent/");
    setConsent(c);
    return c;
  }, []);

  const loadConversation = useCallback(async () => {
    const list = await api.get<{
      conversations: CoachConversationDetail[];
    }>("/coach/conversations/");
    const open = list.conversations.find((c) => c.status === "open");
    if (!open) {
      setConversation(null);
      return;
    }
    const detail = await api.get<CoachConversationDetail>(
      `/coach/conversations/${open.id}/`,
    );
    setConversation(detail);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      await loadConsent();
      await loadConversation();
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [loadConsent, loadConversation]);

  const loadMemory = useCallback(async () => {
    setMemoryLoading(true);
    try {
      const data = await api.get<MemoryRecallPayload>("/coach/memory/me/");
      setMemory(data);
      setMemoryEnabled(true);
    } catch (err) {
      // 403 -> consent off; show educational copy.
      if (err instanceof ApiError && err.status === 403) {
        setMemoryEnabled(false);
        setMemory(null);
      }
    } finally {
      setMemoryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user?.role === "student") {
      load();
      loadMemory();
    }
  }, [user?.role, load, loadMemory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation?.turns?.length]);

  async function handleClearMemory() {
    try {
      await api.delete("/coach/memory/me/");
      setMemory(null);
    } catch {
      // ignore
    }
  }

  const greeting = user
    ? `PALP Coach cho ${displayName(user)}`
    : "PALP Coach";
  const description =
    "Trợ lý học tập riêng của bạn · Local LLM mặc định · Không gamification";

  if (user && user.role !== "student") {
    return null;
  }

  if (error) {
    return (
      <div>
        <PageHeader title={greeting} description={description} />
        <ErrorState
          title="Không tải được dữ liệu coach"
          message="Hãy thử tải lại sau ít phút."
          onRetry={load}
        />
      </div>
    );
  }

  if (loading || !user || !consent) {
    return (
      <div>
        <PageHeader title={greeting} description={description} />
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <CardSkeleton lines={6} />
          </div>
          <CardSkeleton lines={4} />
        </div>
      </div>
    );
  }

  async function patchConsent(payload: Partial<CoachConsentPayload>) {
    setConsentBusy(true);
    try {
      const updated = await api.patch<CoachConsentPayload>(
        "/coach/consent/",
        payload,
      );
      setConsent(updated);
      return updated;
    } catch {
      return null;
    } finally {
      setConsentBusy(false);
    }
  }

  async function handleToggleLocal(next: boolean) {
    await patchConsent({ ai_coach_local: next });
  }

  async function handleToggleCloud(next: boolean) {
    await patchConsent({ ai_coach_cloud: next });
  }

  async function handleToggleEmergency(next: boolean) {
    await patchConsent({ share_emergency_contact: next });
  }

  async function handleSend(text: string) {
    setBusy(true);
    setWarning("");
    try {
      const resp = await api.post<CoachMessageResponse>("/coach/message/", {
        text,
      });
      // Refresh conversation detail (cheap GET) so the UI shows both
      // turns + audit/safety flags consistently.
      await loadConversation();
      if (resp.refusal_kind) {
        setWarning("Coach đã trả lời theo refusal pattern. Bạn có thể đặt câu hỏi khác.");
      } else if (resp.emergency_triggered) {
        setWarning("Hệ thống đã thông báo counselor. Hãy giữ liên lạc.");
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setWarning(
          err.detail ||
            "Bạn cần bật quyền 'Trợ lý AI nội bộ' trước khi chat với coach.",
        );
      } else {
        setWarning("Không gửi được tin nhắn. Hãy thử lại sau.");
      }
    } finally {
      setBusy(false);
    }
  }

  const composerDisabled =
    !consent.ai_coach_local ||
    Boolean(
      consent.cooldown_until &&
        new Date(consent.cooldown_until) > new Date(),
    );

  return (
    <div>
      <PageHeader title={greeting} description={description}>
        <span
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"
          aria-hidden="true"
        >
          <Bot className="h-5 w-5" />
        </span>
      </PageHeader>

      <CoachCooldownBanner consent={consent} />

      <section
        aria-label="Khu trò chuyện và quyền riêng tư"
        className="mt-4 grid gap-6 lg:grid-cols-3 items-start"
      >
        <Card className="lg:col-span-2 flex flex-col" aria-label="Hộp chat coach">
          <CardHeader>
            <CardTitle className="text-base">Trò chuyện</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Coach tôn trọng nguyên tắc: không viết bài hộ · không tiết lộ
              dữ liệu bạn khác · không gamification
            </p>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div
              className="flex flex-col gap-3 max-h-[420px] overflow-y-auto pr-1"
              aria-label="Lịch sử tin nhắn"
            >
              {!conversation || conversation.turns.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  Chưa có tin nhắn nào — hãy bắt đầu bằng câu hỏi về bài
                  học hoặc cảm nghĩ của bạn.
                </p>
              ) : (
                conversation.turns.map((turn) => (
                  <CoachMessageBubble key={turn.id} turn={turn} />
                ))
              )}
              <div ref={messagesEndRef} />
            </div>
            {warning ? (
              <p className="text-xs text-muted-foreground border-t pt-3" role="status">
                {warning}
              </p>
            ) : null}
            <CoachComposer
              disabled={composerDisabled}
              busy={busy}
              onSend={handleSend}
            />
          </CardContent>
        </Card>

        <div className="space-y-6">
          <CoachConsentCard
            consent={consent}
            busy={consentBusy}
            onToggleLocal={handleToggleLocal}
            onToggleCloud={handleToggleCloud}
            onToggleEmergency={handleToggleEmergency}
          />
          <CoachMemoryPanel
            enabled={memoryEnabled}
            data={memory}
            loading={memoryLoading}
            onClear={handleClearMemory}
          />
        </div>
      </section>

      <footer className="mt-10 border-t pt-6">
        <p className="text-xs text-muted-foreground text-center max-w-2xl mx-auto leading-relaxed">
          Mọi tin nhắn được mã hoá khi lưu. Audit log của coach KHÔNG ghi
          nội dung tin nhắn — chỉ metadata an toàn (intent, provider,
          tokens, refusal flag) để counselor + admin có thể debug khi cần.
          Khi phát hiện rủi ro nghiêm trọng, một counselor được thông báo
          trong 15 phút (SLA Phase 4).
        </p>
      </footer>
    </div>
  );
}
