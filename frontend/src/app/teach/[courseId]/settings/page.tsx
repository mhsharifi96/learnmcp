"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/components/lang";
import { Alert, Button, Card, Chip, Field, Input, Textarea, useErrorText } from "@/components/ui";
import { useCourse } from "../course-context";

export default function Settings() {
  const t = useT();
  const router = useRouter();
  const errorText = useErrorText();
  const { course, reload } = useCourse();
  const [d, setD] = useState({ title: course.title, description: course.description, listed: course.listed ?? true });
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [days, setDays] = useState(String(course.reminder_after_days ?? 0));
  const [rErrors, setRErrors] = useState<Record<string, string[]>>({});
  const [rSaved, setRSaved] = useState(false);

  return (
    <div className="space-y-5">
      <Card>
        <h2 className="mb-3 text-xl font-bold text-lapis">{t.teach.settings.title}</h2>
        <Alert>{error}</Alert>
        {saved && <Alert kind="ok">{t.common.saved}</Alert>}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setErrors({});
            setError("");
            setSaved(false);
            try {
              await api(`teach/courses/${course.id}`, { method: "PATCH", body: d });
              await reload();
              setSaved(true);
            } catch (err) {
              setError(errorText(err));
              if (err instanceof ApiError) setErrors(err.errors);
            }
          }}
        >
          <Field label={t.teach.classTitle} htmlFor="c-title" error={errors.title}>
            <Input id="c-title" dir="auto" value={d.title} onChange={(e) => setD({ ...d, title: e.target.value })} />
          </Field>
          <Field label={t.teach.description} htmlFor="c-desc" error={errors.description}>
            <Textarea id="c-desc" rows={4} dir="auto" value={d.description} onChange={(e) => setD({ ...d, description: e.target.value })} />
          </Field>
          <label className="mb-4 flex items-start gap-3">
            <input
              type="checkbox"
              className="mt-1.5 h-4 w-4 accent-[var(--turquoise)]"
              checked={d.listed}
              onChange={(e) => setD({ ...d, listed: e.target.checked })}
            />
            <span>
              {t.teach.settings.listedLabel}
              <span className="block text-sm text-quiet">{t.teach.settings.listedHelp}</span>
            </span>
          </label>
          <Button type="submit">{t.common.save}</Button>
        </form>
      </Card>
      <Card>
        <h2 className="mb-1 flex flex-wrap items-center gap-2 text-xl font-bold text-lapis">
          {t.teach.settings.reminderTitle}
          <Chip tone={course.reminder_after_days > 0 ? "ok" : "default"}>
            {course.reminder_after_days > 0 ? t.teach.settings.reminderOn(course.reminder_after_days) : t.teach.settings.reminderOff}
          </Chip>
        </h2>
        <p className="mb-3 text-sm text-quiet">{t.teach.settings.reminderHelp}</p>
        {rSaved && <Alert kind="ok">{t.common.saved}</Alert>}
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setRErrors({});
            setRSaved(false);
            try {
              await api(`teach/courses/${course.id}`, { method: "PATCH", body: { reminder_after_days: Number(days) || 0 } });
              await reload();
              setRSaved(true);
            } catch (err) {
              setError(errorText(err));
              if (err instanceof ApiError) setRErrors(err.errors);
            }
          }}
        >
          <div className="w-full max-w-sm">
            <Field label={t.teach.settings.reminderLabel} htmlFor="c-remind" error={rErrors.reminder_after_days}>
              <Input id="c-remind" type="number" min={0} max={365} dir="ltr" value={days} onChange={(e) => setDays(e.target.value)} />
            </Field>
          </div>
          <div className="mb-4">
            <Button type="submit">{t.common.save}</Button>
          </div>
        </form>
      </Card>
      <Card className="border-danger/40">
        <h2 className="mb-2 text-xl font-bold text-danger">{t.teach.settings.danger}</h2>
        <p className="mb-3 text-quiet">{t.teach.settings.dangerText}</p>
        <Button
          variant="danger"
          onClick={async () => {
            if (!window.confirm(t.teach.settings.deleteConfirm)) return;
            try {
              await api(`teach/courses/${course.id}`, { method: "DELETE" });
              router.push("/teach/");
            } catch (err) {
              setError(errorText(err));
            }
          }}
        >
          {t.teach.settings.danger}
        </Button>
      </Card>
    </div>
  );
}
