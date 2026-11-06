import type { Metadata } from "next";
import { og, requestLang, SEO } from "@/lib/server";
import JoinCode from "./join-code-view";

export async function generateMetadata(): Promise<Metadata> {
  const lang = await requestLang();
  const s = SEO[lang];
  return {
    title: s.joinTitle,
    description: s.joinDescription,
    alternates: { canonical: "/join/" },
    openGraph: og(lang, { url: "/join/", title: s.joinTitle, description: s.joinDescription }),
  };
}

export default function Page() {
  return <JoinCode />;
}
