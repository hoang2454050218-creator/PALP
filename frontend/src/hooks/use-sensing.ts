"use client";

/**
 * Mounts the behavioural sensing SDK for the current student session.
 *
 * Tied to consent — if the student hasn't granted ``behavioral_signals``
 * the hook is a no-op (safer to be silent than to flicker tracking on/
 * off as the consent flag toggles). Designed to be mounted high in the
 * (student) route group so a single SDK instance covers the whole
 * student experience.
 */
import { useEffect, useRef } from "react";

import { initSensing, type SensingHandle } from "@/lib/sensing";

const RAW_SESSION_KEY = "palp:sensing-raw-session-id";

function ensureSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = window.sessionStorage.getItem(RAW_SESSION_KEY);
  if (!id) {
    id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2) + Date.now().toString(36);
    window.sessionStorage.setItem(RAW_SESSION_KEY, id);
  }
  return id;
}

export interface UseSensingOptions {
  userId: number | null;
  hasBehavioralSignalsConsent: boolean;
  canonicalSessionId?: string;
  enabled?: boolean;
}

export function useSensing({
  userId,
  hasBehavioralSignalsConsent,
  canonicalSessionId,
  enabled = true,
}: UseSensingOptions): {
  pendingCount: () => number;
} {
  const handleRef = useRef<SensingHandle | null>(null);

  useEffect(() => {
    if (!enabled) return;
    if (userId === null) return;
    if (!hasBehavioralSignalsConsent) return;
    if (typeof window === "undefined") return;

    const handle = initSensing({
      userId,
      rawSessionId: ensureSessionId(),
      canonicalSessionId,
      consents: { behavioralSignals: true },
    });
    handleRef.current = handle;

    return () => {
      handle.stop();
      handleRef.current = null;
    };
  }, [enabled, userId, hasBehavioralSignalsConsent, canonicalSessionId]);

  return {
    pendingCount: () => handleRef.current?.buffer.pendingCount() ?? 0,
  };
}
