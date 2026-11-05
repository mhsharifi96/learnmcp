"use client";

import { useT } from "./lang";
import { Field, Input, Textarea } from "./ui";

export function ModeBadge({ mode }: { mode: "ai" | "manual" }) {
  const t = useT();
  return (
    <span
      className={`shrink-0 rounded-md px-2 py-0.5 text-xs font-semibold ${
        mode === "ai" ? "bg-turquoise/10 text-turquoise" : "bg-lapis/10 text-lapis"
      }`}
    >
      {mode === "ai" ? t.teach.quiz.aiBadge : t.teach.quiz.manualBadge}
    </span>
  );
}

export function ModePicker({ value, onChange }: { value: "ai" | "manual"; onChange: (m: "ai" | "manual") => void }) {
  const t = useT();
  const Q = t.teach.quiz;
  const options = [
    { v: "ai" as const, label: Q.ai, help: Q.aiHelp },
    { v: "manual" as const, label: Q.manual, help: Q.manualHelp },
  ];
  return (
    <fieldset className="mb-4">
      <legend className="mb-2 font-medium">{Q.mode}</legend>
      <div className="grid gap-3 sm:grid-cols-2">
        {options.map((o) => (
          <label
            key={o.v}
            className={`flex cursor-pointer gap-3 rounded-lg border p-3 ${
              value === o.v ? "border-turquoise bg-turquoise/5" : "border-line bg-white"
            }`}
          >
            <input
              type="radio"
              name="mode"
              className="mt-1.5 accent-[var(--turquoise)]"
              checked={value === o.v}
              onChange={() => onChange(o.v)}
            />
            <span>
              <span className="block font-semibold">{o.label}</span>
              <span className="block text-sm text-quiet">{o.help}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function PromptFields({
  prompt,
  count,
  errors,
  onChange,
}: {
  prompt: string;
  count: number;
  errors: Record<string, string[]>;
  onChange: (prompt: string, count: number) => void;
}) {
  const t = useT();
  const Q = t.teach.quiz;
  return (
    <>
      <Field label={Q.prompt} htmlFor="q-prompt" error={errors.prompt}>
        <Textarea id="q-prompt" rows={4} dir="auto" value={prompt} placeholder={Q.promptPh} onChange={(e) => onChange(e.target.value, count)} />
      </Field>
      <Field label={Q.count} htmlFor="q-count" error={errors.ai_question_count}>
        <Input id="q-count" type="number" min={1} max={50} className="max-w-28" value={count} onChange={(e) => onChange(prompt, Number(e.target.value))} />
      </Field>
    </>
  );
}
