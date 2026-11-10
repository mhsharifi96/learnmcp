// Static public pages: home, course catalog and the join-by-code page.
import { listedClasses, newest, siteUrl, urlset, xml } from "@/lib/sitemap";

export const dynamic = "force-dynamic";

export async function GET() {
  const url = siteUrl();
  const lastmod = newest(await listedClasses());
  return xml(
    urlset([
      { loc: `${url}/`, changefreq: "weekly", priority: 1 },
      { loc: `${url}/classes/`, changefreq: "daily", priority: 0.9, lastmod },
      { loc: `${url}/join/`, changefreq: "monthly", priority: 0.4 },
    ]),
  );
}
