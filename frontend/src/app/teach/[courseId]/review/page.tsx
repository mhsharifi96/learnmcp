"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useT } from "@/components/lang";
import { Alert, Button, Card, Spinner, useErrorText } from "@/components/ui";
import { useCourse } from "../course-context";

type Item = { id: number; question: string; answer: string; expected: string; accepted: string[]; quiz: string; student: string };

export default function Review() {
  const t = useT();
  const errorText = useErrorText();
  const { course } = useCourse();
  const R = t.teach.review;
  const [items, setItems] = useState<Item[] | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api<{ answers: Item[] }>(`teach/courses/${course.id}/review`).then((d) => setItems(d.answers)).catch((e) => setError(errorText(e)));
  }, [course.id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(load, [load]);

  if (error) return <Alert>{error}</Alert>;
  if (!items) return <Spinner />;

  const mark = async (id: number, status: "correct" | "incorrect") => {
    try {
      await api(`teach/answers/${id}`, { method: "PATCH", body: { status } });
      setItems((xs) => xs!.filter((x) => x.id !== id));
    } catch (e) {
      setError(errorText(e));
    }
  };

  return (
    <div className="space-y-4">
      <p className="max-w-prose text-quiet">{R.lead}</p>
      {items.length === 0 && <p className="font-semibold text-ok">{R.empty}</p>}
      {items.map((a) => (
        <Card key={a.id} className="!p-4">
          <p className="text-sm text-quiet">
            {a.student} · {a.quiz}
          </p>
          <p className="mt-1" dir="auto">
            {a.question}
          </p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            <div className="rounded-lg bg-mist px-3 py-2">
              <span className="block text-xs text-quiet">{t.me.yourAnswer}</span>
              <span dir="auto">{a.answer}</span>
            </div>
            <div className="rounded-lg bg-ok/5 px-3 py-2">
              <span className="block text-xs text-quiet">{R.expected}</span>
              <span dir="auto">{[a.expected, ...a.accepted].join(" / ")}</span>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <Button className="!bg-ok !text-white" onClick={() => mark(a.id, "correct")}>
              {R.markCorrect}
            </Button>
            <Button variant="danger" onClick={() => mark(a.id, "incorrect")}>
              {R.markIncorrect}
            </Button>
          </div>
        </Card>
      ))}
    </div>
  );
}
