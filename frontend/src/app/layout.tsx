import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Vazirmatn } from "next/font/google";
import Script from "next/script";
import { LangProvider } from "@/components/lang";
import { SiteHeader } from "@/components/site-header";
import { DEFAULT_LANG, isLang, LANG_COOKIE } from "@/lib/i18n";
import { OG_LOCALE, requestLang, SEO, siteUrl } from "@/lib/server";
import "./globals.css";

// Vazirmatn (Vazir) for Persian and Latin text, body and headings alike.
const body = Vazirmatn({ subsets: ["arabic", "latin"], variable: "--font-body", display: "swap" });

// Google Tag Manager container.
const GTM_ID = "GTM-ND58R3JM";

// Site-wide defaults; public pages add their own title, description and canonical URL.
export async function generateMetadata(): Promise<Metadata> {
  const lang = await requestLang();
  const s = SEO[lang];
  return {
    metadataBase: new URL(siteUrl()),
    applicationName: "learnmcp",
    title: { default: s.siteTitle, template: "%s | learnmcp" },
    description: s.siteDescription,
    openGraph: { type: "website", siteName: "learnmcp", locale: OG_LOCALE[lang], title: s.siteTitle, description: s.siteDescription },
    twitter: { card: "summary", title: s.siteTitle, description: s.siteDescription },
    formatDetection: { telephone: false, email: false, address: false },
  };
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const stored = (await cookies()).get(LANG_COOKIE)?.value;
  const lang = isLang(stored) ? stored : DEFAULT_LANG;
  return (
    <html lang={lang} dir={lang === "fa" ? "rtl" : "ltr"} className={body.variable}>
      <body className="min-h-screen bg-mist">
        <Script id="gtm-init" strategy="afterInteractive">
          {`window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
window.dataLayer.push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });`}
        </Script>
        <Script id="gtm" strategy="afterInteractive" src={`https://www.googletagmanager.com/gtm.js?id=${GTM_ID}`} />
        <noscript>
          <iframe
            src={`https://www.googletagmanager.com/ns.html?id=${GTM_ID}`}
            height="0"
            width="0"
            style={{ display: "none", visibility: "hidden" }}
          />
        </noscript>
        <LangProvider lang={lang}>
          <SiteHeader />
          <main className="mx-auto w-full max-w-5xl px-4 pb-16 pt-6 sm:pt-10">{children}</main>
        </LangProvider>
      </body>
    </html>
  );
}
