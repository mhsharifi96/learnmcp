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
        <h2 className="mb-4 font-display text-2xl text-lapis">{t.home.how}</h2>
        <ol className="stagger grid gap-4 sm:grid-cols-3">
          {t.home.steps.map(([title, text], i) => (
            <li key={title} className="border-s-4 border-turquoise ps-4">
              <span className="font-semibold text-ink">
                {(i + 1).toLocaleString(undefined)}. {title}
              </span>
              <p className="text-quiet">{text}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
