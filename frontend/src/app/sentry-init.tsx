"use client";

import { useEffect } from "react";

/**
 * Lazy Sentry RUM init -- only loads the SDK when ``NEXT_PUBLIC_SENTRY_DSN``
 * is set (see docs/POST_PILOT_ROADMAP.md item 7). Keeps the bundle small
 * for pilot deployment that doesn't have a Sentry account yet.
 *
 * The SDK is added to package.json after the first time we have a DSN; until
 * then this file dynamic-imports an optional module and silently no-ops.
 */
export function SentryInit() {
  useEffect(() => {
    const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
    if (!dsn) return;

    // Dynamic import using a string variable so the bundler doesn't try to
    // resolve the optional module at build time.
    const sentryModule = "@sentry/nextjs";
    (new Function("m", "return import(m)"))(sentryModule)
      .then((Sentry: any) => {
        Sentry.init({
          dsn,
          environment: process.env.NEXT_PUBLIC_SENTRY_ENV || "development",
          release: process.env.NEXT_PUBLIC_APP_VERSION,
          tracesSampleRate: 0.3,
          replaysSessionSampleRate: 0.1,
          replaysOnErrorSampleRate: 1.0,
          // Privacy-first: never capture PII automatically.
          sendDefaultPii: false,
          beforeSend(event: any) {
            if (event.request?.cookies) delete event.request.cookies;
            if (event.user) {
              delete event.user.email;
              delete event.user.ip_address;
              delete event.user.username;
            }
            return event;
          },
        });
      })
      .catch(() => {
        // SDK not installed yet -- normal in dev. See POST_PILOT_ROADMAP.md.
      });
  }, []);

  return null;
}
