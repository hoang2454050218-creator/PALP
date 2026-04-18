/** @type {import('next').NextConfig} */
//
// Rewrites pipe /api/* to the backend service (resolved via the
// BACKEND_INTERNAL_URL env var when running in Docker, falling back to a
// localhost port for bare-metal `npm run dev`). This keeps the browser on a
// single origin so the CSP can stay simple ("connect-src 'self'") and we
// avoid the trailing-slash CSP gotcha that previously broke login.
const BACKEND_INTERNAL_URL =
  process.env.BACKEND_INTERNAL_URL || "http://backend:8000";
const FALLBACK_LOCAL_BACKEND = process.env.LOCAL_BACKEND_URL || "http://localhost:8000";

const nextConfig = {
  output: "standalone",
  // Django enforces trailing slashes on all API paths (APPEND_SLASH=True).
  // ``skipTrailingSlashRedirect`` keeps the slash on the incoming request,
  // and the explicit ``/api/:path*/`` rewrite ensures the slash survives
  // the proxy hop -- otherwise Next.js drops it on the way to the backend.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backend = BACKEND_INTERNAL_URL || FALLBACK_LOCAL_BACKEND;
    return [
      {
        source: "/api/:path*/",
        destination: `${backend}/api/:path*/`,
      },
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
    ];
  },
  async headers() {
    const extraConnect = process.env.NEXT_PUBLIC_API_URL?.startsWith("http")
      ? ` ${new URL(process.env.NEXT_PUBLIC_API_URL).origin}`
      : "";
    // Sentry RUM ingest endpoint when DSN is set; ignored otherwise.
    let sentryConnect = "";
    let sentryImg = "";
    if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
      try {
        const sentryHost = new URL(process.env.NEXT_PUBLIC_SENTRY_DSN).host;
        sentryConnect = ` https://${sentryHost}`;
        sentryImg = ` https://${sentryHost}`;
      } catch {
        /* malformed DSN -- skip */
      }
    }
    // OpenDyslexic font served from jsdelivr when the user opts in via /preferences.
    const fontHosts = " https://cdn.jsdelivr.net";
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              `connect-src 'self'${extraConnect}${sentryConnect}`,
              `img-src 'self' data: blob:${sentryImg}`,
              `font-src 'self' data:${fontHosts}`,
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains; preload",
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
