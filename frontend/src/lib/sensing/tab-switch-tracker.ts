/**
 * Tab switch tracker.
 *
 * Lightweight subset of FocusTracker — counts only the discrete event
 * of the page becoming hidden via tab switch. Useful as a low-cost
 * signal even when the rest of the sensing SDK is paused.
 */
import type { IngestBuffer } from "./ingest-buffer";

export class TabSwitchTracker {
  private buffer: IngestBuffer;
  private listening = false;

  constructor(buffer: IngestBuffer) {
    this.buffer = buffer;
  }

  start(): void {
    if (this.listening || typeof document === "undefined") return;
    document.addEventListener("visibilitychange", this.onChange);
    this.listening = true;
  }

  stop(): void {
    if (!this.listening || typeof document === "undefined") return;
    document.removeEventListener("visibilitychange", this.onChange);
    this.listening = false;
  }

  private onChange = (): void => {
    if (document.visibilityState !== "hidden") return;
    this.buffer.push({
      event_name: "tab_switched",
      properties: {
        current_url_path: window.location.pathname,
        task_in_progress: window.location.pathname.startsWith("/task"),
      },
    });
  };
}
