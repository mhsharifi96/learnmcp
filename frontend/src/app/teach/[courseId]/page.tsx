"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useFormatDate, useT } from "@/components/lang";
import { Alert, Card, Spinner, useErrorText } from "@/components/ui";
import { useCourse } from "./course-context";

type Dash = {
  student_count: number;
  inactive_count: number;
  inactive_days: number;
  finished_attempts: number;
  needs_review_count: number;
  tool_calls_total: number;
  tool_calls_ok_percent: number | null;
  students: {
    enrollment_id: number;
    name: string;
    email: string;
    last_activity: string | null;
    inactive: boolean;
    avg_score_percent: number | null;
    quizzes_done: number;
    stuck_count: number;
  }[];
  questions: { prompt: string; quiz: string; concept: string; answered: number; correct_rate: number | null }[];
  stuck: { concept: string; count: number; notes: string[] }[];
};

export default function Overview() {
  const t = useT();
  const fmt = useFormatDate();
  const errorText = useErrorText();
  const { course } = useCourse();
  const [d, setD] = useState<Dash | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Dash>(`teach/courses/${course.id}/dashboard`).then(setD).catch((e) => setError(errorText(e)));
  }, [course.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <Alert>{error}</Alert>;
  if (!d) return <Spinner />;

  const stats = [
    { value: d.student_count, label: t.teach.stats.students },
    { value: d.inactive_count, label: t.teach.inactiveFor(d.inactive_days) },
    { value: d.finished_attempts, label: t.teach.stats.finished },
    { value: d.needs_review_count, label: t.teach.stats.review, href: `/teach/${course.id}/review/` },
    { value: d.tool_calls_ok_percent === null ? "—" : `${d.tool_calls_ok_percent}%`, label: `${t.teach.stats.tools} (${d.tool_calls_total})` },
  ];

  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {stats.map((s) => (
          <div key={s.label} className="rounded-lg border border-line bg-surface px-4 py-3">
            <dt className="text-sm text-quiet">{s.label}</dt>
            <dd className="text-2xl font-bold text-lapis">
              {s.href && Number(s.value) > 0 ? <Link href={s.href}>{s.value}</Link> : s.value}
            </dd>
          </div>
        ))}
      </dl>

      <Card>
        <h2 className="mb-3 text-xl font-bold text-lapis">{t.teach.stats.students}</h2>
        {d.students.length === 0 ? (
          <p className="text-quiet">{t.teach.noStudents}</p>
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>{t.teach.studentCol}</th>
                  <th>{t.teach.lastActivity}</th>
                  <th>{t.teach.avgScore}</th>
                  <th>{t.teach.quizzesDone}</th>
                  <th>{t.teach.stuckCol}</th>
                </tr>
              </thead>
              <tbody>
                {d.students.map((s) => (
                  <tr key={s.enrollment_id}>
                    <td>
                      <Link href={`/teach/students/${s.enrollment_id}/`}>{s.name}</Link>
                      <span className="block text-sm text-quiet" dir="ltr">
                        {s.email}
                      </span>
                    </td>
                    <td className={s.inactive ? "text-danger" : ""}>{s.last_activity ? fmt(s.last_activity) : t.teach.never}</td>
                    <td>{s.avg_score_percent === null ? "—" : `${s.avg_score_percent}%`}</td>
                    <td>{s.quizzes_done}</td>
                    <td>{s.stuck_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-xl font-bold text-lapis">{t.teach.stuck}</h2>
          {d.stuck.length === 0 ? (
            <p className="text-quiet">{t.teach.noStuck}</p>
          ) : (
            <ul className="space-y-3">
              {d.stuck.map((s) => (
                <li key={s.concept}>
                  <span className="font-semibold" dir="auto">
                    {s.concept}
                  </span>{" "}
                  <span className="text-quiet">×{s.count}</span>
                  {s.notes.map((n) => (
                    <p key={n} className="text-sm text-quiet" dir="auto">
                      {n}
                    </p>
                  ))}
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <h2 className="mb-3 text-xl font-bold text-lapis">{t.teach.missed}</h2>
          {d.questions.length === 0 ? (
            <p className="text-quiet">{t.teach.noMissed}</p>
          ) : (
            <ul className="space-y-3">
              {d.questions.map((q, i) => (
                <li key={i}>
                  <p dir="auto">{q.prompt}</p>
                  <div className="mt-1 flex items-center gap-2 text-sm text-quiet">
                    <span
                      className="inline-block h-2 rounded bg-turquoise"
                      style={{ width: `${Math.max(4, (q.correct_rate ?? 0) * 0.8)}px` }}
                      aria-hidden="true"
                    />
                    {q.correct_rate ?? 0}% · {q.answered} {t.teach.answers} · {q.quiz}
                    {q.concept && ` · ${q.concept}`}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
