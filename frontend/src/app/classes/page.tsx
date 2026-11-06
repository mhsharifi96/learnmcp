import type { Metadata } from "next";
import { jsonLd, og, publicApi, requestLang, SEO, siteUrl } from "@/lib/server";
import Classes, { type Klass } from "./classes-view";

export async function generateMetadata(): Promise<Metadata> {
  const lang = await requestLang();
  const s = SEO[lang];
  return {
    title: s.classesTitle,
    description: s.classesDescription,
    alternates: { canonical: "/classes/" },
    openGraph: og(lang, { url: "/classes/", title: s.classesTitle, description: s.classesDescription }),
    twitter: { title: s.classesTitle, description: s.classesDescription },
  };
}

export default async function Page() {
  const lang = await requestLang();
  // Public data only (no visitor cookies): renders the list on the server; the client refreshes "joined".
  const data = await publicApi<{ classes: Klass[] }>("classes");
  const classes = data?.classes ?? null;
  const url = siteUrl();
  const ld = classes && {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: SEO[lang].classesTitle,
    url: `${url}/classes/`,
    numberOfItems: classes.length,
    itemListElement: classes.map((c, i) => ({
      "@type": "ListItem",
      position: i + 1,
      url: `${url}/join/${c.code}/`,
      name: c.title,
    })),
  };
  return (
    <>
      {ld && <script type="application/ld+json" dangerouslySetInnerHTML={jsonLd(ld)} />}
      <Classes initial={classes} />
    </>
  );
}
