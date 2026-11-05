"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Problem } from "@/lib/types";
import { useFormatDate, useT } from "@/components/lang";
import { ProblemList } from "@/components/problems";
import {
  Alert,
  Card,
  Chip,
  Icon,
  PageTitle,
  ScoreBar,
  SectionTitle,
  Spinner,
  StatCard,
  StatusTag,
  scoreTone,
  useErrorText,
} from "@/components/ui";

type AnswerRow = {
  id: number;
  question: string;
  answer: string;
  status: string;
  expected: string;
  explanation: string;
  concept: string;
  ai_generated: boolean;
};

type Attempt = {
  id: number;
  quiz: string;
  lesson: string | null;
  ai_generated: boolean;
  started_at: string;
  finished_at: string | null;
  score_percent: number | null;
  correct: number;
  incorrect: number;
  needs_review: number;
  total: number;
  summary: string;
  weak_concepts: string[];
  answers: AnswerRow[];
};

type Data = {
  course: { id: number; title: string };
  student: { name: string; email: string };
  joined_at: string;
  last_activity_at: string | null;
  avg_score_percent: number | null;
  score_trend: { quiz: string; score_percent: number | null; finished_at: string }[];
  attempts: Attempt[];
  problems: Problem[];
  events: { label: string; lesson: string | null; concept: string; note: string; client: string; created_at: string }[];
};

export default function StudentDetail() {
  const t = useT();
  const fmt = useFormatDate();
  const errorText = useErrorText();
  const { id } = useParams<{ id: string }>();
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Data>(`teach/students/${id}`).then(setD).catch((e) => setError(errorText(e)));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <Alert>{error}</Alert>;
  if (!d) return <Spinner />;

  const openProblems = d.problems.filter((p) => !p.resolved_at).length;
  const finished = d.attempts.filter((a) => a.finished_at).length;

  return (
    <div className="space-y-6">
      <Link href={`/teach/${d.course.id}/`} className="inline-flex min-h-[40px] items-center gap-1 text-sm">
        <Icon name="chevron" className="h-4 w-4 rotate-90 rtl:-rotate-90" />
        {t.common.back} · {d.course.title}
      </Link>
      <PageTitle lead={<span dir="ltr">{d.student.email}</span>}>{d.student.name}</PageTitle>
      <p className="-mt-4 text-sm text-quiet">
        {t.me.joined}: {fmt(d.joined_at, false)} · {t.teach.lastActivity}: {fmt(d.last_activity_at)}
      </p>

      <dl className="stagger grid grid-cols-2 gap-3 sm:grid-cols-3">
        <StatCard
          icon="target"
          label={t.teach.avgScore}
          value={d.avg_score_percent === null ? "—" : `${d.avg_score_percent}%`}
          tone={d.avg_score_percent === null ? "default" : d.avg_score_percent >= 80 ? "ok" : d.avg_score_percent >= 50 ? "warn" : "danger"}
        />
        <StatCard icon="clipboard" label={t.teach.quizzesDone} value={finished} />
        <StatCard icon="flag" label={t.teach.openProblems} value={openProblems} tone={openProblems > 0 ? "danger" : "ok"} href="#problems" />
      </dl>

      {d.score_trend.length > 1 && (
        <Card>
          <SectionTitle icon="sparkles">{t.teach.trend}</SectionTitle>
          <ol className="flex h-32 items-end gap-2" aria-label={t.teach.trend}>
            {d.score_trend.map((s, i) => (
              <li key={i} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1" title={`${s.quiz} · ${fmt(s.finished_at)}`}>
                <span className={`text-xs font-semibold tabular-nums ${scoreTone(s.score_percent).text}`}>{s.score_percent}%</span>
                <div
                  className={`bar-grow-y w-full max-w-[2.5rem] rounded-t-md ${scoreTone(s.score_percent).bar}`}
                  style={{ height: `${Math.max(4, s.score_percent ?? 0)}%` }}
                />
                <span className="w-full truncate text-center text-[11px] text-quiet" dir="auto">
                  {s.quiz}
                </span>
              </li>
            ))}
          </ol>
        </Card>
      )}

      <Card>
        <div id="problems" className="scroll-mt-24" />
        <SectionTitle icon="flag">{t.teach.stuck}</SectionTitle>
        <ProblemList
          problems={d.problems}
          showStudent={false}
          onChange={(p) => setD((prev) => (prev ? { ...prev, problems: prev.problems.map((x) => (x.id === p.id ? p : x)) } : prev))}
        />
      </Card>

      <section>
        <SectionTitle icon="clipboard">{t.teach.student.attempts}</SectionTitle>
        {d.attempts.length === 0 && <Card><p className="text-quiet">{t.me.noAttempts}</p></Card>}
        <div className="stagger space-y-4">
          {d.attempts.map((a) => (
            <QuizReport key={a.id} a={a} />
          ))}
        </div>
      </section>

      <Card>
        <details>
          <summary className="flex min-h-[40px] items-center justify-between">
            <span className="flex items-center gap-2 text-lg font-bold text-lapis">
              <Icon name="book" className="h-5 w-5 text-turquoise" />
              {t.teach.student.events} <span className="text-sm font-normal text-quiet">({d.events.length})</span>
            </span>
            <Icon name="chevron" className="h-5 w-5 text-quiet" />
          </summary>
          <div className="mt-3 overflow-x-auto">
            <table>
              <tbody>
                {d.events.length === 0 && (
                  <tr>
                    <td className="text-quiet">{t.me.nothing}</td>
                  </tr>
                )}
                {d.events.map((ev, i) => (
                  <tr key={i}>
                    <td className="whitespace-nowrap text-sm">{fmt(ev.created_at)}</td>
                    <td dir="ltr" className="text-start text-sm">
                      {ev.label}
                    </td>
                    <td dir="auto" className="text-sm">
                      {[ev.lesson, ev.concept, ev.note && `“${ev.note}”`].filter(Boolean).join(" · ")}
                    </td>
                    <td className="text-sm text-quiet">{ev.client || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </Card>
    </div>
  );
}

function QuizReport({ a }: { a: Attempt }) {
  const t = useT();
  const fmt = useFormatDate();
  const r = t.teach.report;
  const numbered = a.answers.map((x, i) => ({ ...x, n: i + 1 }));
  const wrong = numbered.filter((x) => x.status !== "correct");
  const done = !!a.finished_at;

  return (
    <Card>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="flex flex-wrap items-center gap-2 text-lg font-bold text-ink">
            <span dir="auto">{a.quiz}</span>
            {a.ai_generated && <Chip tone="info">{t.teach.quiz.aiBadge}</Chip>}
            {!done && <Chip tone="warn">{r.inProgress}</Chip>}
          </h3>
          <p className="text-sm text-quiet">
            {fmt(a.started_at)}
            {a.lesson && ` · ${a.lesson}`}
          </p>
        </div>
        <div className="w-full sm:w-56">
          <ScoreBar value={a.score_percent} />
          <p className="mt-1 text-xs text-quiet sm:text-end">{r.score(a.correct, a.total)}</p>
        </div>
      </header>

      {done && (
        <div className="mt-4 rounded-lg border border-turquoise/25 bg-turquoise/5 p-4">
          <p className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-turquoise">
            <Icon name="sparkles" className="h-4 w-4" />
            {r.summary}
          </p>
          {a.summary ? (
            <p dir="auto" className="whitespace-pre-line">
              {a.summary}
            </p>
          ) : (
            <p className="text-sm text-quiet">{r.noSummary}</p>
          )}
          {a.weak_concepts.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <span className="text-sm font-semibold text-ink">{r.weakConcepts}:</span>
              {a.weak_concepts.map((c) => (
                <Chip key={c} tone="danger">
                  {c}
                </Chip>
              ))}
            </div>
          )}
        </div>
      )}

      {a.answers.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 flex items-center gap-1.5 font-semibold text-ink">
            <Icon name="alert" className="h-4 w-4 text-danger" />
            {r.mistakes}
          </p>
          {wrong.length === 0 ? (
            <p className="flex items-center gap-1.5 text-ok">
              <Icon name="checkCircle" className="h-4 w-4" />
              {r.noMistakes}
            </p>
          ) : (
            <ol className="stagger space-y-2">
              {wrong.map((x) => (
                <li key={x.id} className="rounded-lg border border-line bg-mist/50 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded bg-lapis px-1.5 py-0.5 text-xs font-bold text-white">{r.q(x.n)}</span>
                    <StatusTag status={x.status} />
                    {x.concept && <Chip>{x.concept}</Chip>}
                  </div>
                  <p className="mt-1.5 font-medium" dir="auto">
                    {x.question}
                  </p>
                  <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
                    <div className="flex items-start gap-1.5 rounded-md bg-danger/5 px-2.5 py-1.5">
                      <Icon name="x" className="mt-1 h-3.5 w-3.5 text-danger" />
                      <div>
                        <dt className="text-xs text-quiet">{r.studentAnswer}</dt>
                        <dd dir="auto" className="font-medium text-danger">
                          {x.answer}
                        </dd>
                      </div>
                    </div>
                    <div className="flex items-start gap-1.5 rounded-md bg-ok/5 px-2.5 py-1.5">
                      <Icon name="check" className="mt-1 h-3.5 w-3.5 text-ok" />
                      <div>
                        <dt className="text-xs text-quiet">{r.correctAnswer}</dt>
                        <dd dir="auto" className="font-medium text-ok">
                          {x.expected}
                        </dd>
                      </div>
                    </div>
                  </dl>
                  {x.explanation && (
                    <p className="mt-2 text-sm text-quiet" dir="auto">
                      <span className="font-semibold">{r.why}: </span>
                      {x.explanation}
                    </p>
                  )}
                </li>
              ))}
            </ol>
          )}

          <details className="mt-3">
            <summary className="inline-flex min-h-[40px] items-center gap-1 text-sm font-medium text-turquoise">
              {r.allAnswers} ({a.answers.length})
              <Icon name="chevron" className="h-4 w-4" />
            </summary>
            <div className="mt-2 overflow-x-auto">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>{t.me.question}</th>
                    <th>{r.studentAnswer}</th>
                    <th>{t.teach.student.expected}</th>
                    <th>{t.me.result}</th>
                  </tr>
                </thead>
                <tbody>
                  {numbered.map((x) => (
                    <tr key={x.id}>
                      <td className="tabular-nums text-quiet">{x.n}</td>
                      <td dir="auto">{x.question}</td>
                      <td dir="auto">{x.answer}</td>
                      <td dir="auto">{x.expected}</td>
                      <td>
                        <StatusTag status={x.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </div>
      )}
    </Card>
  );
}
