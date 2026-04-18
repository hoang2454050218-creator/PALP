"use client";

import { useEffect } from "react";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import type { WellbeingCheckResponse } from "@/types";

const STORAGE_KEY = "palp:study-session-start";
const PING_INTERVAL_MS = 5 * 60 * 1000;
const TOAST_DEDUP_KEY = "palp:wellbeing-last-nudge-id";

/**
 * Tracks how long the student has been continuously on a study page and pings
 * `/api/wellbeing/check/` every 5 minutes so the backend can decide whether to
 * surface a "take a break" nudge. The session start timestamp is persisted in
 * localStorage so brief navigations within the app (dashboard ↔ task) do not
 * reset the counter and cause spurious nudges.
 *
 * Caller controls activation via the `enabled` flag (typically `pathname ===
 * "/task"`). Disabling automatically clears the persisted timestamp so a fresh
 * study session starts next time.
 */
export function useStudySessionPing(enabled: boolean) {
  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;

    const stored = window.localStorage.getItem(STORAGE_KEY);
    const sessionStart = stored ? Number(stored) : Date.now();
    if (!stored) window.localStorage.setItem(STORAGE_KEY, String(sessionStart));

    let cancelled = false;

    const ping = async () => {
      const minutes = Math.max(0, Math.floor((Date.now() - sessionStart) / 60000));
      try {
        const res = await api.post<WellbeingCheckResponse>("/wellbeing/check/", {
          continuous_minutes: minutes,
        });
        if (cancelled || !res.should_nudge || !res.nudge) return;
        const seen = window.localStorage.getItem(TOAST_DEDUP_KEY);
        if (seen === String(res.nudge.id)) return;
        window.localStorage.setItem(TOAST_DEDUP_KEY, String(res.nudge.id));
        toast({
          variant: "info",
          title: "Hãy nghỉ giải lao một chút nhé",
          description: res.message ?? "Bạn đã học liên tục khá lâu. Đứng dậy vươn vai 5 phút sẽ giúp tỉnh táo hơn.",
          action: {
            label: "Xem chi tiết",
            onClick: () => {
              window.location.href = "/wellbeing";
            },
          },
        });
      } catch (err) {
        if (err instanceof ApiError && err.isUnauthorized()) return;
        // Silent fail otherwise - wellbeing nudges shouldn't block learning.
      }
    };

    const interval = window.setInterval(ping, PING_INTERVAL_MS);
    // Trigger immediately so a long-running tab gets a check even before the
    // first 5-minute boundary.
    ping();

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [enabled]);

  useEffect(() => {
    if (enabled || typeof window === "undefined") return;
    window.localStorage.removeItem(STORAGE_KEY);
    window.localStorage.removeItem(TOAST_DEDUP_KEY);
  }, [enabled]);
}
