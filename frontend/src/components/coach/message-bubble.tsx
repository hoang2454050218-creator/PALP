"use client";

import { AlertTriangle, ShieldCheck, Bot, User as UserIcon } from "lucide-react";

import type { CoachTurnPayload } from "./types";

interface Props {
  turn: CoachTurnPayload;
}

function timestamp(value: string): string {
  try {
    const d = new Date(value);
    return d.toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export function CoachMessageBubble({ turn }: Props) {
  const isStudent = turn.role === "student";

  if (turn.emergency_triggered) {
    return (
      <article
        aria-label="Tin nhắn khẩn cấp từ coach"
        className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4"
      >
        <header className="flex items-center gap-2 mb-2">
          <AlertTriangle
            className="h-4 w-4 text-amber-700 dark:text-amber-300"
            aria-hidden="true"
          />
          <span className="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">
            Trợ giúp khẩn cấp
          </span>
        </header>
        <p className="text-sm whitespace-pre-line leading-relaxed">
          {turn.content}
        </p>
        <p className="text-[11px] text-muted-foreground mt-3">
          {timestamp(turn.created_at)} · counselor đã được thông báo
        </p>
      </article>
    );
  }

  if (turn.refusal_triggered) {
    return (
      <article
        aria-label="Tin nhắn từ coach (đã từ chối)"
        className="rounded-lg border border-border/60 bg-muted/40 p-4"
      >
        <header className="flex items-center gap-2 mb-2">
          <ShieldCheck
            className="h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Coach từ chối
          </span>
        </header>
        <p className="text-sm whitespace-pre-line leading-relaxed">
          {turn.content}
        </p>
        <p className="text-[11px] text-muted-foreground mt-3">
          {timestamp(turn.created_at)} · safety filter
        </p>
      </article>
    );
  }

  return (
    <article
      aria-label={isStudent ? "Tin nhắn của bạn" : "Tin nhắn từ coach"}
      className={`flex gap-3 ${isStudent ? "flex-row-reverse" : "flex-row"}`}
    >
      <span
        className={`mt-1 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
          isStudent
            ? "bg-primary/15 text-primary"
            : "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
        }`}
        aria-hidden="true"
      >
        {isStudent ? (
          <UserIcon className="h-3.5 w-3.5" />
        ) : (
          <Bot className="h-3.5 w-3.5" />
        )}
      </span>
      <div
        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm leading-relaxed whitespace-pre-line ${
          isStudent
            ? "bg-primary text-primary-foreground"
            : "bg-card border"
        }`}
      >
        {turn.content}
        <p
          className={`text-[10px] mt-1 ${
            isStudent
              ? "text-primary-foreground/70"
              : "text-muted-foreground"
          }`}
        >
          {timestamp(turn.created_at)}
          {!isStudent && turn.llm_provider
            ? ` · ${turn.llm_provider}`
            : ""}
        </p>
      </div>
    </article>
  );
}
