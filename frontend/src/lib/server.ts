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
  { siteTitle: string; siteDescription: string; keywords: string[]; classesTitle: string; classesDescription: string; joinTitle: string; joinDescription: string; notFound: string; classBy: (title: string, instructor: string) => string }
> = {
  fa: {
    keywords: [
      "آموزش با هوش مصنوعی", "معلم خصوصی هوش مصنوعی", "یادگیری با ChatGPT", "آموزش با چت جی پی تی", "Gemini", "جمینای",
      "Claude", "کلاد", "DeepSeek", "دیپ سیک", "کلاس آنلاین", "آزمون آنلاین", "آموزش زبان انگلیسی", "آیلتس",
      "آموزش رایگان", "دوره رایگان", "آموزش پایتون رایگان", "آموزش اکسل رایگان", "دوره آنلاین رایگان با مدرک",
    ],
    siteTitle: "learnmcp — معلم خصوصی هوش مصنوعی برای کلاس شما",
    siteDescription:
      "مدرس درس‌ها را می‌گذارد و شما با ChatGPT، Gemini، Claude یا DeepSeek (حتی رایگان) گفتگو می‌کنید و یاد می‌گیرید. مدرس می‌بیند کجا مشکل داشتید، نه گفتگوهایتان را.",
    classesTitle: "دوره‌های آموزشی رایگان آنلاین با هوش مصنوعی",
    classesDescription:
      "بیش از ۲۵۰ دوره آموزش رایگان آنلاین: زبان انگلیسی و آیلتس، پایتون و برنامه‌نویسی، اکسل، هوش مصنوعی، کنکور، ریاضی، بازاریابی دیجیتال و مهارت‌های شغلی. ثبت‌نام رایگان، یادگیری با ChatGPT، Gemini و Claude.",
    joinTitle: "ورود به کلاس",
    joinDescription: "کد کلاسی را که مدرس به شما داده وارد کنید و با ChatGPT، Gemini، Claude یا DeepSeek درس بخوانید.",
    notFound: "کلاس پیدا نشد",
    classBy: (title, instructor) => `کلاس «${title}» با ${instructor} در learnmcp. درس‌ها و آزمون‌ها را با هوش مصنوعی خودتان بخوانید.`,
  },
  en: {
    keywords: [
      "AI tutor", "learn with ChatGPT", "Gemini", "Claude", "DeepSeek", "online class", "AI quiz",
      "learn English with AI", "IELTS speaking practice", "teacher dashboard",
    ],
    siteTitle: "learnmcp — A private AI tutor for your class",
    siteDescription:
      "Your teacher puts the lessons here; you learn them by chatting with ChatGPT, Gemini, Claude or DeepSeek, even the free versions. Your teacher sees where you got stuck, never your chats.",
    classesTitle: "Free online courses with an AI tutor",
    classesDescription:
      "250+ free online courses: English and IELTS, Python and programming, Excel, AI, math, exam prep, digital marketing and career skills. Register free and study with ChatGPT, Gemini or Claude.",
    joinTitle: "Join a class",
    joinDescription: "Enter the class code your instructor gave you and study with ChatGPT, Gemini, Claude or DeepSeek.",
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
