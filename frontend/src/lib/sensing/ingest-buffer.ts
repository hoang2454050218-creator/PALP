/**
 * Batched ingest queue for behavioural signals.
 *
 * Accumulates events in memory, flushes to ``POST /api/signals/ingest/``
 * either when the batch reaches `batchSize` or after `flushIntervalMs`,
 * whichever comes first. Failed flushes retain the events and retry on
 * the next tick so transient network errors don't drop signals.
 *
 * Each event gets a UUID idempotency key on push so the server can dedup
 * if the same flush happens to be resent (for example after the page
 * unload handler sends a final beacon).
 */
import { api, ApiError } from "@/lib/api";

export interface SignalEventPayload {
  event_name: string;
  properties: Record<string, unknown>;
  client_timestamp?: string;
  idempotency_key?: string;
}

export interface IngestBufferOptions {
  rawSessionId: string;
  canonicalSessionId?: string;
  batchSize?: number;
  flushIntervalMs?: number;
  endpoint?: string;
}

const DEFAULT_BATCH = 50;
const DEFAULT_FLUSH_MS = 5_000;

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  // Fallback acceptable for older browsers; not crypto-grade but
  // adequate for idempotency.
  return Math.random().toString(36).slice(2) + "-" + Date.now().toString(36);
}

export class IngestBuffer {
  private opts: Required<IngestBufferOptions>;
  private queue: SignalEventPayload[] = [];
  private timer: ReturnType<typeof setInterval> | null = null;
  private flushing = false;
  private boundUnload?: () => void;

  constructor(options: IngestBufferOptions) {
    this.opts = {
      rawSessionId: options.rawSessionId,
      canonicalSessionId: options.canonicalSessionId ?? "",
      batchSize: options.batchSize ?? DEFAULT_BATCH,
      flushIntervalMs: options.flushIntervalMs ?? DEFAULT_FLUSH_MS,
      endpoint: options.endpoint ?? "/api/signals/ingest/",
    };
  }

  push(event: Omit<SignalEventPayload, "client_timestamp" | "idempotency_key"> & {
    idempotency_key?: string;
  }): void {
    this.queue.push({
      event_name: event.event_name,
      properties: event.properties ?? {},
      client_timestamp: new Date().toISOString(),
      idempotency_key: event.idempotency_key ?? uuid(),
    });
    if (this.queue.length >= this.opts.batchSize) {
      void this.flush();
    }
  }

  start(): void {
    if (this.timer || typeof window === "undefined") return;
    this.timer = setInterval(() => void this.flush(), this.opts.flushIntervalMs);
    this.boundUnload = () => void this.flush(true);
    window.addEventListener("beforeunload", this.boundUnload);
    window.addEventListener("pagehide", this.boundUnload);
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    if (typeof window !== "undefined" && this.boundUnload) {
      window.removeEventListener("beforeunload", this.boundUnload);
      window.removeEventListener("pagehide", this.boundUnload);
      this.boundUnload = undefined;
    }
  }

  async flush(useBeacon = false): Promise<void> {
    if (this.flushing || this.queue.length === 0) return;
    this.flushing = true;

    const batch = this.queue.splice(0, this.opts.batchSize);
    const body = JSON.stringify({
      raw_session_id: this.opts.rawSessionId,
      canonical_session_id: this.opts.canonicalSessionId || undefined,
      events: batch,
    });

    try {
      if (useBeacon && typeof navigator !== "undefined" && navigator.sendBeacon) {
        const ok = navigator.sendBeacon(
          this.opts.endpoint,
          new Blob([body], { type: "application/json" }),
        );
        if (!ok) {
          // Fallback: requeue + try the regular path
          this.queue.unshift(...batch);
          await api.post(this.opts.endpoint, JSON.parse(body));
        }
      } else {
        await api.post(this.opts.endpoint, JSON.parse(body));
      }
    } catch (err) {
      // Requeue on transient errors; drop on permanent (consent revoked / 4xx)
      if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
        // 403 -> consent revoked; 400 -> bad payload. Don't loop.
        if (err.status === 403) this.stop();
      } else {
        this.queue.unshift(...batch);
      }
    } finally {
      this.flushing = false;
    }
  }

  setCanonicalSessionId(id: string): void {
    this.opts.canonicalSessionId = id;
  }

  pendingCount(): number {
    return this.queue.length;
  }
}
