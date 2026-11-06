// Server-only helpers for SEO: public site URL, request language and read-only fetches of public API data.
// Import only from server components, generateMetadata, sitemap.ts and robots.ts.
import { cookies } from "next/headers";
import { DEFAULT_LANG, isLang, LANG_COOKIE, type Lang } from "@/lib/i18n";

/** Public origin used for canonical URLs, Open Graph and the sitemap, e.g. https://learn.example.com */
export function siteUrl(): string {
  return (process.env.SITE_URL || process.env.PUBLIC_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");
}

/** Django origin reachable from the Next.js server (in compose: http://web:8000). */
function internalApi(): string {
  return (process.env.INTERNAL_API_URL || process.env.DJANGO_ORIGIN || "http://127.0.0.1:8000").replace(/\/+$/, "");
}

export async function requestLang(): Promise<Lang> {
  const stored = (await cookies()).get(LANG_COOKIE)?.value;
  return isLang(stored) ? stored : DEFAULT_LANG;
}

/** GET a public API path without the visitor's cookies. Returns null on 404 or when the API is unreachable. */
export async function publicApi<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${internalApi()}/api/${path}`, {
      headers: { Accept: "application/json", "X-Forwarded-Proto": "https" },
      next: { revalidate: 60 },
      signal: AbortSignal.timeout(4000),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

/** Serialise JSON-LD safely for a <script> tag. */
export function jsonLd(data: unknown): { __html: string } {
  return { __html: JSON.stringify(data).replace(/</g, "\\u003c") };
}

export const OG_LOCALE: Record<Lang, string> = { fa: "fa_IR", en: "en_US" };

/** Open Graph for one page. Next replaces (not merges) the layout's openGraph, so repeat the site fields. */
export function og(lang: Lang, page: { url: string; title: string; description: string }) {
  return { type: "website" as const, siteName: "learnmcp", locale: OG_LOCALE[lang], ...page };
}

export const SEO: Record<
  Lang,
  { siteTitle: string; siteDescription: string; classesTitle: string; classesDescription: string; joinTitle: string; joinDescription: string; notFound: string; classBy: (title: string, instructor: string) => string }
> = {
  fa: {
    siteTitle: "learnmcp — با همان هوش مصنوعی خودت یاد بگیر",
    siteDescription:
      "مدرس درس و آزمون را می‌سازد؛ شما در Claude یا ChatGPT (حتی نسخهٔ رایگان) آن را می‌خوانید. مدرس پیشرفت شما را می‌بیند، نه گفتگوهایتان را.",
    classesTitle: "همهٔ کلاس‌ها",
    classesDescription:
      "فهرست کلاس‌های آنلاین learnmcp: برنامه‌نویسی، ریاضی، زبان انگلیسی، آمادگی کنکور و مصاحبه و بیشتر. با هوش مصنوعی خودتان درس بخوانید و آزمون بدهید.",
    joinTitle: "ورود به کلاس",
    joinDescription: "کد کلاسی را که مدرس به شما داده وارد کنید و با Claude یا ChatGPT درس بخوانید.",
    notFound: "کلاس پیدا نشد",
    classBy: (title, instructor) => `کلاس «${title}» با ${instructor} در learnmcp. درس‌ها و آزمون‌ها را با هوش مصنوعی خودتان بخوانید.`,
  },
  en: {
    siteTitle: "learnmcp — Learn with the AI you already use",
    siteDescription:
      "Your instructor writes the lessons and quizzes. You study them in Claude or ChatGPT, even on a free plan. Your instructor sees your progress, never your conversations.",
    classesTitle: "All classes",
    classesDescription:
      "Online classes on learnmcp: programming, math, English, exam and interview prep and more. Study lessons and take quizzes with the AI you already use.",
    joinTitle: "Join a class",
    joinDescription: "Enter the class code your instructor gave you and study with Claude or ChatGPT.",
    notFound: "Class not found",
    classBy: (title, instructor) => `“${title}” by ${instructor} on learnmcp. Study the lessons and quizzes with your own AI.`,
  },
};

/** Trim text to a meta-description length on a word boundary. */
export function clip(text: string, max = 160): string {
  const flat = text.replace(/\s+/g, " ").trim();
  if (flat.length <= max) return flat;
  const cut = flat.slice(0, max - 1);
  return cut.slice(0, cut.lastIndexOf(" ") > 80 ? cut.lastIndexOf(" ") : cut.length) + "…";
}
