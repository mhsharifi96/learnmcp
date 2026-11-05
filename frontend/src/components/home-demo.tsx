"use client";

import { useEffect, useRef } from "react";
import { useT } from "./lang";
import { Icon } from "./ui";

/* Feature demo: student finishes a quiz in their AI -> report lands in the instructor panel.
   Loop controller toggles classes only (no inline styles); CSS does all motion. */
const STEPS: [string, number][] = [
  ["s1", 300],
  ["s2", 1100],
  ["s3", 2300],
  ["s4", 3300],
  ["s5", 4300],
];
const LOOP_MS = 7800;

export function HomeDemo() {
  const t = useT();
  const d = t.home.demo;
  const stage = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const all = STEPS.map(([c]) => c);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.classList.add(...all); // static final state
      return;
    }
    const timers: number[] = [];
    const run = () => {
      el.classList.remove(...all);
      STEPS.forEach(([cls, at]) => timers.push(window.setTimeout(() => el.classList.add(cls), at)));
      timers.push(window.setTimeout(() => el.classList.remove(...all), LOOP_MS - 600));
      timers.push(window.setTimeout(run, LOOP_MS));
    };
    run();
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div ref={stage} aria-hidden="true" className="demo relative overflow-hidden rounded-2xl border border-line bg-surface p-4 shadow-sm sm:p-5">
      <p className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-quiet">
        <Icon name="sparkles" className="h-3.5 w-3.5 text-turquoise" />
        {d.student}
      </p>

      <div className="d-el d-1 ms-auto w-fit max-w-[85%] rounded-2xl rounded-ee-sm bg-lapis px-4 py-2 text-white" dir="ltr">
        {d.answer}
      </div>

      <div className="d-el d-2 mt-3 max-w-[92%] rounded-2xl rounded-es-sm border border-line bg-mist px-4 py-2.5">
        <span className="mb-1 block text-xs text-turquoise" dir="ltr">
          learnmcp · submit_answer → submit_quiz_report
        </span>
        <span className="d-typing inline-flex gap-1 py-1 text-quiet">
          <span />
          <span />
          <span />
        </span>
        <span className="d-el d-3 block text-sm leading-6">{d.report}</span>
      </div>

      <div className="d-el d-4 mt-4 rounded-xl border border-line border-s-4 border-s-danger bg-surface p-3 shadow-sm">
        <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-quiet">
          <Icon name="flag" className="h-3.5 w-3.5 text-danger" />
          {d.instructor}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-ink">{d.student1}</span>
          <span className="rounded-full border border-line bg-mist px-2 py-0.5 text-xs">{d.chip}</span>
          <span className="rounded-full border border-saffron/30 bg-saffron/15 px-2 py-0.5 text-xs text-[#7a4f0f]">
            {t.teach.problems.severity.medium}
          </span>
        </div>
        <p className="mt-1 text-sm font-medium">{d.problem}</p>
        <p className="text-xs text-quiet">{d.problemNote}</p>
        <div className="mt-2 flex items-center gap-2">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-mist">
            <div className="d-fill h-full w-[60%] rounded-full bg-saffron" />
          </div>
          <span className="text-xs font-semibold tabular-nums text-[#8a5a12]">60%</span>
        </div>
      </div>

      <div className="d-el d-5 absolute end-4 top-4 inline-flex items-center gap-1 rounded-full bg-ok px-2.5 py-1 text-xs font-semibold text-white">
        <Icon name="check" className="h-3.5 w-3.5" />
        {d.sent}
      </div>
    </div>
  );
}
