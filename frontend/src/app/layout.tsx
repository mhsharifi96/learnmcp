import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Lalezar, Vazirmatn } from "next/font/google";
import { LangProvider } from "@/components/lang";
import { SiteHeader } from "@/components/site-header";
import { DEFAULT_LANG, isLang, LANG_COOKIE } from "@/lib/i18n";
import "./globals.css";

const display = Lalezar({ weight: "400", subsets: ["arabic", "latin"], variable: "--font-display", display: "swap" });
const body = Vazirmatn({ subsets: ["arabic", "latin"], variable: "--font-body", display: "swap" });

export const metadata: Metadata = {
  title: "learnmcp",
  description: "Learn your instructor's lessons with the AI you already use.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const stored = (await cookies()).get(LANG_COOKIE)?.value;
  const lang = isLang(stored) ? stored : DEFAULT_LANG;
  return (
    <html lang={lang} dir={lang === "fa" ? "rtl" : "ltr"} className={`${display.variable} ${body.variable}`}>
      <body className="min-h-screen bg-mist">
        <LangProvider lang={lang}>
          <SiteHeader />
          <main className="mx-auto w-full max-w-5xl px-4 pb-16 pt-6 sm:pt-10">{children}</main>
        </LangProvider>
      </body>
    </html>
  );
}
