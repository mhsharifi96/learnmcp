// Server-only XML builders for the sitemap index and its child sitemaps (sitemaps.org protocol + image extension).
import { publicApi, siteUrl } from "@/lib/server";

export type SitemapClass = { code: string; title: string; updated?: string; image?: string | null; theme?: string };

const esc = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");

export async function listedClasses(): Promise<SitemapClass[]> {
  const data = await publicApi<{ classes: SitemapClass[] }>("classes");
  return data?.classes ?? [];
}

/** Newest `updated` date among the classes, or undefined. */
export function newest(classes: SitemapClass[]): string | undefined {
  return classes.map((c) => c.updated).filter((d): d is string => !!d).sort().pop();
}

type Entry = { loc: string; lastmod?: string; changefreq?: string; priority?: number; image?: { loc: string; title: string } };

export function urlset(entries: Entry[]): string {
  const body = entries
    .map((e) =>
      [
        "<url>",
        `<loc>${esc(e.loc)}</loc>`,
        e.lastmod && `<lastmod>${esc(e.lastmod)}</lastmod>`,
        e.changefreq && `<changefreq>${e.changefreq}</changefreq>`,
        e.priority !== undefined && `<priority>${e.priority.toFixed(1)}</priority>`,
        e.image && `<image:image><image:loc>${esc(e.image.loc)}</image:loc><image:title>${esc(e.image.title)}</image:title></image:image>`,
        "</url>",
      ]
        .filter(Boolean)
        .join(""),
    )
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n${body}\n</urlset>\n`;
}

export function sitemapIndex(maps: { loc: string; lastmod?: string }[]): string {
  const body = maps
    .map((m) => `<sitemap><loc>${esc(m.loc)}</loc>${m.lastmod ? `<lastmod>${esc(m.lastmod)}</lastmod>` : ""}</sitemap>`)
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</sitemapindex>\n`;
}

export function xml(body: string): Response {
  return new Response(body, {
    headers: { "Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, max-age=300, s-maxage=600" },
  });
}

export { siteUrl };
