"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { QuizSummary } from "@/lib/types";
import { useT } from "@/components/lang";
import { Alert, Button, Card, Chip, Field, Input, useErrorText } from "@/components/ui";
import { ModeBadge, ModePicker, PromptFields } from "@/components/quiz-fields";
import { inputClass } from "@/components/ui";
import { AiBuilder, DraftBar } from "@/components/ai-builder";
import { useCourse } from "../course-context";

export default function Quizzes() {
  const t = useT();
  const router = useRouter();
  const errorText = useErrorText();
  const { course, reload } = useCourse();
  const Q = t.teach.quiz;
  const [adding, setAdding] = useState(false);
  const [d, setD] = useState({ title: "", lesson_id: "" as string, mode: "ai" as "ai" | "manual", prompt: "", ai_question_count: 8 });
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");

  return (
    <div className="space-y-4">
      <AiBuilder courseId={course.id} target="quizzes" onImported={reload} />
      <DraftBar
        courseId={course.id}
        count={course.lessons.filter((l) => l.draft).length + course.quizzes.filter((q) => q.draft).length}
        onDone={reload}
      />
      {course.quizzes.length === 0 && !adding && <p className="text-quiet">{Q.empty}</p>}
      <ul className="space-y-3">
        {course.quizzes.map((q) => (
          <li key={q.id}>
            <Link
              href={`/teach/quizzes/${q.id}/`}
              className="flex items-center gap-3 rounded-xl border border-line bg-surface p-4 text-ink hover:border-lapis hover:no-underline"
            >
              <ModeBadge mode={q.mode} />
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2 font-semibold" dir="auto">
                  {q.title}
                  {q.draft && <Chip tone="warn">{t.teach.draft}</Chip>}
                </span>
                <span className="block text-sm text-quiet" dir="auto">
                  {q.lesson ?? Q.noLesson} · {q.question_count} {Q.questions}
                </span>
              </span>
              <span className="text-sm text-turquoise">{Q.open}</span>
            </Link>
          </li>
        ))}
      </ul>
      {adding ? (
        <Card>
          <h2 className="mb-3 text-xl font-bold text-lapis">{Q.add}</h2>
          <Alert>{error}</Alert>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setErrors({});
              setError("");
              try {
                const body = { ...d, lesson_id: d.lesson_id ? Number(d.lesson_id) : null };
                const q = await api<QuizSummary>(`teach/courses/${course.id}/quizzes`, { method: "POST", body });
                router.push(`/teach/quizzes/${q.id}/`);
              } catch (err) {
                setError(errorText(err));
                if (err instanceof ApiError) setErrors(err.errors);
              }
            }}
          >
            <Field label={Q.title} htmlFor="q-title" error={errors.title}>
              <Input id="q-title" value={d.title} onChange={(e) => setD({ ...d, title: e.target.value })} required />
            </Field>
            <Field label={Q.lesson} htmlFor="q-lesson" error={errors.lesson_id}>
              <select id="q-lesson" className={inputClass} value={d.lesson_id} onChange={(e) => setD({ ...d, lesson_id: e.target.value })}>
                <option value="">{Q.noLesson}</option>
                {course.lessons.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.order}. {l.title}
                  </option>
                ))}
              </select>
            </Field>
            <ModePicker value={d.mode} onChange={(mode) => setD({ ...d, mode })} />
            {d.mode === "ai" && (
              <PromptFields
                prompt={d.prompt}
                count={d.ai_question_count}
                errors={errors}
                onChange={(prompt, ai_question_count) => setD({ ...d, prompt, ai_question_count })}
              />
            )}
            <div className="flex gap-2">
              <Button type="submit" disabled={!d.title.trim()}>
                {Q.add}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setAdding(false)}>
                {t.common.cancel}
              </Button>
            </div>
          </form>
        </Card>
      ) : (
        <Button onClick={() => setAdding(true)}>{Q.add}</Button>
      )}
    </div>
  );
}
