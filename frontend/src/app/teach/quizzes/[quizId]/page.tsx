"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Question, QuizDetail } from "@/lib/types";
import { useT } from "@/components/lang";
import { ModePicker, PromptFields } from "@/components/quiz-fields";
import { Alert, Button, Card, Field, Input, inputClass, PageTitle, Spinner, Textarea, useErrorText } from "@/components/ui";

type QDraft = Omit<Question, "id">;
const lines = (s: string) => s.split("\n").map((x) => x.trim()).filter(Boolean);
const LETTERS = "ABCDEFGHIJ";

function QuestionForm({
  initial,
  onSave,
  onCancel,
  onDelete,
}: {
  initial: QDraft;
  onSave: (d: QDraft) => Promise<void>;
  onCancel: () => void;
  onDelete?: () => Promise<void>;
}) {
  const t = useT();
  const errorText = useErrorText();
  const Qn = t.teach.question;
  const [d, setD] = useState(initial);
  const [optionsText, setOptionsText] = useState(initial.options.join("\n"));
  const [acceptedText, setAcceptedText] = useState(initial.accepted_answers.join("\n"));
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const opts = lines(optionsText);

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError("");
        setErrors({});
        try {
          await onSave({
            ...d,
            options: d.type === "mcq" ? opts : [],
            accepted_answers: d.type === "short" ? lines(acceptedText) : [],
          });
        } catch (err) {
          setError(errorText(err));
          if (err instanceof ApiError) setErrors(err.errors);
        }
        setBusy(false);
      }}
    >
      <Alert>{error}</Alert>
      <div className="mb-4 flex flex-wrap gap-2" role="radiogroup" aria-label={Qn.type}>
        {(["mcq", "short"] as const).map((ty) => (
          <button
            type="button"
            key={ty}
            role="radio"
            aria-checked={d.type === ty}
            onClick={() => setD({ ...d, type: ty })}
            className={`rounded-full border px-3 py-1 text-sm ${d.type === ty ? "border-turquoise bg-turquoise/10 font-semibold text-turquoise" : "border-line"}`}
          >
            {ty === "mcq" ? Qn.mcq : Qn.short}
          </button>
        ))}
      </div>
      <Field label={Qn.prompt} htmlFor="qn-prompt" error={errors.prompt}>
        <Textarea id="qn-prompt" rows={2} dir="auto" value={d.prompt} onChange={(e) => setD({ ...d, prompt: e.target.value })} required />
      </Field>
      {d.type === "mcq" && (
        <Field label={Qn.options} htmlFor="qn-options" help={Qn.optionsHelp} error={errors.options_json}>
          <Textarea id="qn-options" rows={4} dir="auto" value={optionsText} onChange={(e) => setOptionsText(e.target.value)} />
        </Field>
      )}
      <Field
        label={Qn.correct}
        htmlFor="qn-correct"
        help={d.type === "mcq" ? Qn.correctHelpMcq : Qn.correctHelpShort}
        error={errors.correct_answer}
      >
        {d.type === "mcq" && opts.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {opts.map((o, i) => {
              const letter = LETTERS[i];
              const on = d.correct_answer.toUpperCase() === letter || d.correct_answer === o;
              return (
                <button
                  type="button"
                  key={i}
                  onClick={() => setD({ ...d, correct_answer: letter })}
                  aria-pressed={on}
                  className={`rounded-lg border px-3 py-1.5 text-sm ${on ? "border-ok bg-ok/10 font-semibold text-ok" : "border-line bg-white"}`}
                  dir="auto"
                >
                  {letter}) {o}
                </button>
              );
            })}
          </div>
        ) : (
          <Input id="qn-correct" dir="auto" value={d.correct_answer} onChange={(e) => setD({ ...d, correct_answer: e.target.value })} />
        )}
      </Field>
      {d.type === "short" && (
        <Field label={Qn.accepted} htmlFor="qn-acc" help={Qn.acceptedHelp} error={errors.accepted_answers_json}>
          <Textarea id="qn-acc" rows={2} dir="auto" value={acceptedText} onChange={(e) => setAcceptedText(e.target.value)} />
        </Field>
      )}
      <div className="grid gap-x-4 sm:grid-cols-2">
        <Field label={Qn.explanation} htmlFor="qn-exp" help={Qn.explanationHelp} error={errors.explanation}>
          <Textarea id="qn-exp" rows={2} dir="auto" value={d.explanation} onChange={(e) => setD({ ...d, explanation: e.target.value })} />
        </Field>
        <Field label={Qn.concept} htmlFor="qn-concept" error={errors.concept}>
          <Input id="qn-concept" dir="auto" value={d.concept} onChange={(e) => setD({ ...d, concept: e.target.value })} />
        </Field>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={busy}>
          {busy ? t.common.saving : t.common.save}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          {t.common.cancel}
        </Button>
        {onDelete && (
          <Button
            type="button"
            variant="danger"
            className="ms-auto"
            onClick={async () => {
              if (window.confirm(t.common.confirmDelete)) await onDelete();
            }}
          >
            {t.common.delete}
          </Button>
        )}
      </div>
    </form>
  );
}

export default function QuizEditor() {
  const t = useT();
  const router = useRouter();
  const errorText = useErrorText();
  const { quizId } = useParams<{ quizId: string }>();
  const Q = t.teach.quiz;
  const [quiz, setQuiz] = useState<QuizDetail | null>(null);
  const [s, setS] = useState({ title: "", lesson_id: "", mode: "ai" as "ai" | "manual", prompt: "", ai_question_count: 8 });
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [editing, setEditing] = useState<number | "new" | null>(null);

  const load = useCallback(async () => {
    try {
      const q = await api<QuizDetail>(`teach/quizzes/${quizId}`);
      setQuiz(q);
      setS({ title: q.title, lesson_id: q.lesson_id ? String(q.lesson_id) : "", mode: q.mode, prompt: q.prompt, ai_question_count: q.ai_question_count });
    } catch (e) {
      setError(errorText(e));
    }
  }, [quizId]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    load();
  }, [load]);

  if (!quiz) return error ? <Alert>{error}</Alert> : <Spinner />;

  const reloadQuestions = async () => {
    const q = await api<QuizDetail>(`teach/quizzes/${quizId}`);
    setQuiz(q);
  };

  return (
    <div className="space-y-5">
      <Link href={`/teach/${quiz.course_id}/quizzes/`} className="text-sm">
        {t.common.back}
      </Link>
      <PageTitle>{quiz.title}</PageTitle>
      <Card>
        <Alert>{error}</Alert>
        {saved && <Alert kind="ok">{t.common.saved}</Alert>}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setErrors({});
            setError("");
            setSaved(false);
            try {
              const q = await api<QuizDetail>(`teach/quizzes/${quizId}`, {
                method: "PATCH",
                body: { ...s, lesson_id: s.lesson_id ? Number(s.lesson_id) : null },
              });
              setQuiz(q);
              setSaved(true);
            } catch (err) {
              setError(errorText(err));
              if (err instanceof ApiError) setErrors(err.errors);
            }
          }}
        >
          <div className="grid gap-x-4 sm:grid-cols-2">
            <Field label={Q.title} htmlFor="q-title" error={errors.title}>
              <Input id="q-title" dir="auto" value={s.title} onChange={(e) => setS({ ...s, title: e.target.value })} />
            </Field>
            <Field label={Q.lesson} htmlFor="q-lesson" error={errors.lesson_id}>
              <select id="q-lesson" className={inputClass} value={s.lesson_id} onChange={(e) => setS({ ...s, lesson_id: e.target.value })}>
                <option value="">{Q.noLesson}</option>
                {quiz.lessons.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.title}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <ModePicker value={s.mode} onChange={(mode) => setS({ ...s, mode })} />
          {s.mode === "ai" && (
            <PromptFields
              prompt={s.prompt}
              count={s.ai_question_count}
              errors={errors}
              onChange={(prompt, ai_question_count) => setS({ ...s, prompt, ai_question_count })}
            />
          )}
          <div className="flex flex-wrap gap-2">
            <Button type="submit">{t.common.save}</Button>
            <Button
              type="button"
              variant="danger"
              className="ms-auto"
              onClick={async () => {
                if (!window.confirm(t.common.confirmDelete)) return;
                await api(`teach/quizzes/${quizId}`, { method: "DELETE" });
                router.push(`/teach/${quiz.course_id}/quizzes/`);
              }}
            >
              {t.common.delete}
            </Button>
          </div>
        </form>
      </Card>

      {quiz.mode === "manual" && (
        <section>
          <h2 className="mb-3 text-xl font-bold text-lapis">
            {Q.questions} ({quiz.questions.length})
          </h2>
          {quiz.questions.length === 0 && editing !== "new" && <p className="mb-3 text-quiet">{Q.noQuestions}</p>}
          <ol className="space-y-3">
            {quiz.questions.map((q, i) => (
              <li key={q.id}>
                <Card className="!p-4">
                  {editing === q.id ? (
                    <QuestionForm
                      initial={q}
                      onCancel={() => setEditing(null)}
                      onSave={async (d) => {
                        await api(`teach/questions/${q.id}`, { method: "PATCH", body: d });
                        await reloadQuestions();
                        setEditing(null);
                      }}
                      onDelete={async () => {
                        await api(`teach/questions/${q.id}`, { method: "DELETE" });
                        await reloadQuestions();
                        setEditing(null);
                      }}
                    />
                  ) : (
                    <div className="flex items-start gap-3">
                      <span className="font-bold text-lapis">{(i + 1).toLocaleString()}.</span>
                      <div className="min-w-0 flex-1" dir="auto">
                        <p>{q.prompt}</p>
                        {q.type === "mcq" ? (
                          <ul className="mt-1 text-sm">
                            {q.options.map((o, j) => {
                              const ok = q.correct_answer.toUpperCase() === LETTERS[j] || q.correct_answer === o;
                              return (
                                <li key={j} className={ok ? "font-semibold text-ok" : "text-quiet"}>
                                  {LETTERS[j]}) {o}
                                </li>
                              );
                            })}
                          </ul>
                        ) : (
                          <p className="mt-1 text-sm font-semibold text-ok">{[q.correct_answer, ...q.accepted_answers].join(" / ")}</p>
                        )}
                      </div>
                      <Button variant="secondary" className="shrink-0 px-3 py-1 text-sm" onClick={() => setEditing(q.id)}>
                        {t.common.edit}
                      </Button>
                    </div>
                  )}
                </Card>
              </li>
            ))}
          </ol>
          <div className="mt-3">
            {editing === "new" ? (
              <Card>
                <QuestionForm
                  initial={{
                    order: (quiz.questions.at(-1)?.order ?? 0) + 1,
                    type: "mcq",
                    prompt: "",
                    options: [],
                    correct_answer: "",
                    accepted_answers: [],
                    explanation: "",
                    concept: "",
                  }}
                  onCancel={() => setEditing(null)}
                  onSave={async (d) => {
                    await api(`teach/quizzes/${quizId}/questions`, { method: "POST", body: d });
                    await reloadQuestions();
                    setEditing(null);
                  }}
                />
              </Card>
            ) : (
              <Button onClick={() => setEditing("new")}>{t.teach.question.add}</Button>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
