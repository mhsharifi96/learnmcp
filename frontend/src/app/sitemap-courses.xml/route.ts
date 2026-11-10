// Every listed course page (/join/CODE/) with its cover image, built per request so new courses appear without a rebuild.
import { listedClasses, siteUrl, urlset, xml } from "@/lib/sitemap";

export const dynamic = "force-dynamic";

export async function GET() {
  const url = siteUrl();
  const classes = await listedClasses();
  return xml(
    urlset(
      classes.map((c) => ({
        loc: `${url}/join/${c.code}/`,
        lastmod: c.updated,
        changefreq: "weekly",
        priority: 0.8,
        image: { loc: `${url}${c.image || `/cover/${c.theme || "general"}`}`, title: c.title },
      })),
    ),
  );
}
