"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useRef } from "react";
import { CodeForm } from "@/components/code-form";
import { HomeDemo } from "@/components/home-demo";
import { useLang, useT } from "@/components/lang";
import { Card, Icon } from "@/components/ui";

// WebGL scene is client-only and loaded after first paint; the CSS gradient covers until then.
const TwinScene = dynamic(() => import("@/components/twin-scene"), { ssr: false });

/* Adds .is-in to [data-reveal] elements once they scroll into view (CSS does the motion). */
function useReveal() {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const els = root.current?.querySelectorAll<HTMLElement>("[data-reveal]");
    if (!els?.length) return;
    if (!("IntersectionObserver" in window)) {
      els.forEach((e) => e.classList.add("is-in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((en) => {
          if (en.isIntersecting) {
            en.target.classList.add("is-in");
            io.unobserve(en.target);
          }
        }),
      { rootMargin: "0px 0px -10% 0px", threshold: 0.12 },
    );
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, []);
  return root;
}

function Eyebrow({ children, dark = false }: { children: React.ReactNode; dark?: boolean }) {
  return (
    <p
      className={`mb-3 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold tracking-wide ${
        dark ? "border-white/15 bg-white/5 text-[#9ff0e8]" : "border-turquoise/25 bg-turquoise/5 text-turquoise"
      }`}
    >
      <span className="eyebrow-dot" aria-hidden="true" />
      {children}
    </p>
  );
}

export default function Home() {
  const t = useT();
  const lang = useLang();
  const tw = t.home.twin;
  const root = useReveal();

  return (
    <div ref={root} className="space-y-20 sm:space-y-28">
      {/* ------------------------------------------------------------ hero */}
      <section className="twin-hero relative -mt-6 mx-[calc(50%-50vw)] overflow-hidden text-white sm:-mt-10">
        <div className="twin-grid absolute inset-0" aria-hidden="true" />
        <TwinScene rtl={lang === "fa"} />
        <div className="twin-fade absolute inset-0" aria-hidden="true" />

        <div className="relative mx-auto grid min-h-[640px] max-w-5xl items-center gap-10 px-4 pb-16 pt-[300px] md:min-h-[680px] md:grid-cols-2 md:py-24">
          <div className="hero-in">
            <Eyebrow dark>{tw.eyebrow}</Eyebrow>
            <h1 className="font-display text-[2.6rem] leading-[1.15] sm:text-6xl">
              <span className="twin-gradient-text block" dir="ltr" style={{ textAlign: "start" }}>
                {tw.titleA}
              </span>
              <span className="block">{tw.titleB}</span>
            </h1>
            <p className="mt-5 text-xl font-semibold text-[#cfe3ff]">{tw.sub}</p>
            <p className="mt-3 max-w-prose text-[1.05rem] text-[#a9bbd6]">{tw.lead}</p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/signup/" className="btn-glow inline-flex min-h-[48px] items-center gap-2 rounded-xl bg-saffron px-5 font-bold text-ink hover:no-underline">
                {tw.ctaTeacher}
                <span aria-hidden="true" className="arrow">
                  {lang === "fa" ? "←" : "→"}
                </span>
              </Link>
              <a href="#start" className="inline-flex min-h-[48px] items-center rounded-xl border border-white/20 bg-white/5 px-5 font-semibold text-white backdrop-blur transition-colors hover:border-white/40 hover:bg-white/10 hover:no-underline">
                {tw.ctaStudent}
              </a>
            </div>

            <dl className="mt-10 grid max-w-md grid-cols-3 gap-4 border-t border-white/10 pt-6">
              {tw.stats.map(([n, label]) => (
                <div key={label}>
                  <dt className="sr-only">{label}</dt>
                  <dd className="font-display text-3xl text-white" dir="ltr" style={{ textAlign: "start" }}>
                    {n}
                  </dd>
                  <dd className="mt-1 text-xs leading-5 text-[#8ea3c2]">{label}</dd>
                </div>
              ))}
            </dl>
          </div>

          {/* HUD readouts floating around the 3D model (decorative) */}
          <div className="pointer-events-none relative hidden h-[460px] md:block" aria-hidden="true">
            <div className="hud hud-a absolute start-0 top-6 w-56">
              <p className="hud-label">
                <span className="live-dot" /> {tw.hud.model}
              </p>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-xs text-[#8ea3c2]">{tw.hud.mastery}</span>
                <span className="font-display text-2xl tabular-nums">{lang === "fa" ? "۷۸٪" : "78%"}</span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
                <div className="hud-bar h-full w-[78%] rounded-full" />
              </div>
            </div>
            <div className="hud hud-b absolute bottom-16 end-0 w-60">
              <p className="hud-label text-[#ffd38a]">
                <Icon name="alert" className="h-3.5 w-3.5" /> {tw.hud.weak}
              </p>
              <p className="mt-1.5 text-sm font-semibold">{tw.hud.weakTopic}</p>
            </div>
            <div className="hud hud-c absolute bottom-2 start-6">
              <p className="hud-label">
                <Icon name="checkCircle" className="h-3.5 w-3.5 text-[#3fd1c7]" /> {tw.hud.sync}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------ what is it */}
      <section data-reveal className="reveal">
        <div className="max-w-3xl">
          <Eyebrow>{tw.whatEyebrow}</Eyebrow>
          <h2 className="font-display text-3xl leading-tight text-lapis sm:text-4xl">{tw.whatTitle}</h2>
          <p className="mt-4 text-lg text-quiet">{tw.whatText}</p>
        </div>
        <ol className="twin-loop relative mt-10 grid gap-5 md:grid-cols-3">
          {tw.loop.map(([title, text], i) => (
            <li key={title} className="loop-step relative rounded-2xl border border-line bg-surface p-6 shadow-sm" style={{ ["--i" as string]: i }}>
              <span className="loop-num mb-4 flex h-11 w-11 items-center justify-center rounded-xl font-display text-lg text-white">
                {(i + 1).toLocaleString(lang === "fa" ? "fa-IR" : "en")}
              </span>
              <h3 className="text-lg font-bold text-ink">{title}</h3>
              <p className="mt-1.5 text-quiet">{text}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* ------------------------------------------------------------ why */}
      <section data-reveal className="reveal">
        <div className="max-w-3xl">
          <Eyebrow>{tw.whyEyebrow}</Eyebrow>
          <h2 className="font-display text-3xl leading-tight text-lapis sm:text-4xl">{tw.whyTitle}</h2>
          <p className="mt-3 text-lg text-quiet">{tw.whyLead}</p>
        </div>
        <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tw.why.map(([icon, title, text], i) => (
            <li key={title} className="why-card group relative overflow-hidden rounded-2xl border border-line bg-surface p-6" style={{ ["--i" as string]: i }}>
              <span className="why-icon mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-lapis/5 text-lapis">
                <Icon name={icon} className="h-5 w-5" />
              </span>
              <h3 className="text-lg font-bold text-ink">{title}</h3>
              <p className="mt-1.5 text-quiet">{text}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* ------------------------------------------------------------ live demo */}
      <section data-reveal className="reveal grid items-center gap-10 md:grid-cols-[1fr_1.1fr]">
        <div>
          <Eyebrow>{tw.demoEyebrow}</Eyebrow>
          <h2 className="font-display text-3xl leading-tight text-lapis sm:text-4xl">{tw.demoTitle}</h2>
          <p className="mt-4 text-lg text-quiet">{tw.demoText}</p>
        </div>
        <HomeDemo />
      </section>

      {/* ------------------------------------------------------------ start */}
      <section id="start" data-reveal className="reveal scroll-mt-24">
        <Eyebrow>{tw.startEyebrow}</Eyebrow>
        <div className="mt-2 grid gap-5 md:grid-cols-2">
          <Card className="lift">
            <h2 className="font-display text-2xl text-lapis">{t.home.studentTitle}</h2>
            <p className="mb-4 mt-1 text-quiet">{t.home.studentText}</p>
            <CodeForm />
            <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
              <Link href="/student/signup/">{t.student.signupTitle}</Link>
              <Link href="/student/login/">{t.student.loginTitle}</Link>
              <Link href="/me/">{t.nav.me}</Link>
            </p>
          </Card>
          <Card className="lift">
            <h2 className="font-display text-2xl text-lapis">{t.home.instructorTitle}</h2>
            <p className="mb-4 mt-1 text-quiet">{t.home.instructorText}</p>
            <Link href="/signup/" className="inline-flex min-h-[44px] items-center rounded-lg bg-lapis px-4 font-semibold text-white hover:no-underline hover:brightness-110">
              {t.home.signup}
            </Link>
            <p className="mt-3 text-sm">
              {t.home.haveAccount} <Link href="/login/">{t.nav.login}</Link>
            </p>
          </Card>
        </div>
      </section>

      {/* ------------------------------------------------------------ how */}
      <section data-reveal className="reveal">
        <h2 className="mb-6 font-display text-3xl text-lapis">{t.home.how}</h2>
        <div className="grid gap-10 md:grid-cols-2">
          {(
            [
              [t.home.studentStepsTitle, t.home.studentSteps],
              [t.home.instructorStepsTitle, t.home.instructorSteps],
            ] as const
          ).map(([who, steps]) => (
            <div key={who}>
              <h3 className="mb-4 text-lg font-semibold text-turquoise">{who}</h3>
              <ol className="steps space-y-5">
                {steps.map(([title, text], i) => (
                  <li key={title} className="relative flex gap-4">
                    <span className="step-dot relative z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-lapis font-bold text-white">
                      {(i + 1).toLocaleString(lang === "fa" ? "fa-IR" : "en")}
                    </span>
                    <span>
                      <span className="font-semibold text-ink">{title}</span>
                      <p className="text-quiet">{text}</p>
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------------------ apps */}
      <section data-reveal className="reveal">
        <h2 className="font-display text-3xl text-lapis">{t.home.appsTitle}</h2>
        <p className="mb-6 mt-2 text-lg text-quiet">{t.home.appsLead}</p>
        <ul className="grid gap-4 sm:grid-cols-2">
          {t.home.apps.map(([name, text]) => (
            <li key={name} className="lift rounded-2xl border border-line bg-surface p-5">
              <h3 className="font-semibold text-ink" dir="auto">
                {name}
              </h3>
              <p className="mt-1 text-quiet">{text}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* ------------------------------------------------------------ faq */}
      <section data-reveal className="reveal">
        <h2 className="mb-6 font-display text-3xl text-lapis">{t.home.faqTitle}</h2>
        <div className="space-y-3">
          {t.home.faq.map(([q, a]) => (
            <details key={q} className="rounded-2xl border border-line bg-surface px-5 py-4">
              <summary className="flex cursor-pointer items-center justify-between gap-4 font-semibold text-ink">
                {q}
                <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-quiet" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                  <path d="m6 9 6 6 6-6" />
                </svg>
              </summary>
              <p className="mt-2 text-quiet">{a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------------------ final CTA */}
      <section data-reveal className="reveal twin-cta relative overflow-hidden rounded-3xl px-6 py-14 text-center text-white sm:px-12">
        <div className="twin-grid absolute inset-0 opacity-60" aria-hidden="true" />
        <div className="relative mx-auto max-w-2xl">
          <h2 className="font-display text-3xl leading-tight sm:text-4xl">{tw.finalTitle}</h2>
          <p className="mt-4 text-lg text-[#b8c8e0]">{tw.finalText}</p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/signup/" className="btn-glow inline-flex min-h-[48px] items-center rounded-xl bg-saffron px-6 font-bold text-ink hover:no-underline">
              {t.home.signup}
            </Link>
            <a href="#start" className="inline-flex min-h-[48px] items-center rounded-xl border border-white/20 bg-white/5 px-6 font-semibold text-white hover:border-white/40 hover:no-underline">
              {tw.ctaStudent}
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
