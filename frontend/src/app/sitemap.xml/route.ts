// Sitemap index: /sitemap.xml lists the page and course sitemaps (submit only this URL to Search Console).
import { listedClasses, newest, siteUrl, sitemapIndex, xml } from "@/lib/sitemap";

export const dynamic = "force-dynamic";

export async function GET() {
  const url = siteUrl();
  const lastmod = newest(await listedClasses());
  return xml(
    sitemapIndex([
      { loc: `${url}/sitemap-pages.xml`, lastmod },
      { loc: `${url}/sitemap-courses.xml`, lastmod },
    ]),
  );
}
