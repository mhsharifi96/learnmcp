import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/server";

export const dynamic = "force-dynamic";

export default function robots(): MetadataRoute.Robots {
  const url = siteUrl();
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Private or per-student pages, the API and the MCP/prompt endpoints.
      disallow: ["/teach/", "/me/", "/study/", "/connect/", "/r/", "/s/", "/api/", "/admin/", "/verify-email/"],
    },
    sitemap: [`${url}/sitemap.xml`, `${url}/sitemap-pages.xml`, `${url}/sitemap-courses.xml`],
    host: url,
  };
}
