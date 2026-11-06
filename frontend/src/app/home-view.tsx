"use client";

import Link from "next/link";
import { CodeForm } from "@/components/code-form";
import { HomeDemo } from "@/components/home-demo";
import { useT } from "@/components/lang";
import { Card } from "@/components/ui";

export default function Home() {
  const t = useT();
  return (
    <div className="space-y-10">
      <section className="grid items-center gap-8 md:grid-cols-[1.1fr_1fr]">
        <div>
          <h1 className="font-display text-4xl leading-[1.25] text-lapis sm:text-5xl">{t.home.title}</h1>
          <p className="mt-4 max-w-prose text-lg text-quiet">{t.home.lead}</p>
        </div>
        <HomeDemo />
      </section>

      <div className="stagger grid gap-5 md:grid-cols-2">
        <Card>
          <h2 className="font-display text-2xl text-lapis">{t.home.studentTitle}</h2>
          <p className="mb-4 mt-1 text-quiet">{t.home.studentText}</p>
          <CodeForm />
          <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
            <Link href="/student/signup/">{t.student.signupTitle}</Link>
            <Link href="/student/login/">{t.student.loginTitle}</Link>
            <Link href="/me/">{t.nav.me}</Link>
          </p>
        </Card>
        <Card>
          <h2 className="font-display text-2xl text-lapis">{t.home.instructorTitle}</h2>
          <p className="mb-4 mt-1 text-quiet">{t.home.instructorText}</p>
          <Link
            href="/signup/"
            className="inline-flex rounded-lg bg-lapis px-4 py-2 font-semibold text-white hover:no-underline hover:brightness-110"
          >
            {t.home.signup}
          </Link>
          <p className="mt-3 text-sm">
            {t.home.haveAccount} <Link href="/login/">{t.nav.login}</Link>
          </p>
        </Card>
      </div>

      <section>
        <h2 className="mb-4 font-display text-2xl text-lapis">{t.home.whatTitle}</h2>
        <ul className="stagger grid gap-4 sm:grid-cols-3">
          {t.home.what.map(([title, text]) => (
            <li key={title} className="rounded-xl border border-line bg-surface p-4">
              <h3 className="font-semibold text-ink">{title}</h3>
              <p className="mt-1 text-quiet">{text}</p>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-4 font-display text-2xl text-lapis">{t.home.how}</h2>
        <div className="grid gap-8 md:grid-cols-2">
          {(
            [
              [t.home.studentStepsTitle, t.home.studentSteps],
              [t.home.instructorStepsTitle, t.home.instructorSteps],
            ] as const
          ).map(([who, steps]) => (
            <div key={who}>
              <h3 className="mb-3 text-lg font-semibold text-turquoise">{who}</h3>
              <ol className="space-y-4">
                {steps.map(([title, text], i) => (
                  <li key={title} className="flex gap-3">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-lapis font-bold text-white">
                      {(i + 1).toLocaleString(undefined)}
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

      <section>
        <h2 className="font-display text-2xl text-lapis">{t.home.appsTitle}</h2>
        <p className="mb-4 mt-1 text-quiet">{t.home.appsLead}</p>
        <ul className="stagger grid gap-4 sm:grid-cols-2">
          {t.home.apps.map(([name, text]) => (
            <li key={name} className="rounded-xl border border-line bg-surface p-4">
              <h3 className="font-semibold text-ink" dir="auto">
                {name}
              </h3>
              <p className="mt-1 text-quiet">{text}</p>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-4 font-display text-2xl text-lapis">{t.home.faqTitle}</h2>
        <div className="space-y-2">
          {t.home.faq.map(([q, a]) => (
            <details key={q} className="rounded-xl border border-line bg-surface px-4 py-3">
              <summary className="cursor-pointer font-semibold text-ink">{q}</summary>
              <p className="mt-2 text-quiet">{a}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
