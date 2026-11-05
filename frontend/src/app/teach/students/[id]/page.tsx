"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useFormatDate, useT } from "@/components/lang";
import { Alert, Card, PageTitle, Spinner, StatusTag, useErrorText } from "@/components/ui";

type Data = {
  course: { id: number; title: string };
  student: { name: string; email: string };
  joined_at: string;
  last_activity_at: string | null;
  attempts: {
    id: number;
    quiz: string;
    ai_generated: boolean;
    started_at: string;
    finished_at: string | null;
    score_percent: number | null;
    answers: { id: number; question: string; answer: string; status: string; expected: string; concept: string; ai_generated: boolean }[];
  }[];
  events: { label: string; lesson: string | null; concept: string; note: string; client: string; created_at: string }[];
};

export default function StudentDetail() {
  const t = useT();
  const fmt = useFormatDate();
  const errorText = useErrorText();
  const { id } = useParams<{ id: string }>();
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Data>(`teach/students/${id}`).then(setD).catch((e) => setError(errorText(e)));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <Alert>{error}</Alert>;
  if (!d) return <Spinner />;

  return (
    <div className="space-y-5">
      <Link href={`/teach/${d.course.id}/`} className="text-sm">
        {t.common.back} · {d.course.title}
      </Link>
      <PageTitle lead={<span dir="ltr">{d.student.email}</span>}>{d.student.name}</PageTitle>
      <p className="-mt-4 text-sm text-quiet">
        {t.me.joined}: {fmt(d.joined_at, false)} · {t.teach.lastActivity}: {fmt(d.last_activity_at)}
      </p>
      <Card>
        <h2 className="mb-3 text-xl font-bold text-lapis">{t.teach.student.attempts}</h2>
        {d.attempts.length === 0 && <p className="text-quiet">{t.me.noAttempts}</p>}
        {d.attempts.map((a) => (
          <div key={a.id} className="mb-5">
            <p>
              <strong>{a.quiz}</strong> · {fmt(a.started_at)} · {a.finished_at ? `${a.score_percent}%` : t.me.notFinished}
            </p>
            {a.answers.length > 0 && (
              <div className="overflow-x-auto">
                <table className="mt-1">
                  <thead>
                    <tr>
                      <th>{t.me.question}</th>
                      <th>{t.me.yourAnswer}</th>
                      <th>{t.teach.student.expected}</th>
                      <th>{t.me.result}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.answers.map((x) => (
                      <tr key={x.id}>
                        <td dir="auto">
                          {x.question}
                          {x.concept && <span className="block text-xs text-quiet">{x.concept}</span>}
                        </td>
                        <td dir="auto">{x.answer}</td>
                        <td dir="auto">{x.expected}</td>
                        <td>
                          <StatusTag status={x.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
      </Card>
      <Card>
        <h2 className="mb-3 text-xl font-bold text-lapis">{t.teach.student.events}</h2>
        <div className="overflow-x-auto">
          <table>
            <tbody>
              {d.events.length === 0 && (
                <tr>
                  <td className="text-quiet">{t.me.nothing}</td>
                </tr>
              )}
              {d.events.map((ev, i) => (
                <tr key={i}>
                  <td className="whitespace-nowrap">{fmt(ev.created_at)}</td>
                  <td dir="ltr" className="text-start">{ev.label}</td>
                  <td dir="auto">{[ev.lesson, ev.concept, ev.note && `“${ev.note}”`].filter(Boolean).join(" · ")}</td>
                  <td>{ev.client || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
