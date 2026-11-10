"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Cover } from "@/components/cover";
import { useT } from "@/components/lang";
import { Alert, ButtonLink, Card, Chip, Icon, PageTitle, Spinner, inputClass, useErrorText } from "@/components/ui";

export type Klass = {
  id: number;
  code: string;
  title: string;
  description: string;
  category?: string;
  instructor: string;
  instructor_id: number;
  lessons: number;
  students: number;
  joined: boolean;
  image?: string | null;
  theme?: string;
};

const MIN_SHOWN_STUDENTS = 10;
const CATEGORY_ORDER = ["ai", "code", "language", "office", "design", "marketing", "academic", "engineering", "finance", "career", "skills", "hobby"];

export default function Classes({ initial = null }: { initial?: Klass[] | null }) {
  const t = useT();
  const errorText = useErrorText();
  const [items, setItems] = useState<Klass[] | null>(initial);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [teacher, setTeacher] = useState("");
  const [category, setCategory] = useState("");

  // Open a topic from the URL (?category=ai) so each topic has a shareable link.
  useEffect(() => {
    const c = new URLSearchParams(window.location.search).get("category");
    if (c) setCategory(c);
  }, []);
  const pickCategory = (c: string) => {
    setCategory(c);
    const u = new URL(window.location.href);
    if (c) u.searchParams.set("category", c);
    else u.searchParams.delete("category");
    window.history.replaceState(null, "", u);
  };

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

  const categories = useMemo(() => {
    const m = new Map<string, number>();
    for (const c of items ?? []) if (c.category) m.set(c.category, (m.get(c.category) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => {
      const ia = CATEGORY_ORDER.indexOf(a[0]), ib = CATEGORY_ORDER.indexOf(b[0]);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    });
  }, [items]);

  const shown = useMemo(() => {
    const needle = q.trim().toLocaleLowerCase();
    return (items ?? []).filter(
      (c) =>
        (!teacher || String(c.instructor_id) === teacher) &&
        (!category || c.category === category) &&
        (!needle || `${c.title} ${c.description} ${c.instructor}`.toLocaleLowerCase().includes(needle)),
    );
  }, [items, q, teacher, category]);

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

      {categories.length > 0 && (
        <nav aria-label={t.catalog.allCategories} className="flex flex-wrap gap-2">
          <button type="button" onClick={() => pickCategory("")} className={`rounded-full border px-3 py-1 text-sm ${!category ? "border-lapis bg-lapis text-white" : "border-line bg-surface hover:border-lapis"}`}>
            {t.catalog.allCategories}
          </button>
          {categories.map(([key, n]) => (
            <button key={key} type="button" onClick={() => pickCategory(key)} className={`rounded-full border px-3 py-1 text-sm ${category === key ? "border-lapis bg-lapis text-white" : "border-line bg-surface hover:border-lapis"}`}>
              {`${t.catalog.categories[key] ?? key} (${n})`}
            </button>
          ))}
        </nav>
      )}

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
          <Card key={c.id} className="flex flex-col overflow-hidden !p-5">
            <Link href={c.joined ? "/me/" : `/join/${c.code}/`} className="-mx-5 -mt-5 mb-4 block" tabIndex={-1} aria-hidden>
              <Cover image={c.image} theme={c.theme} />
            </Link>
            <div className="mb-1 flex items-start justify-between gap-3">
              <h2 className="font-display text-xl text-lapis" dir="auto">
                <Link href={c.joined ? "/me/" : `/join/${c.code}/`} className="text-inherit hover:no-underline">
                  {c.title}
                </Link>
              </h2>
              {c.joined ? <Chip tone="ok">{t.catalog.joined}</Chip> : <Chip tone="ok">{t.catalog.free}</Chip>}
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
              {c.category && t.catalog.categories[c.category] && (
                <button type="button" onClick={() => pickCategory(c.category!)}>
                  <Chip tone="info">{t.catalog.categories[c.category]}</Chip>
                </button>
              )}
              <Chip>{t.catalog.lessons(c.lessons)}</Chip>
              {/* Small numbers read as "nobody joined": show a "new" badge until the class has a real crowd. */}
              {c.students >= MIN_SHOWN_STUDENTS ? <Chip>{t.catalog.students(c.students)}</Chip> : <Chip tone="info">{t.catalog.newCourse}</Chip>}
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
