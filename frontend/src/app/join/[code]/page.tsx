"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/components/lang";
import { VerifyNotice } from "@/components/student-auth-form";
import type { StudentAccount } from "@/lib/types";
import { Alert, Button, ButtonLink, Card, PageTitle, Spinner, useErrorText } from "@/components/ui";

type ClassInfo = {
  code: string;
  title: string;
  description: string;
  instructor: string;
  linked: boolean;
  already_joined: boolean;
  student: StudentAccount | null;
};

export default function Join() {
  const t = useT();
  const errorText = useErrorText();
  const router = useRouter();
  const { code } = useParams<{ code: string }>();
  const [info, setInfo] = useState<ClassInfo | null>(null);
  const [loadError, setLoadError] = useState("");
  const [consent, setConsent] = useState(false);
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<ClassInfo>(`classes/${encodeURIComponent(code)}`)
      .then(setInfo)
      .catch((e) => setLoadError(e instanceof ApiError && e.status === 404 ? t.join.notFound : errorText(e)));
  }, [code]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loadError)
    return (
      <div className="mx-auto max-w-lg">
        <Alert>{loadError}</Alert>
        <Link href="/join/">{t.join.codeTitle}</Link>
      </div>
    );
  if (!info) return <Spinner />;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setErrors({});
    try {
      const r = await api<{ enrollment_id: number }>(`classes/${info!.code}/join`, { method: "POST", body: { consent } });
      router.push(`/connect/${r.enrollment_id}/`);
    } catch (err) {
      setError(errorText(err));
      if (err instanceof ApiError) setErrors(err.errors);
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <p className="text-quiet">
          {t.join.by} {info.instructor}
        </p>
        <PageTitle>{info.title}</PageTitle>
        {info.description && <p className="-mt-3 max-w-prose whitespace-pre-line">{info.description}</p>}
      </div>

      {info.already_joined ? (
        <Card>
          <p className="mb-3">{t.join.already}</p>
          <Link href="/me/">{t.join.goMe}</Link>
        </Card>
      ) : (
        <>
          <Card>
            <h2 className="mb-3 text-xl font-bold text-lapis">{t.join.sharedTitle}</h2>
            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <h3 className="font-semibold text-ok">{t.join.recorded}</h3>
                <ul className="mt-1 list-disc space-y-1 ps-5">
                  {t.join.recordedItems.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-danger">{t.join.notRecorded}</h3>
                <ul className="mt-1 list-disc space-y-1 ps-5">
                  {t.join.notRecordedItems.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              </div>
            </div>
            <p className="mt-4 text-sm text-quiet">{t.join.dataNote}</p>
          </Card>

          <Card>
            <h2 className="mb-3 text-xl font-bold text-lapis">{t.join.details}</h2>
            {!info.student ? (
              <>
                <p className="mb-4">{t.student.needAccount}</p>
                <div className="flex flex-wrap gap-3">
                  <ButtonLink href={`/student/signup/?next=${encodeURIComponent(`/join/${info.code}/`)}`}>{t.student.signup}</ButtonLink>
                  <ButtonLink href={`/student/login/?next=${encodeURIComponent(`/join/${info.code}/`)}`} variant="secondary">
                    {t.student.login}
                  </ButtonLink>
                </div>
              </>
            ) : !info.student.email_verified ? (
              <VerifyNotice email={info.student.email} />
            ) : (
              <>
                <Alert>{error}</Alert>
                <dl className="mb-4 grid gap-1 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-quiet">{t.join.name}</dt>
                    <dd className="font-semibold">{info.student.name}</dd>
                  </div>
                  <div>
                    <dt className="text-quiet">{t.join.email}</dt>
                    <dd className="font-semibold" dir="ltr">{info.student.email}</dd>
                  </div>
                </dl>
                <form onSubmit={submit} noValidate>
                  <div className="mb-3">
                    <label className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        className="mt-1.5 h-4 w-4 accent-[var(--turquoise)]"
                        checked={consent}
                        onChange={(e) => setConsent(e.target.checked)}
                      />
                      <span>{t.join.consent}</span>
                    </label>
                    {errors.consent && <p className="ms-7 text-sm text-danger">{errors.consent.join(" ")}</p>}
                  </div>
                  <Button type="submit" disabled={busy || !consent} className="mt-2">
                    {busy ? t.common.loading : t.join.submit}
                  </Button>
                </form>
              </>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
