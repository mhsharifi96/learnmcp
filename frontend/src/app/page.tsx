import type { Metadata } from "next";
import { jsonLd, og, requestLang, SEO, siteUrl } from "@/lib/server";
import Home from "./home-view";

export async function generateMetadata(): Promise<Metadata> {
  const lang = await requestLang();
  const s = SEO[lang];
  return {
    title: { absolute: s.siteTitle },
    description: s.siteDescription,
    alternates: { canonical: "/" },
    openGraph: og(lang, { url: "/", title: s.siteTitle, description: s.siteDescription }),
  };
}

export default async function Page() {
  const lang = await requestLang();
  const url = siteUrl();
  const data = {
    "@context": "https://schema.org",
    "@graph": [
      { "@type": "Organization", "@id": `${url}/#org`, name: "learnmcp", url: `${url}/` },
      {
        "@type": "WebSite",
        "@id": `${url}/#website`,
        name: "learnmcp",
        url: `${url}/`,
        description: SEO[lang].siteDescription,
        inLanguage: lang,
        publisher: { "@id": `${url}/#org` },
      },
    ],
  };
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={jsonLd(data)} />
      <Home />
    </>
  );
}
