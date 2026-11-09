import type { Metadata } from "next";
import { cache } from "react";
import { clip, jsonLd, og, publicApi, requestLang, SEO, siteUrl } from "@/lib/server";
import Join, { type PublicClass } from "./join-view";

type Params = Promise<{ code: string }>;

const loadClass = cache(async (code: string) => {
  const c = await publicApi<PublicClass>(`classes/${encodeURIComponent(code)}`);
  if (!c) return null;
  // Only the public fields: never pass visitor-specific data from a cookie-less server fetch.
  return {
    code: c.code,
    title: c.title,
    description: c.description,
    instructor: c.instructor,
    listed: c.listed !== false,
    lessons: c.listed !== false && Array.isArray(c.lessons) ? c.lessons : [],
    requires_approval: !!c.requires_approval,
    quizzes: c.quizzes ?? 0,
    image: c.image ?? null,
    theme: c.theme ?? "general",
  } satisfies PublicClass;
});

/** Absolute URL of the class cover for previews: the uploaded photo, or the automatic PNG cover. */
function coverUrl(c: PublicClass): string {
  return `${siteUrl()}${c.image || `/cover/${c.theme || "general"}`}`;
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { code } = await params;
  const lang = await requestLang();
  const s = SEO[lang];
  const c = await loadClass(code);
  if (!c) return { title: s.notFound, robots: { index: false, follow: true } };
  const path = `/join/${c.code}/`;
  const description = clip(c.description || s.classBy(c.title, c.instructor));
  return {
    title: c.title,
    description,
    keywords: [c.title, ...c.title.split(/[\s:،,–-]+/).filter((w) => w.length > 2), ...s.keywords.slice(-5)],
    alternates: { canonical: path },
    // Unlisted classes are only for people with the code: keep them out of search results.
    robots: c.listed ? undefined : { index: false, follow: false },
    authors: [{ name: c.instructor }],
    openGraph: { ...og(lang, { url: path, title: c.title, description }), images: [{ url: coverUrl(c), width: 1200, height: 630, alt: c.title }] },
    twitter: { card: "summary_large_image", title: c.title, description, images: [coverUrl(c)] },
  };
}

export default async function Page({ params }: { params: Params }) {
  const { code } = await params;
  const lang = await requestLang();
  const c = await loadClass(code);
  const url = siteUrl();
  const ld = c?.listed && {
    "@context": "https://schema.org",
    "@type": "Course",
    "@id": `${url}/join/${c.code}/#course`,
    name: c.title,
    description: clip(c.description || SEO[lang].classBy(c.title, c.instructor), 500),
    url: `${url}/join/${c.code}/`,
    courseCode: c.code,
    inLanguage: lang,
    isAccessibleForFree: true,
    offers: { "@type": "Offer", category: "Free", price: 0, priceCurrency: "USD", availability: "https://schema.org/InStock" },
    provider: { "@type": "Organization", name: "learnmcp", sameAs: `${url}/` },
    author: { "@type": "Person", name: c.instructor },
    image: coverUrl(c),
    hasCourseInstance: {
      "@type": "CourseInstance",
      courseMode: "Online",
      courseWorkload: `PT${Math.max(1, c.lessons.length)}H`,
      instructor: { "@type": "Person", name: c.instructor },
    },
    ...(c.lessons.length
      ? { syllabusSections: c.lessons.map((l) => ({ "@type": "Syllabus", name: l.title, position: l.order })) }
      : {}),
  };
  const crumbs = c?.listed && {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "learnmcp", item: `${url}/` },
      { "@type": "ListItem", position: 2, name: SEO[lang].classesTitle, item: `${url}/classes/` },
      { "@type": "ListItem", position: 3, name: c.title, item: `${url}/join/${c.code}/` },
    ],
  };
  return (
    <>
      {ld && <script type="application/ld+json" dangerouslySetInnerHTML={jsonLd(ld)} />}
      {crumbs && <script type="application/ld+json" dangerouslySetInnerHTML={jsonLd(crumbs)} />}
      <Join initial={c} />
    </>
  );
}
