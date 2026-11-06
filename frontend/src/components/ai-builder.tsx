"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useT } from "@/components/lang";
import { Alert, Button, Card, Field, Textarea, useErrorText } from "@/components/ui";

/**
 * Instructor writes a goal -> server builds a prompt -> instructor runs it in their own AI ->
 * pastes the JSON back -> everything is created as drafts.
 */
export function AiBuilder({
  courseId,
  target,
  onImported,
}: {
  courseId: number;
  target: "lessons" | "quizzes";
  onImported: () => Promise<void>;
}) {
  const t = useT();
  const B = t.teach.builder;
  const errorText = useErrorText();
  const [open, setOpen] = useState(false);
  const [goal, setGoal] = useState("");
  const [prompt, setPrompt] = useState("");
  const [json, setJson] = useState("");
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState("");

  if (!open) {
    return (
      <Button variant="secondary" onClick={() => setOpen(true)}>
        ✨ {B.open}
      </Button>
    );
  }

  return (
    <Card className="border-lapis/30">
      <div className="mb-2 flex items-start gap-3">
        <h2 className="flex-1 text-xl font-bold text-lapis">{B.title}</h2>
        <Button variant="ghost" className="px-3 py-1 text-sm" onClick={() => setOpen(false)}>
          {B.close}
        </Button>
      </div>
      <p className="mb-4 text-sm text-quiet">{B.lead}</p>
      <Alert>{error}</Alert>
      {done && <Alert kind="ok">{done}</Alert>}

      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            const r = await api<{ prompt: string }>(`teach/courses/${courseId}/ai-prompt`, { method: "POST", body: { goal, target } });
            setPrompt(r.prompt);
            setCopied(false);
          } catch (err) {
            setError(errorText(err));
          }
          setBusy(false);
        }}
      >
        <Field label={B.goal} htmlFor="ai-goal">
          <Textarea
            id="ai-goal"
            rows={4}
            dir="auto"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder={target === "lessons" ? B.goalPhLessons : B.goalPhQuizzes}
          />
        </Field>
        <Button type="submit" disabled={busy || !goal.trim()}>
          {B.makePrompt}
        </Button>
      </form>

      {prompt && (
        <div className="mt-6 space-y-4">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-3">
              <h3 className="flex-1 font-semibold text-ink">{B.step1}</h3>
              <Button
                type="button"
                onClick={() =>
                  navigator.clipboard.writeText(prompt).then(() => {
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  })
                }
              >
                {copied ? B.copied : B.copyPrompt}
              </Button>
            </div>
            <Textarea readOnly rows={6} dir="ltr" value={prompt} className="font-mono text-xs" onFocus={(e) => e.target.select()} />
          </div>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              setDone("");
              try {
                const r = await api<{ lessons: number; quizzes: number }>(`teach/courses/${courseId}/import`, {
                  method: "POST",
                  body: { json },
                });
                await onImported();
                setDone(B.imported(r.lessons, r.quizzes));
                setJson("");
              } catch (err) {
                setError(errorText(err));
              }
              setBusy(false);
            }}
          >
            <Field label={B.step2} htmlFor="ai-json">
              <Textarea
                id="ai-json"
                rows={8}
                dir="ltr"
                className="font-mono text-xs"
                value={json}
                onChange={(e) => setJson(e.target.value)}
                placeholder={B.jsonPh}
              />
            </Field>
            <Button type="submit" disabled={busy || !json.trim()}>
              {busy ? B.importing : B.import}
            </Button>
          </form>
        </div>
      )}
    </Card>
  );
}

/** "Publish all drafts" bar, shown when the class has drafts. */
export function DraftBar({ courseId, count, onDone }: { courseId: number; count: number; onDone: () => Promise<void> }) {
  const t = useT();
  const errorText = useErrorText();
  const [error, setError] = useState("");
  if (!count) return null;
  return (
    <div className="rounded-xl border border-saffron/40 bg-saffron/10 p-4">
      <Alert>{error}</Alert>
      <div className="flex flex-wrap items-center gap-3">
        <p className="flex-1 text-sm text-ink">{t.teach.draftsLead}</p>
        <Button
          onClick={async () => {
            if (!window.confirm(t.teach.publishAllConfirm)) return;
            try {
              await api(`teach/courses/${courseId}/publish`, { method: "POST", body: {} });
              await onDone();
            } catch (err) {
              setError(errorText(err));
            }
          }}
        >
          {t.teach.publishAll(count)}
        </Button>
      </div>
    </div>
  );
}
