/**
 * Public entry point for the behavioural-sensing SDK.
 *
 * Usage from a layout/component:
 *
 *   const session = initSensing({
 *     userId: user.id,
 *     consents: { behavioralSignals: true },
 *     rawSessionId: ensureSessionId(),
 *   });
 *   return () => session.stop();
 */
import { FocusTracker } from "./focus-tracker";
import { FrustrationDetector } from "./frustration-detector";
import { IdleDetector } from "./idle-detector";
import { IngestBuffer } from "./ingest-buffer";
import { TabSwitchTracker } from "./tab-switch-tracker";

export interface InitSensingOptions {
  userId: number;
  rawSessionId: string;
  canonicalSessionId?: string;
  consents: {
    behavioralSignals: boolean;
  };
  idleThresholdMs?: number;
}

export interface SensingHandle {
  buffer: IngestBuffer;
  trackers: {
    focus: FocusTracker;
    idle: IdleDetector;
    tabSwitch: TabSwitchTracker;
    frustration: FrustrationDetector;
  };
  setCanonicalSessionId(id: string): void;
  stop(): void;
}

const NULL_HANDLE: SensingHandle = {
  buffer: new IngestBuffer({ rawSessionId: "noop" }),
  trackers: {
    focus: new FocusTracker(new IngestBuffer({ rawSessionId: "noop" })),
    idle: new IdleDetector(new IngestBuffer({ rawSessionId: "noop" })),
    tabSwitch: new TabSwitchTracker(new IngestBuffer({ rawSessionId: "noop" })),
    frustration: new FrustrationDetector(new IngestBuffer({ rawSessionId: "noop" })),
  },
  setCanonicalSessionId() {},
  stop() {},
};

export function initSensing(opts: InitSensingOptions): SensingHandle {
  if (!opts.consents.behavioralSignals) {
    return NULL_HANDLE;
  }
  if (typeof window === "undefined") {
    // SSR-safe no-op
    return NULL_HANDLE;
  }

  const buffer = new IngestBuffer({
    rawSessionId: opts.rawSessionId,
    canonicalSessionId: opts.canonicalSessionId,
  });
  const focus = new FocusTracker(buffer);
  const idle = new IdleDetector(buffer, { thresholdMs: opts.idleThresholdMs });
  const tabSwitch = new TabSwitchTracker(buffer);
  const frustration = new FrustrationDetector(buffer);

  buffer.start();
  focus.start();
  idle.start();
  tabSwitch.start();
  frustration.start();

  return {
    buffer,
    trackers: { focus, idle, tabSwitch, frustration },
    setCanonicalSessionId(id) {
      buffer.setCanonicalSessionId(id);
    },
    stop() {
      focus.stop();
      idle.stop();
      tabSwitch.stop();
      frustration.stop();
      buffer.stop();
    },
  };
}

export type { IngestBuffer, SignalEventPayload } from "./ingest-buffer";
export { FocusTracker } from "./focus-tracker";
export { IdleDetector } from "./idle-detector";
export { TabSwitchTracker } from "./tab-switch-tracker";
export { FrustrationDetector } from "./frustration-detector";
