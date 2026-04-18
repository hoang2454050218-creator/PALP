import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://palp.dau.edu.vn";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        // Authenticated areas should not surface in search results - allow only
        // the public landing pages (root + login). Everything else is gated by
        // backend auth and would be 401 anyway, but explicit disallow keeps
        // crawlers from wasting budget on unreachable content.
        allow: ["/", "/login"],
        disallow: [
          "/api/",
          "/dashboard",
          "/pathway",
          "/task",
          "/assessment",
          "/wellbeing",
          "/privacy",
          "/preferences",
          "/overview",
          "/alerts",
          "/knowledge-graph",
          "/history",
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
