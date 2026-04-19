/**
 * Frustration pattern detector.
 *
 * Currently watches:
 *   - rapid_click   ≥ 5 clicks within RAPID_WINDOW_MS
 *   - rapid_backspace  ≥ 5 backspace key presses within RAPID_WINDOW_MS
 *
 * When detected, emits `frustration_signal` with an intensity score
 * scaled by how far past the trigger threshold the user got.
 *
 * Future patterns (ragequit, repeat_wrong) hook in via additional
 * `feed*()` methods called from the feature code that has the context.
 */
import type { IngestBuffer } from "./ingest-buffer";

const RAPID_WINDOW_MS = 1_500;
const RAPID_THRESHOLD = 5;

export class FrustrationDetector {
  private buffer: IngestBuffer;
  private clickTimestamps: number[] = [];
  private backspaceTimestamps: number[] = [];
  private listening = false;

  constructor(buffer: IngestBuffer) {
    this.buffer = buffer;
  }

  start(): void {
    if (this.listening || typeof window === "undefined") return;
    window.addEventListener("mousedown", this.onClick, { passive: true });
    window.addEventListener("keydown", this.onKey, { passive: true });
    this.listening = true;
  }

  stop(): void {
    if (!this.listening || typeof window === "undefined") return;
    window.removeEventListener("mousedown", this.onClick);
    window.removeEventListener("keydown", this.onKey);
    this.listening = false;
    this.clickTimestamps = [];
    this.backspaceTimestamps = [];
  }

  /** External signal that the same wrong answer was retried. */
  feedRepeatWrong(taskId: number | null): void {
    this.buffer.push({
      event_name: "frustration_signal",
      properties: {
        pattern: "repeat_wrong",
        intensity: 0.6,
        task_id: taskId,
      },
    });
  }

  /** External signal that the user abruptly left mid-task. */
  feedRagequit(taskId: number | null): void {
    this.buffer.push({
      event_name: "frustration_signal",
      properties: {
        pattern: "ragequit",
        intensity: 0.9,
        task_id: taskId,
      },
    });
  }

  private onClick = (): void => {
    this.recordTimestamp(this.clickTimestamps, "rapid_click");
  };

  private onKey = (e: KeyboardEvent): void => {
    if (e.key === "Backspace") {
      this.recordTimestamp(this.backspaceTimestamps, "rapid_backspace");
    }
  };

  private recordTimestamp(
    bucket: number[],
    pattern: "rapid_click" | "rapid_backspace",
  ): void {
    const now = Date.now();
    bucket.push(now);
    while (bucket.length && now - bucket[0]! > RAPID_WINDOW_MS) {
      bucket.shift();
    }
    if (bucket.length >= RAPID_THRESHOLD) {
      const intensity = Math.min(1, bucket.length / (RAPID_THRESHOLD * 2));
      bucket.length = 0;
      this.buffer.push({
        event_name: "frustration_signal",
        properties: {
          pattern,
          intensity,
        },
      });
    }
  }
}
