"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Problem } from "@/lib/types";
import { useFormatDate, useT } from "@/components/lang";
import { ProblemList } from "@/components/problems";
import { Alert, Card, Chip, Icon, ScoreBar, SectionTitle, Spinner, StatCard, useErrorText } from "@/components/ui";
import { useCourse } from "./course-context";

type Student = {
  enrollment_id: number;
  name: string;
  email: string;
  last_activity: string | null;
  inactive: boolean;
  avg_score_percent: number | null;
  quizzes_done: number;
  problem_count: number;
};

type Dash = {
  student_count: number;
  inactive_count: number;
  inactive_days: number;
  finished_attempts: number;
  needs_review_count: number;
  tool_calls_total: number;
  tool_calls_ok_percent: number | null;
  open_problem_count: number;
  students: Student[];
  questions: { prompt: string; quiz: string; concept: string; answered: number; correct_rate: number | null }[];
  weak_concepts: { concept: string; count: number; students: string[] }[];
  problems: Problem[];
};

type SortKey = "name" | "problems" | "score" | "activity";

export default function Overview() {
  const t = useT();
  const fmt = useFormatDate();
  const errorText = useErrorText();
  const { course } = useCourse();
  const [d, setD] = useState<Dash | null>(null);
  const [error, setError] = useState("");
  const [sort, setSort] = useState<SortKey>("problems");

  useEffect(() => {
    api<Dash>(`teach/courses/${course.id}/dashboard`).then(setD).catch((e) => setError(errorText(e)));
  }, [course.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const students = useMemo(() => {
    if (!d) return [];
    const list = [...d.students];
    const ts = (s: Student) => (s.last_activity ? Date.parse(s.last_activity) : 0);
    list.sort((a, b) => {
      if (sort === "problems") return b.problem_count - a.problem_count || (a.avg_score_percent ?? 101) - (b.avg_score_percent ?? 101);
      if (sort === "score") return (a.avg_score_percent ?? 101) - (b.avg_score_percent ?? 101);
      if (sort === "activity") return ts(a) - ts(b);
      return a.name.localeCompare(b.name);
    });
    return list;
  }, [d, sort]);

  if (error) return <Alert>{error}</Alert>;
  if (!d) return <Spinner />;

  function updateProblem(p: Problem) {
    setD((prev) => {
      if (!prev) return prev;
      const old = prev.problems.find((x) => x.id === p.id);
      const delta = old && !!old.resolved_at !== !!p.resolved_at ? (p.resolved_at ? -1 : 1) : 0;
      return {
        ...prev,
        open_problem_count: prev.open_problem_count + delta,
        problems: prev.problems.map((x) => (x.id === p.id ? p : x)),
        students: prev.students.map((s) =>
          s.enrollment_id === p.enrollment_id ? { ...s, problem_count: s.problem_count + delta } : s,
        ),
      };
    });
  }

  const sortButtons: { key: SortKey; label: string }[] = [
    { key: "problems", label: t.teach.stuckCol },
    { key: "score", label: t.teach.avgScore },
    { key: "activity", label: t.teach.lastActivity },
    { key: "name", label: t.teach.studentCol },
  ];

  return (
    <div className="space-y-6">
      <dl className="stagger grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard icon="users" label={t.teach.stats.students} value={d.student_count} />
        <StatCard
          icon="flag"
          label={t.teach.openProblems}
          value={d.open_problem_count}
          tone={d.open_problem_count > 0 ? "danger" : "ok"}
          href="#problems"
        />
        <StatCard icon="moon" label={t.teach.inactiveFor(d.inactive_days)} value={d.inactive_count} tone={d.inactive_count > 0 ? "warn" : "default"} />
        <StatCard icon="clipboard" label={t.teach.stats.finished} value={d.finished_attempts} />
        <StatCard
          icon="eye"
          label={t.teach.stats.review}
          value={d.needs_review_count}
          tone={d.needs_review_count > 0 ? "warn" : "default"}
          href={d.needs_review_count > 0 ? `/teach/${course.id}/review/` : undefined}
        />
        <StatCard
          icon="plug"
          label={`${t.teach.stats.tools} (${d.tool_calls_total})`}
          value={d.tool_calls_ok_percent === null ? "—" : `${d.tool_calls_ok_percent}%`}
        />
      </dl>

      <Card>
        <SectionTitle
          icon="users"
          aside={
            d.students.length > 1 && (
              <div className="flex flex-wrap gap-1 text-sm" role="group">
                {sortButtons.map((b) => (
                  <button
                    key={b.key}
                    type="button"
                    aria-pressed={sort === b.key}
                    onClick={() => setSort(b.key)}
                    className={`min-h-[36px] rounded-md px-2.5 transition-colors ${
                      sort === b.key ? "bg-lapis text-white" : "text-quiet hover:bg-mist hover:text-ink"
                    }`}
                  >
                    {b.label}
                  </button>
                ))}
              </div>
            )
          }
        >
          {t.teach.stats.students}
        </SectionTitle>
        {d.students.length === 0 ? (
          <p className="text-quiet">{t.teach.noStudents}</p>
        ) : (
          <div className="-mx-5 overflow-x-auto sm:-mx-6">
            <table className="min-w-[640px]">
              <thead>
                <tr>
                  <th className="ps-5 sm:ps-6">{t.teach.studentCol}</th>
                  <th>{t.teach.stuckCol}</th>
                  <th className="w-48">{t.teach.avgScore}</th>
                  <th>{t.teach.quizzesDone}</th>
                  <th className="pe-5 sm:pe-6">{t.teach.lastActivity}</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.enrollment_id}>
                    <td className="ps-5 sm:ps-6">
                      <Link href={`/teach/students/${s.enrollment_id}/`} className="font-semibold">
                        {s.name}
                      </Link>
                      <span className="block text-sm text-quiet" dir="ltr">
                        {s.email}
                      </span>
                    </td>
                    <td>
                      {s.problem_count > 0 ? (
                        <Chip tone="danger">
                          <Icon name="flag" className="h-3 w-3" />
                          {t.teach.problems.openCount(s.problem_count)}
                        </Chip>
                      ) : (
                        <span className="text-quiet">—</span>
                      )}
                    </td>
                    <td>
                      <ScoreBar value={s.avg_score_percent} />
                    </td>
                    <td className="tabular-nums">{s.quizzes_done}</td>
                    <td className="pe-5 sm:pe-6">
                      <span className={s.inactive ? "inline-flex items-center gap-1 text-danger" : ""}>
                        {s.inactive && <Icon name="moon" className="h-4 w-4" />}
                        {s.last_activity ? fmt(s.last_activity) : t.teach.never}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card>
        <div id="problems" className="scroll-mt-24" />
        <SectionTitle icon="flag">{t.teach.stuck}</SectionTitle>
        <ProblemList problems={d.problems} onChange={updateProblem} />
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <SectionTitle icon="target" aside={<span className="text-sm text-quiet">{t.teach.weakLead}</span>}>
            {t.teach.weak}
          </SectionTitle>
          {d.weak_concepts.length === 0 ? (
            <p className="text-quiet">{t.teach.noWeak}</p>
          ) : (
            <ul className="stagger space-y-3">
              {d.weak_concepts.map((w) => {
                const max = d.weak_concepts[0].count || 1;
                return (
                  <li key={w.concept}>
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="font-semibold" dir="auto">
                        {w.concept}
                      </span>
                      <span className="text-sm tabular-nums text-quiet">×{w.count}</span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-mist">
                      <div className="bar-grow h-full rounded-full bg-danger/70" style={{ width: `${(100 * w.count) / max}%` }} />
                    </div>
                    <p className="mt-1 text-xs text-quiet" dir="auto">
                      {w.students.join("، ")}
                    </p>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
        <Card>
          <SectionTitle icon="xCircle">{t.teach.missed}</SectionTitle>
          {d.questions.length === 0 ? (
            <p className="text-quiet">{t.teach.noMissed}</p>
          ) : (
            <ul className="stagger space-y-4">
              {d.questions.map((q, i) => (
                <li key={i}>
                  <p dir="auto" className="line-clamp-2">
                    {q.prompt}
                  </p>
                  <ScoreBar value={q.correct_rate} className="mt-1" />
                  <p className="text-xs text-quiet">
                    {q.answered} {t.teach.answers} · {q.quiz}
                    {q.concept && ` · ${q.concept}`}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
