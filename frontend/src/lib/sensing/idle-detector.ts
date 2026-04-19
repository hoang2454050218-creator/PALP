/**
 * Idle detector.
 *
 * Mouse + keyboard inactivity beyond `thresholdMs` produces an
 * `idle_started` event; the next user input emits `idle_ended` carrying
 * the actual idle duration. The threshold defaults to 5s but can be
 * overridden so the same component is testable with short timeouts.
 */
import type { IngestBuffer } from "./ingest-buffer";

const ACTIVITY_EVENTS = ["mousemove", "mousedown", "keydown", "scroll", "touchstart"] as const;

export interface IdleDetectorOptions {
  thresholdMs?: number;
}

export class IdleDetector {
  private buffer: IngestBuffer;
  private threshold: number;
  private idleSince: number | null = null;
  private lastActivity = Date.now();
  private timer: ReturnType<typeof setTimeout> | null = null;
  private listening = false;

  constructor(buffer: IngestBuffer, options: IdleDetectorOptions = {}) {
    this.buffer = buffer;
    this.threshold = options.thresholdMs ?? 5_000;
  }

  start(): void {
    if (this.listening || typeof window === "undefined") return;
    for (const evt of ACTIVITY_EVENTS) {
      window.addEventListener(evt, this.onActivity, { passive: true });
    }
    this.listening = true;
    this.scheduleCheck();
  }

  stop(): void {
    if (!this.listening || typeof window === "undefined") return;
    for (const evt of ACTIVITY_EVENTS) {
      window.removeEventListener(evt, this.onActivity);
    }
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.listening = false;
    this.idleSince = null;
  }

  private onActivity = (): void => {
    const now = Date.now();
    if (this.idleSince !== null) {
      this.buffer.push({
        event_name: "idle_ended",
        properties: {
          idle_duration_ms: now - this.idleSince,
          url_path: window.location.pathname,
        },
      });
      this.idleSince = null;
    }
    this.lastActivity = now;
    this.scheduleCheck();
  };

  private scheduleCheck(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(this.checkIdle, this.threshold);
  }

  private checkIdle = (): void => {
    if (Date.now() - this.lastActivity < this.threshold) {
      this.scheduleCheck();
      return;
    }
    if (this.idleSince === null) {
      this.idleSince = Date.now();
      this.buffer.push({
        event_name: "idle_started",
        properties: {
          idle_duration_ms: this.threshold,
          url_path: window.location.pathname,
        },
      });
    }
    // Re-check periodically in case the user never comes back; this keeps
    // the rollup honest even for very long idle stretches.
    this.scheduleCheck();
  };
}
