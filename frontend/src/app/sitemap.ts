import type { MetadataRoute } from "next";
import { publicApi, siteUrl } from "@/lib/server";

// Built per request (with the API's 60s cache) so new listed classes appear without a rebuild.
export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const url = siteUrl();
  const data = await publicApi<{ classes: { code: string }[] }>("classes");
  return [
    { url: `${url}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${url}/classes/`, changeFrequency: "daily", priority: 0.9 },
    { url: `${url}/join/`, changeFrequency: "monthly", priority: 0.5 },
    ...(data?.classes ?? []).map((c) => ({
      url: `${url}/join/${c.code}/`,
      changeFrequency: "weekly" as const,
      priority: 0.8,
    })),
  ];
}
