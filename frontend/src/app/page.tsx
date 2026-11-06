import type { Metadata } from "next";
import { dictionaries } from "@/lib/i18n";
import { jsonLd, og, requestLang, SEO, siteUrl } from "@/lib/server";
import Home from "./home-view";

export async function generateMetadata(): Promise<Metadata> {
  const lang = await requestLang();
  const s = SEO[lang];
  return {
    title: { absolute: s.siteTitle },
    description: s.siteDescription,
    keywords: s.keywords,
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
      {
        "@type": "FAQPage",
        "@id": `${url}/#faq`,
        inLanguage: lang,
        mainEntity: dictionaries[lang].home.faq.map(([q, a]) => ({
          "@type": "Question",
          name: q,
          acceptedAnswer: { "@type": "Answer", text: a },
        })),
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
