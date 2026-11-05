"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/components/lang";
import { Alert, Button, Card, Field, Input, Textarea, useErrorText } from "@/components/ui";
import { useCourse } from "../course-context";

export default function Settings() {
  const t = useT();
  const router = useRouter();
  const errorText = useErrorText();
  const { course, reload } = useCourse();
  const [d, setD] = useState({ title: course.title, description: course.description });
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

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
          <Button type="submit">{t.common.save}</Button>
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
