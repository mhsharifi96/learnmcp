"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useT } from "@/components/lang";
import { Alert, ButtonLink, Card, Chip, Icon, PageTitle, Spinner, inputClass, useErrorText } from "@/components/ui";

export type Klass = {
  id: number;
  code: string;
  title: string;
  description: string;
  instructor: string;
  instructor_id: number;
  lessons: number;
  students: number;
  joined: boolean;
};

export default function Classes({ initial = null }: { initial?: Klass[] | null }) {
  const t = useT();
  const errorText = useErrorText();
  const [items, setItems] = useState<Klass[] | null>(initial);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [teacher, setTeacher] = useState("");

  useEffect(() => {
    api<{ classes: Klass[] }>("classes")
      .then((d) => setItems(d.classes))
      .catch((e) => setError(errorText(e)));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const instructors = useMemo(() => {
    const m = new Map<number, { name: string; count: number }>();
    for (const c of items ?? []) {
      const cur = m.get(c.instructor_id) ?? { name: c.instructor, count: 0 };
      cur.count += 1;
      m.set(c.instructor_id, cur);
    }
    return [...m.entries()].sort((a, b) => a[1].name.localeCompare(b[1].name));
  }, [items]);

  const shown = useMemo(() => {
    const needle = q.trim().toLocaleLowerCase();
    return (items ?? []).filter(
      (c) =>
        (!teacher || String(c.instructor_id) === teacher) &&
        (!needle || `${c.title} ${c.description} ${c.instructor}`.toLocaleLowerCase().includes(needle)),
    );
  }, [items, q, teacher]);

  if (error) return <Alert>{error}</Alert>;
  if (!items) return <Spinner />;

  return (
    <div className="space-y-5">
      <PageTitle lead={t.catalog.lead}>{t.catalog.title}</PageTitle>

      <div className="grid gap-3 sm:grid-cols-[1fr_16rem]">
        <label className="relative block">
          <span className="sr-only">{t.catalog.search}</span>
          <input
            type="search"
            dir="auto"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t.catalog.search}
            className={inputClass}
          />
        </label>
        <label className="block">
          <span className="sr-only">{t.catalog.instructor}</span>
          <select value={teacher} onChange={(e) => setTeacher(e.target.value)} className={inputClass}>
            <option value="">{t.catalog.allInstructors}</option>
            {instructors.map(([id, v]) => (
              <option key={id} value={id}>
                {`${v.name} (${v.count})`}
              </option>
            ))}
          </select>
        </label>
      </div>

      {instructors.length > 1 && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setTeacher("")}
            className={`rounded-full border px-3 py-1 text-sm ${!teacher ? "border-lapis bg-lapis text-white" : "border-line bg-surface hover:border-lapis"}`}
          >
            {t.catalog.allInstructors}
          </button>
          {instructors.map(([id, v]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTeacher(String(id))}
              className={`rounded-full border px-3 py-1 text-sm ${teacher === String(id) ? "border-lapis bg-lapis text-white" : "border-line bg-surface hover:border-lapis"}`}
            >
              {v.name}
            </button>
          ))}
        </div>
      )}

      <p className="text-sm text-quiet">{t.catalog.count(shown.length)}</p>
      {shown.length === 0 && (
        <Card>
          <p className="text-quiet">{t.catalog.empty}</p>
        </Card>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        {shown.map((c) => (
          <Card key={c.id} className="flex flex-col !p-5">
            <div className="mb-1 flex items-start justify-between gap-3">
              <h2 className="font-display text-xl text-lapis" dir="auto">
                {c.title}
              </h2>
              {c.joined && <Chip tone="ok">{t.catalog.joined}</Chip>}
            </div>
            <p className="mb-2 flex items-center gap-1.5 text-sm text-quiet">
              <Icon name="users" className="h-4 w-4" />
              <button type="button" className="hover:text-lapis hover:underline" onClick={() => setTeacher(String(c.instructor_id))}>
                {c.instructor}
              </button>
            </p>
            {c.description && (
              <p className="mb-3 line-clamp-3 text-[0.95rem]" dir="auto">
                {c.description}
              </p>
            )}
            <p className="mb-4 mt-auto flex flex-wrap gap-2 text-sm">
              <Chip>{t.catalog.lessons(c.lessons)}</Chip>
              <Chip>{t.catalog.students(c.students)}</Chip>
            </p>
            {c.joined ? (
              <ButtonLink href="/me/" variant="secondary">
                {t.catalog.open}
              </ButtonLink>
            ) : (
              <ButtonLink href={`/join/${c.code}/`}>{t.catalog.join}</ButtonLink>
            )}
          </Card>
        ))}
      </div>
      <p className="text-sm text-quiet">
        <Link href="/join/">{t.nav.join}</Link>
      </p>
    </div>
  );
}
