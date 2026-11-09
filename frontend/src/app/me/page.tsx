"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { PendingNotice } from "@/app/join/[code]/join-view";
import { api } from "@/lib/api";
import { useFormatDate, useLang, useT } from "@/components/lang";
import { VerifyNotice } from "@/components/student-auth-form";
import type { LessonKind, StudentAccount } from "@/lib/types";
import {
  Alert,
  Button,
  ButtonLink,
  Card,
  Chip,
  Icon,
  PageTitle,
  ScoreBar,
  SectionTitle,
  Spinner,
  StatCard,
  StatusTag,
  useErrorText,
} from "@/components/ui";

type App = { name: string; via: "mcp" | "prompt" };
type Item =
  | { type: "lesson"; at: string; title: string; app: App }
  | { type: "feedback"; at: string; title: string; understood: number | null; difficult: string[]; note: string; app: App }
  | {
      type: "quiz";
      at: string;
      attempt_id: number;
      title: string;
      lesson: string | null;
      finished: boolean;
      score_percent: number | null;
      correct: number;
      needs_review: number;
      total: number;
      answered: number;
      summary: string;
      weak_concepts: string[];
      app: App;
      answers: { question: string; answer: string; status: string }[];
    }
  | { type: "problem"; at: string; title: string; lesson: string | null; note: string; resolved: boolean; instructor_note: string };

type Progress = {
  lessons_total: number;
  lessons_started: number;
  lessons_done: number;
  quizzes_done: number;
  average_score_percent: number | null;
  lessons: { id: number; order: number; title: string; kind: LessonKind; status: "not_started" | "started" | "quiz_done"; best_score_percent: number | null }[];
  next_lesson: { id: number; title: string } | null;
};

type Enr = {
  id: number;
  course: string;
  instructor: string;
  joined_at: string;
  approved?: boolean;
  consent_at: string;
  token_hint: string;
  progress: Progress;
  timeline: Item[];
};

type Filter = "all" | "lesson" | "quiz" | "problem";

function AppTag({ app }: { app: App }) {
  const t = useT();
  if (!app.name && app.via === "mcp") return null;
  return (
    <span className="text-xs text-quiet">
      {[app.name, t.hist.via[app.via]].filter(Boolean).join(" · ")}
    </span>
  );
}

function QuizEntry({ item }: { item: Extract<Item, { type: "quiz" }> }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  return (
    <div className="min-w-0 flex-1">
      <p className="flex flex-wrap items-center gap-2">
        <strong dir="auto">{item.title}</strong>
        {!item.finished && <Chip tone="warn">{t.hist.inProgress}</Chip>}
        <AppTag app={item.app} />
      </p>
      {item.lesson && (
        <p className="text-sm text-quiet" dir="auto">
          {item.lesson}
        </p>
      )}
      {item.finished ? (
        <div className="mt-1 max-w-sm">
          <ScoreBar value={item.score_percent} />
          <p className="text-sm text-quiet">
            {t.hist.correctOf(item.correct, item.total)}
            {item.needs_review > 0 && ` · ${t.hist.review(item.needs_review)}`}
          </p>
        </div>
      ) : (
        <p className="text-sm text-quiet">{t.hist.answered(item.answered, item.total)}</p>
      )}
      {item.summary && (
        <p className="mt-2 rounded-lg bg-mist px-3 py-2 text-sm" dir="auto">
          <span className="font-semibold">{t.hist.aiSummary}: </span>
          {item.summary}
        </p>
      )}
      {item.weak_concepts.length > 0 && (
        <p className="mt-2 flex flex-wrap items-center gap-1.5 text-sm">
          <span className="text-quiet">{t.hist.toReview}:</span>
          {item.weak_concepts.map((c) => (
            <Chip key={c} tone="warn">
              {c}
            </Chip>
          ))}
        </p>
      )}
      {item.answers.length > 0 && (
        <>
          <button type="button" className="mt-2 text-sm font-medium text-lapis hover:underline" onClick={() => setOpen(!open)}>
            {open ? t.hist.hideAnswers : t.hist.showAnswers}
          </button>
          {open && (
            <ol className="mt-2 space-y-2">
              {item.answers.map((a, i) => (
                <li key={i} className="rounded-lg border border-line px-3 py-2 text-sm">
                  <p dir="auto">
                    <span className="text-quiet">{i + 1}. </span>
                    {a.question}
                  </p>
                  <p className="mt-1 flex flex-wrap items-center gap-2">
                    <span dir="auto" className="font-medium">
                      {a.answer}
                    </span>
                    <StatusTag status={a.status} />
                  </p>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </div>
  );
}

function Entry({ item, time }: { item: Item; time: string }) {
  const t = useT();
  const icon = { lesson: "book", feedback: "message", quiz: "award", problem: "alert" }[item.type];
  const tone = {
    lesson: "bg-lapis/10 text-lapis",
    feedback: "bg-turquoise/10 text-turquoise",
    quiz: "bg-saffron/20 text-[#8a5a12]",
    problem: "bg-danger/10 text-danger",
  }[item.type];
  return (
    <li className="relative flex gap-3 py-3 pe-14">
      <span className="absolute end-0 top-3 text-xs text-quiet" dir="ltr">
        {time}
      </span>
      <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${tone}`}>
        <Icon name={icon} className="h-4 w-4" />
      </span>
      {item.type === "lesson" && (
        <div className="min-w-0 flex-1">
          <p className="text-sm text-quiet">{t.hist.studied}</p>
          <p className="flex flex-wrap items-center gap-2">
            <strong dir="auto">{item.title}</strong>
            <AppTag app={item.app} />
          </p>
        </div>
      )}
      {item.type === "feedback" && (
        <div className="min-w-0 flex-1">
          <p className="text-sm text-quiet">{t.hist.feedback}</p>
          <p className="flex flex-wrap items-center gap-2">
            <strong dir="auto">{item.title}</strong>
            {item.understood != null && <Chip tone={item.understood >= 4 ? "ok" : item.understood <= 2 ? "danger" : "warn"}>{t.hist.understood(item.understood)}</Chip>}
            <AppTag app={item.app} />
          </p>
          {item.difficult.length > 0 && (
            <p className="mt-1 flex flex-wrap items-center gap-1.5 text-sm">
              <span className="text-quiet">{t.hist.difficult}:</span>
              {item.difficult.map((c) => (
                <Chip key={c} tone="warn">
                  {c}
                </Chip>
              ))}
            </p>
          )}
          {item.note && (
            <p className="mt-1 text-sm" dir="auto">
              {item.note}
            </p>
          )}
        </div>
      )}
      {item.type === "quiz" && <QuizEntry item={item} />}
      {item.type === "problem" && (
        <div className="min-w-0 flex-1">
          <p className="text-sm text-quiet">{t.hist.problem}</p>
          <p className="flex flex-wrap items-center gap-2">
            <strong dir="auto">{item.title}</strong>
            {item.resolved && <Chip tone="ok">{t.hist.resolved}</Chip>}
          </p>
          {item.lesson && item.lesson !== item.title && (
            <p className="text-sm text-quiet" dir="auto">
              {item.lesson}
            </p>
          )}
          {item.note && (
            <p className="mt-1 text-sm" dir="auto">
              {item.note}
            </p>
          )}
          {item.instructor_note && (
            <p className="mt-2 rounded-lg bg-ok/10 px-3 py-2 text-sm" dir="auto">
              <span className="font-semibold">{t.hist.instructorNote}: </span>
              {item.instructor_note}
            </p>
          )}
        </div>
      )}
    </li>
  );
}

function History({ items }: { items: Item[] }) {
  const t = useT();
  const fmt = useFormatDate();
  const lang = useLang();
  const [filter, setFilter] = useState<Filter>("all");

  const groups = useMemo(() => {
    const shown = items.filter((i) => filter === "all" || i.type === filter || (filter === "lesson" && i.type === "feedback"));
    const dayKey = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
    const today = new Date();
    const yesterday = new Date(Date.now() - 86_400_000);
    const out: { label: string; items: Item[] }[] = [];
    for (const it of shown) {
      const d = new Date(it.at);
      const label =
        dayKey(d) === dayKey(today) ? t.hist.today : dayKey(d) === dayKey(yesterday) ? t.hist.yesterday : fmt(it.at, false);
      if (out.at(-1)?.label !== label) out.push({ label, items: [] });
      out.at(-1)!.items.push(it);
    }
    return out;
  }, [items, filter, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const time = (iso: string) =>
    new Intl.DateTimeFormat(lang === "fa" ? "fa-IR" : "en-GB", { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        {(["all", "lesson", "quiz", "problem"] as Filter[]).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`rounded-full border px-3 py-1 text-sm ${filter === f ? "border-lapis bg-lapis text-white" : "border-line bg-surface hover:border-lapis"}`}
          >
            {t.hist.filter[f]}
          </button>
        ))}
      </div>
      {groups.length === 0 && <p className="text-quiet">{t.hist.empty}</p>}
      {groups.map((g) => (
        <div key={g.label} className="mb-2">
          <h4 className="sticky top-16 z-10 bg-surface py-1 text-sm font-semibold text-quiet">{g.label}</h4>
          <ul className="divide-y divide-[var(--line)]">
            {g.items.map((it, i) => (
              <Entry key={i} item={it} time={time(it.at)} />
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function ClassCard({ e, onError, onLeft }: { e: Enr; onError: (s: string) => void; onLeft: () => void }) {
  const t = useT();
  const fmt = useFormatDate();
  const router = useRouter();
  const errorText = useErrorText();
  const p = e.progress;
  const statusTone = { not_started: "default", started: "info", quiz_done: "ok" } as const;

  if (e.approved === false)
    return (
      <Card>
        <h2 className="mb-1 font-display text-2xl text-lapis" dir="auto">
          {e.course}
        </h2>
        <p className="mb-4 text-sm text-quiet">
          {t.me.instructor}: <span className="text-ink">{e.instructor}</span> · <Chip tone="warn">{t.catalog.pending}</Chip>
        </p>
        <PendingNotice link={false} />
      </Card>
    );

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="font-display text-2xl text-lapis pe-2" dir="auto">
              {e.course}
            </h2>
            <p className="text-sm text-quiet">
              {t.me.instructor}: <span className="text-ink">{e.instructor}</span>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:flex-col sm:items-end">
            <ButtonLink href={`/study/${e.id}/`}>{t.hist.continue}</ButtonLink>
            <span className="text-sm text-quiet" dir="auto">
              {p.next_lesson ? `${t.hist.next}: ${p.next_lesson.title}` : p.lessons_total > 0 ? t.hist.allDone : ""}
            </span>
          </div>
        </div>
      </Card>

      <Card>
        <SectionTitle icon="target">{t.hist.progress}</SectionTitle>
        <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard icon="book" label={t.hist.lessonsStarted} value={`${p.lessons_started}/${p.lessons_total}`} />
          <StatCard icon="checkCircle" label={t.hist.lessonsDone} value={p.lessons_done} tone="ok" />
          <StatCard icon="award" label={t.hist.quizzes} value={p.quizzes_done} tone="warn" />
          <StatCard icon="target" label={t.hist.avg} value={p.average_score_percent == null ? "—" : `${p.average_score_percent}%`} />
        </dl>
      </Card>

      {p.lessons.length > 0 && (
        <Card>
          <SectionTitle icon="book">{t.hist.lessons}</SectionTitle>
          <ol className="space-y-2">
            {p.lessons.map((l) => (
              <li key={l.id} className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-2 rounded-lg border border-line bg-mist/40 p-3 sm:grid-cols-[1fr_auto_10rem]">
                <span className="flex min-w-0 flex-wrap items-center gap-2">
                  <span className="text-quiet">{l.order}.</span>
                  <span dir="auto">{l.title}</span>
                  {l.kind !== "general" && <Chip tone="info">{t.kinds[l.kind]?.label}</Chip>}
                </span>
                <Chip tone={statusTone[l.status]}>{t.hist.status[l.status]}</Chip>
                <div className="col-span-2 sm:col-span-1">{l.best_score_percent != null && <ScoreBar value={l.best_score_percent} />}</div>
              </li>
            ))}
          </ol>
        </Card>
      )}

      <Card>
        <SectionTitle icon="calendar">{t.hist.history}</SectionTitle>
        <History items={e.timeline} />
      </Card>

      <details className="rounded-xl border border-line bg-surface px-4 py-3 shadow-sm">
        <summary className="cursor-pointer py-1 font-medium text-lapis">{t.hist.settings}</summary>
        <dl className="mt-2 grid gap-x-6 gap-y-1 text-sm text-quiet sm:grid-cols-2">
          <div>
            {t.hist.joined}: {fmt(e.joined_at, false)}
          </div>
          <div>
            {t.hist.consent}: {fmt(e.consent_at)}
          </div>
          <div>
            {t.hist.linkEnds}: <code dir="ltr">…{e.token_hint}</code>
          </div>
        </dl>
        <p className="mt-3 text-sm text-quiet">{t.hist.regenerateNote}</p>
        <div className="my-3 flex flex-wrap gap-2">
          <Button
            variant="secondary"
            className="text-sm"
            onClick={async () => {
              try {
                await api(`enrollments/${e.id}/regenerate`, { method: "POST" });
                router.push(`/connect/${e.id}/`);
              } catch (err) {
                onError(errorText(err));
              }
            }}
          >
            <Icon name="repeat" className="h-4 w-4" />
            {t.me.regenerate}
          </Button>
          <Button
            variant="danger"
            className="text-sm"
            onClick={async () => {
              if (!window.confirm(t.me.leaveConfirm)) return;
              try {
                await api(`enrollments/${e.id}/leave`, { method: "POST" });
                onLeft();
              } catch (err) {
                onError(errorText(err));
              }
            }}
          >
            {t.me.leave}
          </Button>
        </div>
        <p className="mb-2 text-xs text-quiet">{t.me.lead}</p>
      </details>
    </div>
  );
}

export default function Me() {
  const t = useT();
  const errorText = useErrorText();
  const router = useRouter();
  const [data, setData] = useState<Enr[] | null>(null);
  const [student, setStudent] = useState<StudentAccount | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(() => {
    api<{ enrollments: Enr[]; student: StudentAccount | null }>("me")
      .then((d) => {
        setStudent(d.student);
        setData(d.enrollments);
      })
      .catch((e) => setError(errorText(e)));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(load, [load]);

  if (!data && error) return <Alert>{error}</Alert>;
  if (!data) return <Spinner />;

  return (
    <div className="space-y-5">
      <PageTitle>{t.me.title}</PageTitle>
      <Alert>{error}</Alert>
      <Alert kind="ok">{notice}</Alert>

      {student ? (
        <Card className="!p-4 sm:!p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <strong>{student.name}</strong>
                <Chip tone={student.email_verified ? "ok" : "warn"}>
                  {student.email_verified ? t.student.verifiedChip : t.student.unverifiedChip}
                </Chip>
              </div>
              <span dir="ltr" className="mt-1 block break-all text-sm text-quiet">
                {student.email}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-line pt-3 sm:border-0 sm:pt-0">
              <label className="flex items-center gap-2 text-sm" title={t.student.remindersHelp}>
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-[var(--turquoise)]"
                  checked={student.email_reminders}
                  onChange={async (ev) => {
                    try {
                      const r = await api<{ student: StudentAccount }>("me/settings", {
                        method: "PATCH",
                        body: { email_reminders: ev.target.checked },
                      });
                      setStudent(r.student);
                    } catch (err) {
                      setError(errorText(err));
                    }
                  }}
                />
                {t.student.reminders}
              </label>
              <Button
                variant="ghost"
                className="ms-auto px-2 py-1 text-sm"
                onClick={async () => {
                  await api("auth/logout", { method: "POST" }).catch(() => undefined);
                  router.push("/");
                  router.refresh();
                }}
              >
                {t.student.logout}
              </Button>
            </div>
          </div>
          {!student.email_verified && (
            <div className="mt-3">
              <VerifyNotice email={student.email} />
            </div>
          )}
        </Card>
      ) : (
        <Card>
          <p className="mb-3">{data.length > 0 ? t.student.legacy : t.student.needAccount}</p>
          <div className="flex flex-wrap gap-3">
            <ButtonLink href="/student/signup/">{t.student.signup}</ButtonLink>
            <ButtonLink href="/student/login/" variant="secondary">
              {t.student.login}
            </ButtonLink>
          </div>
        </Card>
      )}

      {data.length === 0 && (
        <Card>
          <p className="mb-3">{t.me.empty}</p>
          <div className="flex flex-wrap gap-3">
            <ButtonLink href="/classes/">{t.nav.classes}</ButtonLink>
            <ButtonLink href="/join/" variant="secondary">
              {t.me.joinLink}
            </ButtonLink>
          </div>
          <p className="mt-3 text-sm">
            <Link href="/me/restore/">{t.me.restoreLink}</Link>
          </p>
        </Card>
      )}

      {data.map((e) => (
        <ClassCard
          key={e.id}
          e={e}
          onError={setError}
          onLeft={() => {
            setNotice(t.me.left);
            load();
          }}
        />
      ))}
    </div>
  );
}
