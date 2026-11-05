"use client";

import Link from "next/link";
import { CodeForm } from "@/components/code-form";
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
        <div aria-hidden="true" className="rounded-2xl border border-line bg-surface p-4 sm:p-5">
          <div className="bubble-1 ms-auto w-fit max-w-[85%] rounded-2xl rounded-ee-sm bg-lapis px-4 py-2.5 text-white">
            {t.home.chatYou}
          </div>
          <div className="bubble-2 mt-3 max-w-[90%] rounded-2xl rounded-es-sm border border-line bg-mist px-4 py-3">
            <span className="mb-1 block text-xs text-turquoise" dir="ltr">
              learnmcp · list_my_courses
            </span>
            {t.home.chatAi}
          </div>
        </div>
      </section>

      <div className="grid gap-5 md:grid-cols-2">
        <Card>
          <h2 className="font-display text-2xl text-lapis">{t.home.studentTitle}</h2>
          <p className="mb-4 mt-1 text-quiet">{t.home.studentText}</p>
          <CodeForm />
          <p className="mt-3 text-sm">
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
        <ol className="grid gap-4 sm:grid-cols-3">
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
