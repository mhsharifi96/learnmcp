import type { MetadataRoute } from "next";
import { publicApi, siteUrl } from "@/lib/server";

// Built per request (with the API's 60s cache) so new listed classes appear without a rebuild.
export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const url = siteUrl();
  const data = await publicApi<{ classes: { code: string; updated?: string; image?: string | null; theme?: string }[] }>("classes");
  const classes = data?.classes ?? [];
  const newest = classes.map((c) => c.updated).filter(Boolean).sort().pop();
  return [
    { url: `${url}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${url}/classes/`, changeFrequency: "daily", priority: 0.9, ...(newest ? { lastModified: newest } : {}) },
    { url: `${url}/join/`, changeFrequency: "monthly", priority: 0.4 },
    ...classes.map((c) => ({
      url: `${url}/join/${c.code}/`,
      changeFrequency: "weekly" as const,
      priority: 0.8,
      ...(c.updated ? { lastModified: c.updated } : {}),
      images: [`${url}${c.image || `/cover/${c.theme || "general"}`}`],
    })),
  ];
}
