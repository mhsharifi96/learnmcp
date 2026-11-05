"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useT } from "@/components/lang";
import { Alert, Button, Card, Chip, PageTitle, SectionTitle, Spinner, useErrorText } from "@/components/ui";

type QuizItem = { quiz_id: number; title: string; questions: number; ai_generated?: boolean; best_score_percent?: number };
type LessonItem = { lesson_id: number; order: number; title: string; status: string; quizzes: QuizItem[] };
type Course = { course_id: number; title: string; lessons: LessonItem[]; class_quizzes: QuizItem[] };
type Target = { lesson_id: number } | { quiz_id: number };

export default function Study() {
  const t = useT();
  const errorText = useErrorText();
  const { id } = useParams<{ id: string }>();
  const [course, setCourse] = useState<Course | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [done, setDone] = useState("");

  useEffect(() => {
    api<{ course: Course }>(`enrollments/${id}/study`)
      .then((d) => setCourse(d.course))
      .catch((e) => setError(errorText(e)));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function copy(key: string, target: Target) {
    setBusy(key);
    setError("");
    try {
      const { prompt } = await api<{ prompt: string }>(`enrollments/${id}/prompt`, { method: "POST", body: target });
      await navigator.clipboard.writeText(prompt);
      setDone(key);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy("");
    }
  }

  function CopyButton({ k, target, label, quiz = false }: { k: string; target: Target; label: string; quiz?: boolean }) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <Button variant={quiz || done === k ? "secondary" : "primary"} className="px-3 py-1.5 text-sm" disabled={busy === k} onClick={() => copy(k, target)}>
          {busy === k ? t.common.loading : label}
        </Button>
        {done === k && <span className="text-sm text-quiet">{t.study.copied}</span>}
      </div>
    );
  }

  function QuizInfo({ q }: { q: QuizItem }) {
    return (
      <span className="flex flex-wrap items-center gap-2">
        <Chip>{t.study.quizLabel}</Chip>
        <span dir="auto">{q.title}</span>
        <span className="text-sm text-quiet">{t.study.questions(q.questions)}</span>
        {q.ai_generated && <Chip tone="info">{t.study.aiQuiz}</Chip>}
        {q.best_score_percent != null && <Chip tone="ok">{`${t.study.best} ${q.best_score_percent}%`}</Chip>}
      </span>
    );
  }

  function QuizRow({ q }: { q: QuizItem }) {
    return (
      <li className="flex flex-wrap items-center justify-between gap-3 py-2">
        <span className="flex flex-wrap items-center gap-2">
          <Chip>{t.study.quizLabel}</Chip>
          <span dir="auto">{q.title}</span>
          <span className="text-sm text-quiet">{t.study.questions(q.questions)}</span>
          {q.ai_generated && <Chip tone="info">{t.study.aiQuiz}</Chip>}
          {q.best_score_percent != null && <Chip tone="ok">{`${t.study.best} ${q.best_score_percent}%`}</Chip>}
        </span>
        <CopyButton k={`q${q.quiz_id}`} target={{ quiz_id: q.quiz_id }} label={t.study.copyQuiz} quiz />
      </li>
    );
  }

  if (error && !course) return <Alert>{error}</Alert>;
  if (!course) return <Spinner />;

  return (
    <div className="space-y-5">
      <PageTitle lead={t.study.lead}>{`${t.study.title}: ${course.title}`}</PageTitle>
      <Card>
        <ol className="list-decimal space-y-1 ps-5">
          {t.study.steps.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
        <p className="mt-3 text-sm text-quiet">{t.study.oneUse}</p>
      </Card>
      <Alert>{error}</Alert>

      <Card>
        <SectionTitle icon="book">{t.study.lessons}</SectionTitle>
        {course.lessons.length === 0 && <p className="text-quiet">{t.study.empty}</p>}
        <ul className="divide-y divide-[var(--line)]">
          {course.lessons.map((l) => (
            <li key={l.lesson_id} className="py-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <strong dir="auto">{`${l.order}. ${l.title}`}</strong>
                <CopyButton
                  k={`l${l.lesson_id}`}
                  target={{ lesson_id: l.lesson_id }}
                  label={l.quizzes.length > 0 ? t.study.copyLessonQuiz : t.study.copyLesson}
                />
              </div>
              {l.quizzes.length > 0 && (
                <ul className="ms-4 mt-2 space-y-1 border-s border-[var(--line)] ps-4">
                  {l.quizzes.map((q) => (
                    <li key={q.quiz_id}>
                      <QuizInfo q={q} />
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </Card>

      {course.class_quizzes.length > 0 && (
        <Card>
          <SectionTitle icon="check">{t.study.classQuizzes}</SectionTitle>
          <ul className="divide-y divide-[var(--line)]">
            {course.class_quizzes.map((q) => (
              <QuizRow key={q.quiz_id} q={q} />
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
