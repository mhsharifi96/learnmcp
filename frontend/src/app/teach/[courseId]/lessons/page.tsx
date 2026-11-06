"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { LESSON_KINDS, type Lesson, type LessonKind } from "@/lib/types";
import { useT } from "@/components/lang";
import { Alert, Button, Card, Chip, Field, Input, Textarea, useErrorText } from "@/components/ui";
import { AiBuilder, DraftBar } from "@/components/ai-builder";
import { useCourse } from "../course-context";

type Draft = Omit<Lesson, "id">;
const empty = (order: number): Draft => ({ order, title: "", kind: "general", brief: "", objectives: "", content: "", teaching_notes: "" });

function LessonForm({
  initial,
  onSave,
  onCancel,
  onDelete,
}: {
  initial: Draft;
  onSave: (d: Draft) => Promise<void>;
  onCancel: () => void;
  onDelete?: () => Promise<void>;
}) {
  const t = useT();
  const errorText = useErrorText();
  const [d, setD] = useState(initial);
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const L = t.teach.lesson;
  const set = (k: keyof Draft) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setD({ ...d, [k]: k === "order" ? Number(e.target.value) : e.target.value });

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setErrors({});
        setError("");
        try {
          await onSave(d);
        } catch (err) {
          setError(errorText(err));
          if (err instanceof ApiError) setErrors(err.errors);
        }
        setBusy(false);
      }}
    >
      <Alert>{error}</Alert>
      <div className="grid gap-x-4 sm:grid-cols-[1fr_6rem]">
        <Field label={L.title} htmlFor="l-title" error={errors.title}>
          <Input id="l-title" value={d.title} onChange={set("title")} required />
        </Field>
        <Field label={L.order} htmlFor="l-order" error={errors.order}>
          <Input id="l-order" type="number" min={1} value={d.order} onChange={set("order")} />
        </Field>
      </div>
      <fieldset className="mb-4">
        <legend className="mb-2 font-medium text-ink">{L.kind}</legend>
        <div className="flex flex-wrap gap-2" role="radiogroup">
          {LESSON_KINDS.map((k) => (
            <button
              key={k}
              type="button"
              role="radio"
              aria-checked={d.kind === k}
              onClick={() => setD({ ...d, kind: k as LessonKind })}
              className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
                d.kind === k ? "border-lapis bg-lapis text-white" : "border-line bg-surface text-ink hover:border-lapis"
              }`}
            >
              {t.kinds[k].label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-sm text-quiet">{t.kinds[d.kind].help}</p>
        {errors.kind && <p className="mt-1 text-sm text-danger">{errors.kind.join(" ")}</p>}
      </fieldset>
      <Field label={L.brief} htmlFor="l-brief" help={L.briefHelp} error={errors.brief}>
        <Textarea id="l-brief" rows={4} dir="auto" value={d.brief} onChange={set("brief")} placeholder={t.kinds[d.kind].ph} />
      </Field>
      <details className="mb-4 rounded-lg border border-line px-4 py-2" open={!!(d.content || d.objectives || d.teaching_notes)}>
        <summary className="cursor-pointer py-1 font-medium text-lapis">
          {L.objectives} · {L.content} · {L.notes} <span className="text-sm text-quiet">({t.common.optional})</span>
        </summary>
        <div className="pt-3">
          <Field label={L.objectives} htmlFor="l-obj" help={L.objectivesHelp} error={errors.objectives}>
            <Textarea id="l-obj" rows={3} dir="auto" value={d.objectives} onChange={set("objectives")} />
          </Field>
          <Field label={L.content} htmlFor="l-content" help={L.contentHelp} error={errors.content}>
            <Textarea id="l-content" rows={8} dir="auto" value={d.content} onChange={set("content")} />
          </Field>
          <Field label={L.notes} htmlFor="l-notes" help={L.notesHelp} error={errors.teaching_notes}>
            <Textarea id="l-notes" rows={3} dir="auto" value={d.teaching_notes} onChange={set("teaching_notes")} />
          </Field>
        </div>
      </details>
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

export default function Lessons() {
  const t = useT();
  const { course, reload } = useCourse();
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const L = t.teach.lesson;
  const nextOrder = (course.lessons.at(-1)?.order ?? 0) + 1;
  const drafts = course.lessons.filter((l) => l.draft).length + course.quizzes.filter((q) => q.draft).length;
  const setDraft = async (id: number, draft: boolean) => {
    await api(`teach/lessons/${id}`, { method: "PATCH", body: { draft } });
    await reload();
  };

  return (
    <div className="space-y-4">
      <AiBuilder courseId={course.id} target="lessons" onImported={reload} />
      <DraftBar courseId={course.id} count={drafts} onDone={reload} />
      {course.lessons.length === 0 && editing !== "new" && <p className="text-quiet">{L.empty}</p>}
      <ol className="space-y-3">
        {course.lessons.map((l) => {
          const quizzes = course.quizzes.filter((q) => q.lesson_id === l.id);
          return (
            <li key={l.id}>
              <Card className={`!p-4 sm:!p-5 ${l.draft ? "border-dashed border-saffron/60" : ""}`}>
                {editing === l.id ? (
                  <LessonForm
                    initial={l}
                    onCancel={() => setEditing(null)}
                    onSave={async (d) => {
                      await api(`teach/lessons/${l.id}`, { method: "PATCH", body: d });
                      await reload();
                      setEditing(null);
                    }}
                    onDelete={async () => {
                      await api(`teach/lessons/${l.id}`, { method: "DELETE" });
                      await reload();
                      setEditing(null);
                    }}
                  />
                ) : (
                  <div className="flex items-start gap-4">
                    <span className="mt-0.5 min-w-8 rounded-md bg-mist px-2 text-center font-bold text-lapis">
                      {l.order.toLocaleString()}
                    </span>
                    <div className="min-w-0 flex-1">
                      <h3 className="flex flex-wrap items-center gap-2 font-semibold text-ink">
                        <span dir="auto">{l.title}</span>
                        {l.kind !== "general" && <Chip tone="info">{t.kinds[l.kind]?.label}</Chip>}
                        {l.draft && <Chip tone="warn">{t.teach.draft}</Chip>}
                      </h3>
                      <p className="line-clamp-2 text-sm text-quiet" dir="auto">
                        {l.brief || l.content}
                      </p>
                      <p className="mt-1 text-xs text-turquoise">
                        {l.content.trim() ? L.written : L.aiBuilt}
                        {quizzes.length > 0 && ` · ${quizzes.map((q) => q.title).join("، ")}`}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col gap-2">
                      <Button variant="secondary" className="px-3 py-1 text-sm" onClick={() => setEditing(l.id)}>
                        {t.common.edit}
                      </Button>
                      {l.draft && (
                        <Button className="px-3 py-1 text-sm" onClick={() => setDraft(l.id, false)}>
                          {t.teach.publish}
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </Card>
            </li>
          );
        })}
      </ol>
      {editing === "new" ? (
        <Card>
          <h2 className="mb-3 text-xl font-bold text-lapis">{L.add}</h2>
          <LessonForm
            initial={empty(nextOrder)}
            onCancel={() => setEditing(null)}
            onSave={async (d) => {
              await api(`teach/courses/${course.id}/lessons`, { method: "POST", body: d });
              await reload();
              setEditing(null);
            }}
          />
        </Card>
      ) : (
        <Button onClick={() => setEditing("new")}>{L.add}</Button>
      )}
    </div>
  );
}
