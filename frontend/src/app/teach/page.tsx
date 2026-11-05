"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { CourseSummary } from "@/lib/types";
import { useT } from "@/components/lang";
import { Alert, Button, Card, Field, Input, PageTitle, Spinner, Textarea, useErrorText } from "@/components/ui";

export default function Classes() {
  const t = useT();
  const router = useRouter();
  const errorText = useErrorText();
  const [courses, setCourses] = useState<CourseSummary[] | null>(null);
  const [error, setError] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ title: "", description: "" });
  const [errors, setErrors] = useState<Record<string, string[]>>({});

  useEffect(() => {
    api<{ courses: CourseSummary[] }>("teach/courses")
      .then((d) => {
        setCourses(d.courses);
        if (d.courses.length === 0) setShowNew(true);
      })
      .catch((e) => setError(errorText(e)));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!courses && !error) return <Spinner />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <PageTitle>{t.teach.classes}</PageTitle>
        {!showNew && <Button onClick={() => setShowNew(true)}>{t.teach.newClass}</Button>}
      </div>
      <Alert>{error}</Alert>
      {showNew && (
        <Card>
          <h2 className="mb-3 text-xl font-bold text-lapis">{t.teach.newClass}</h2>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setErrors({});
              try {
                const c = await api<CourseSummary>("teach/courses", { method: "POST", body: form });
                router.push(`/teach/${c.id}/lessons/`);
              } catch (err) {
                setError(errorText(err));
                if (err instanceof ApiError) setErrors(err.errors);
              }
            }}
          >
            <Field label={t.teach.classTitle} htmlFor="title" error={errors.title}>
              <Input id="title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            </Field>
            <Field label={t.teach.description} htmlFor="desc" error={errors.description}>
              <Textarea id="desc" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
            <div className="flex gap-2">
              <Button type="submit" disabled={!form.title.trim()}>
                {t.teach.create}
              </Button>
              {courses && courses.length > 0 && (
                <Button type="button" variant="ghost" onClick={() => setShowNew(false)}>
                  {t.common.cancel}
                </Button>
              )}
            </div>
          </form>
        </Card>
      )}
      {courses?.length === 0 && !showNew && <p className="text-quiet">{t.teach.emptyClasses}</p>}
      <ul className="grid gap-4 sm:grid-cols-2">
        {courses?.map((c) => (
          <li key={c.id}>
            <Link
              href={`/teach/${c.id}/`}
              className="block h-full rounded-xl border border-line bg-surface p-5 text-ink hover:border-lapis hover:no-underline"
            >
              <span className="block font-display text-2xl text-lapis">{c.title}</span>
              <span className="mt-1 block text-sm text-quiet">
                {c.students ?? 0} {t.teach.students} · {c.lessons ?? 0} {t.teach.lessons} ·{" "}
                <span dir="ltr" className="font-mono">
                  {c.join_code}
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
