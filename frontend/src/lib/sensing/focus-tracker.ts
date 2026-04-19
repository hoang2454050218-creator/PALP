/**
 * Focus / blur tracker.
 *
 * Wraps the Page Visibility API + window focus events. Emits:
 *   - `focus_lost`  whenever the tab becomes hidden or window blurs and
 *                   the user stays away for >= MIN_AWAY_MS.
 *   - `focus_gained` when they return.
 *
 * Each tracker is meant to live for the lifetime of one student session.
 * `start()` is idempotent; `stop()` always clears listeners + timers.
 */
import type { IngestBuffer } from "./ingest-buffer";

const MIN_AWAY_MS = 2_000;

export class FocusTracker {
  private buffer: IngestBuffer;
  private awayStart: number | null = null;
  private listening = false;

  constructor(buffer: IngestBuffer) {
    this.buffer = buffer;
  }

  start(): void {
    if (this.listening || typeof document === "undefined") return;
    document.addEventListener("visibilitychange", this.onVisibilityChange);
    window.addEventListener("blur", this.onBlur);
    window.addEventListener("focus", this.onFocus);
    this.listening = true;
  }

  stop(): void {
    if (!this.listening || typeof document === "undefined") return;
    document.removeEventListener("visibilitychange", this.onVisibilityChange);
    window.removeEventListener("blur", this.onBlur);
    window.removeEventListener("focus", this.onFocus);
    this.listening = false;
    this.awayStart = null;
  }

  private onVisibilityChange = (): void => {
    if (document.visibilityState === "hidden") {
      this.markAway("visibility_hidden");
    } else {
      this.markBack();
    }
  };

  private onBlur = (): void => this.markAway("window_blur");
  private onFocus = (): void => this.markBack();

  private markAway(trigger: "visibility_hidden" | "window_blur" | "tab_switch"): void {
    if (this.awayStart !== null) return;
    this.awayStart = Date.now();
    // Defer the actual emission until we come back so we know the duration.
    // Persist trigger via a closure for the next markBack call.
    this._lastTrigger = trigger;
  }

  private _lastTrigger: "visibility_hidden" | "window_blur" | "tab_switch" =
    "visibility_hidden";

  private markBack(): void {
    if (this.awayStart === null) return;
    const awayDuration = Date.now() - this.awayStart;
    this.awayStart = null;
    if (awayDuration < MIN_AWAY_MS) return;

    this.buffer.push({
      event_name: "focus_lost",
      properties: {
        focus_duration_ms: awayDuration,
        trigger: this._lastTrigger,
        url_path: typeof window !== "undefined" ? window.location.pathname : "",
      },
    });
    this.buffer.push({
      event_name: "focus_gained",
      properties: {
        away_duration_ms: awayDuration,
        url_path: typeof window !== "undefined" ? window.location.pathname : "",
      },
    });
  }
}
