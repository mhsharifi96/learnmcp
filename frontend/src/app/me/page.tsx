"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useFormatDate, useT } from "@/components/lang";
import { VerifyNotice } from "@/components/student-auth-form";
import type { StudentAccount } from "@/lib/types";
import { Alert, Button, ButtonLink, Card, Chip, ComingSoon, PageTitle, SectionTitle, Spinner, StatusTag, useErrorText } from "@/components/ui";

type Attempt = {
  id: number;
  quiz: string;
  started_at: string;
  finished_at: string | null;
  score_percent: number | null;
  answers: { id: number; question: string; answer: string; status: string }[];
};
type Ev = { label: string; lesson: string | null; concept: string; note: string; client: string; created_at: string };
type Enr = {
  id: number;
  course: string;
  instructor: string;
  student: { name: string; email: string };
  joined_at: string;
  consent_at: string;
  token_hint: string;
  attempts: Attempt[];
  events: Ev[];
};

export default function Me() {
  const t = useT();
  const fmt = useFormatDate();
  const errorText = useErrorText();
  const router = useRouter();
  const [data, setData] = useState<Enr[] | null>(null);
  const [student, setStudent] = useState<StudentAccount | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(() => {
    api<{ enrollments: Enr[]; student: StudentAccount | null }>("me")
      .then((d) => {
        setStudent(d.student);
        setData(d.enrollments);
      }).catch((e) => setError(errorText(e)));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(load, [load]);

  if (error) return <Alert>{error}</Alert>;
  if (!data) return <Spinner />;

  return (
    <div className="space-y-5">
      <PageTitle lead={t.me.lead}>{t.me.title}</PageTitle>
      <Alert kind="ok">{notice}</Alert>
      {student ? (
        <Card>
          <SectionTitle
            icon="users"
            aside={
              <Button
                variant="ghost"
                className="px-2 py-1 text-sm"
                onClick={async () => {
                  await api("auth/logout", { method: "POST" }).catch(() => undefined);
                  router.push("/");
                  router.refresh();
                }}
              >
                {t.student.logout}
              </Button>
            }
          >
            {t.student.account}
          </SectionTitle>
          <p className="mb-3 flex flex-wrap items-center gap-2">
            <strong>{student.name}</strong>
            <span dir="ltr" className="text-quiet">
              {student.email}
            </span>
            <Chip tone={student.email_verified ? "ok" : "warn"}>
              {student.email_verified ? t.student.verifiedChip : t.student.unverifiedChip}
            </Chip>
          </p>
          {!student.email_verified && <VerifyNotice email={student.email} />}
          <label className="mt-3 flex items-start gap-3">
            <input
              type="checkbox"
              className="mt-1.5 h-4 w-4 accent-[var(--turquoise)]"
              checked={student.email_reminders}
              onChange={async (ev) => {
                try {
                  const r = await api<{ student: StudentAccount }>("me/settings", {
                    method: "PATCH",
                    body: { email_reminders: ev.target.checked },
                  });
                  setStudent(r.student);
                } catch (err) {
                  setError(errorText(err));
                }
              }}
            />
            <span>
              {t.student.reminders}
              <span className="block text-sm text-quiet">{t.student.remindersHelp}</span>
            </span>
          </label>
        </Card>
      ) : (
        <Card>
          <p className="mb-3">{data.length > 0 ? t.student.legacy : t.student.needAccount}</p>
          <div className="flex flex-wrap gap-3">
            <ButtonLink href="/student/signup/">{t.student.signup}</ButtonLink>
            <ButtonLink href="/student/login/" variant="secondary">
              {t.student.login}
            </ButtonLink>
          </div>
        </Card>
      )}
      {data.length === 0 && (
        <Card>
          <p className="mb-2">{t.me.empty}</p>
          <p className="flex flex-wrap gap-4">
            <Link href="/join/">{t.me.joinLink}</Link>
            <Link href="/me/restore/">{t.me.restoreLink}</Link>
          </p>
        </Card>
      )}
      {data.map((e) => (
        <Card key={e.id}>
          <h2 className="font-display text-2xl text-lapis">{e.course}</h2>
          <dl className="mt-2 grid gap-x-6 gap-y-1 text-sm text-quiet sm:grid-cols-2">
            <div>
              {t.me.instructor}: <span className="text-ink">{e.instructor}</span>
            </div>
            <div>
              {e.student.name} (<span dir="ltr">{e.student.email}</span>)
            </div>
            <div>
              {t.me.joined}: {fmt(e.joined_at, false)}
            </div>
            <div>
              {t.me.consent}: {fmt(e.consent_at)}
            </div>
            <div>
              {t.me.linkEnds}: <code dir="ltr">…{e.token_hint}</code>
            </div>
          </dl>

          <h3 className="mb-2 mt-6 text-lg font-bold">{t.me.attempts}</h3>
          {e.attempts.length === 0 && <p className="text-quiet">{t.me.noAttempts}</p>}
          {e.attempts.map((a) => (
            <div key={a.id} className="mb-4">
              <p>
                <strong>{a.quiz}</strong> · {fmt(a.started_at)} ·{" "}
                {a.finished_at ? `${t.me.score} ${a.score_percent}%` : t.me.notFinished}
              </p>
              {a.answers.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="mt-1">
                    <thead>
                      <tr>
                        <th>{t.me.question}</th>
                        <th>{t.me.yourAnswer}</th>
                        <th>{t.me.result}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {a.answers.map((x) => (
                        <tr key={x.id}>
                          <td dir="auto">{x.question}</td>
                          <td dir="auto">{x.answer}</td>
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

          <h3 className="mb-2 mt-6 text-lg font-bold">{t.me.events}</h3>
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>{t.me.when}</th>
                  <th>{t.me.what}</th>
                  <th>{t.me.details}</th>
                  <th>{t.me.app}</th>
                </tr>
              </thead>
              <tbody>
                {e.events.length === 0 && (
                  <tr>
                    <td colSpan={4} className="text-quiet">
                      {t.me.nothing}
                    </td>
                  </tr>
                )}
                {e.events.map((ev, i) => (
                  <tr key={i}>
                    <td className="whitespace-nowrap">{fmt(ev.created_at)}</td>
                    <td dir="ltr" className="text-start">{ev.label}</td>
                    <td dir="auto">
                      {[ev.lesson, ev.concept, ev.note && `“${ev.note}”`].filter(Boolean).join(" · ")}
                    </td>
                    <td>{ev.client || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <ButtonLink href={`/study/${e.id}/`}>{t.study.open}</ButtonLink>
            <Button
              variant="secondary"
              onClick={async () => {
                try {
                  await api(`enrollments/${e.id}/regenerate`, { method: "POST" });
                  router.push(`/connect/${e.id}/`);
                } catch (err) {
                  setError(errorText(err));
                }
              }}
            >
              {t.me.regenerate}
            </Button>
            <Button
              variant="danger"
              onClick={async () => {
                if (!window.confirm(t.me.leaveConfirm)) return;
                try {
                  await api(`enrollments/${e.id}/leave`, { method: "POST" });
                  setNotice(t.me.left);
                  load();
                } catch (err) {
                  setError(errorText(err));
                }
              }}
            >
              {t.me.leave}
            </Button>
          </div>
        </Card>
      ))}
      <ComingSoon title={t.soon.title} lead={t.soon.meLead} items={t.soon.me} />
    </div>
  );
}
