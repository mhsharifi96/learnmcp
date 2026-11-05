"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { CourseDetail } from "@/lib/types";
import { useT } from "@/components/lang";
import { Alert, CopyBox, Spinner, useErrorText } from "@/components/ui";
import { CourseContext } from "./course-context";

export default function CourseLayout({ children }: { children: React.ReactNode }) {
  const t = useT();
  const errorText = useErrorText();
  const { courseId } = useParams<{ courseId: string }>();
  const path = usePathname();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [error, setError] = useState("");
  const [origin, setOrigin] = useState("");

  const reload = useCallback(async () => {
    try {
      setCourse(await api<CourseDetail>(`teach/courses/${courseId}`));
    } catch (e) {
      setError(errorText(e));
    }
  }, [courseId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setOrigin(window.location.origin);
    reload();
  }, [reload]);

  if (error) return <Alert>{error}</Alert>;
  if (!course) return <Spinner />;

  const base = `/teach/${course.id}/`;
  const tabs = [
    { href: base, label: t.teach.tabs.overview },
    { href: `${base}lessons/`, label: `${t.teach.tabs.lessons} (${course.lessons.length})` },
    { href: `${base}quizzes/`, label: `${t.teach.tabs.quizzes} (${course.quizzes.length})` },
    { href: `${base}review/`, label: t.teach.tabs.review },
    { href: `${base}settings/`, label: t.teach.tabs.settings },
  ];

  return (
    <CourseContext.Provider value={{ course, reload }}>
      <h1 className="font-display text-3xl leading-tight text-lapis sm:text-4xl">{course.title}</h1>
      <div className="mt-3 max-w-2xl">
        <p className="mb-1 text-sm text-quiet">
          {t.teach.invite} · {t.teach.code}{" "}
          <span dir="ltr" className="font-mono text-ink">
            {course.join_code}
          </span>
        </p>
        {origin && <CopyBox id="invite" value={`${origin}/join/${course.join_code}/`} />}
      </div>
      <nav className="-mx-4 mt-6 overflow-x-auto px-4" aria-label="class">
        <ul className="flex min-w-max gap-1 border-b border-line">
          {tabs.map((tab) => {
            const active = tab.href === base ? path === base : path.startsWith(tab.href);
            return (
              <li key={tab.href}>
                <Link
                  href={tab.href}
                  aria-current={active ? "page" : undefined}
                  className={`-mb-px block border-b-2 px-3 py-2 hover:no-underline ${
                    active ? "border-saffron font-semibold text-lapis" : "border-transparent text-quiet hover:text-ink"
                  }`}
                >
                  {tab.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="pt-6">{children}</div>
    </CourseContext.Provider>
  );
}
