"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Cover } from "@/components/cover";
import { useT } from "@/components/lang";
import { VerifyNotice } from "@/components/student-auth-form";
import type { StudentAccount } from "@/lib/types";
import { Alert, Button, ButtonLink, buttonClass, Card, Chip, Icon, PageTitle, Spinner, useErrorText } from "@/components/ui";

/** Shown after registering for a class that needs the site admin's approval. */
export function PendingNotice({ link = true }: { link?: boolean }) {
  const t = useT();
  return (
    <div className="flex items-start gap-4">
      <Icon name="checkCircle" className="mt-1 h-8 w-8 shrink-0 text-ok" />
      <div>
        <h2 className="mb-2 text-xl font-bold text-lapis">{t.join.pendingTitle}</h2>
        <p className="leading-8">{t.join.pendingText}</p>
        {link && (
          <Link href="/me/" className="mt-3 inline-block">
            {t.join.goMe}
          </Link>
        )}
      </div>
    </div>
  );
}

/** What anyone can see about a class (also fetched on the server for SEO). */
export type PublicClass = {
  code: string;
  title: string;
  description: string;
  instructor: string;
  listed: boolean;
  lessons: { order: number; title: string }[];
  image?: string | null;
  theme?: string;
  requires_approval?: boolean;
  quizzes?: number;
};

type ClassInfo = PublicClass & {
  linked: boolean;
  already_joined: boolean;
  pending: boolean;
  student: StudentAccount | null;
};

export default function Join({ initial = null }: { initial?: PublicClass | null }) {
  const t = useT();
  const errorText = useErrorText();
  const router = useRouter();
  const { code } = useParams<{ code: string }>();
  const [info, setInfo] = useState<ClassInfo | null>(null);
  const shown: PublicClass | null = info ?? initial;
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
  if (!shown) return <Spinner />;

  const quizSlots = Math.max(1, Math.min(shown.quizzes || shown.lessons?.length || 3, 4));
  const header = (
    <div className="space-y-5">
      <div>
        <Cover image={shown.image} theme={shown.theme} alt={shown.title} className="mb-5 max-h-72 rounded-2xl" />
        <p className="flex flex-wrap items-center gap-2 text-quiet">
          <Chip tone="ok">{t.join.free}</Chip>
          <span>
            {t.join.by} {shown.instructor}
          </span>
        </p>
        <PageTitle>{shown.title}</PageTitle>
        {!info?.already_joined && (
          <a href="#register" className={buttonClass("primary", "-mt-2 hover:no-underline")}>
            <Icon name="lock" className="h-4 w-4" />
            {t.join.registerCta}
          </a>
        )}
      </div>
      {shown.description && (
        <Card>
          <h2 className="mb-3 text-xl font-bold text-lapis">{t.join.about}</h2>
          <div className="max-w-prose whitespace-pre-line leading-8" dir="auto">
            {shown.description}
          </div>
        </Card>
      )}
      {shown.lessons?.length > 0 && (
        <Card>
          <h2 className="mb-3 text-xl font-bold text-lapis">
            {t.join.syllabus} <span className="text-base font-normal text-quiet">({t.catalog.lessons(shown.lessons.length)})</span>
          </h2>
          <ol className="space-y-2">
            {shown.lessons.map((l) => (
              <li key={l.order} className="flex items-center gap-3 rounded-lg border border-line bg-mist/40 p-3">
                <span className="text-quiet">{l.order}.</span>
                <span className="min-w-0 flex-1" dir="auto">
                  {l.title}
                </span>
                {!info?.already_joined || info.pending ? (
                  <span className="flex shrink-0 items-center gap-1 text-sm text-quiet" title={t.join.locked}>
                    <Icon name="lock" className="h-4 w-4" />
                    <span className="hidden sm:inline">{t.join.locked}</span>
                  </span>
                ) : null}
              </li>
            ))}
          </ol>
        </Card>
      )}
      {(!info?.already_joined || info.pending) && (
        <Card className="relative overflow-hidden">
          <h2 className="mb-3 text-xl font-bold text-lapis">{t.join.quizzesTitle}</h2>
          <div aria-hidden className="pointer-events-none select-none space-y-3 blur-[3px]">
            {Array.from({ length: quizSlots }, (_, i) => (
              <div key={i} className="rounded-lg border border-line p-3">
                <p className="mb-2 font-semibold">{t.join.lockedQuiz(i + 1)}</p>
                <div className="mb-1.5 h-2.5 w-11/12 rounded bg-line" />
                <div className="mb-1.5 h-2.5 w-3/4 rounded bg-line" />
                <div className="h-2.5 w-1/2 rounded bg-line" />
              </div>
            ))}
          </div>
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-surface/60 p-6 text-center backdrop-blur-[1px]">
            <Icon name="lock" className="mb-2 h-8 w-8 text-lapis" />
            <p className="font-bold text-lapis">{t.join.lockedTitle}</p>
            <p className="mt-1 max-w-md text-sm text-quiet">{t.join.lockedText}</p>
          </div>
        </Card>
      )}
    </div>
  );

  if (!info)
    return (
      <div className="mx-auto max-w-3xl space-y-5">
        {header}
        <Spinner />
      </div>
    );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setErrors({});
    try {
      const r = await api<{ enrollment_id: number; pending?: boolean }>(`classes/${info!.code}/join`, { method: "POST", body: { consent } });
      router.push(`/connect/${r.enrollment_id}/`);
    } catch (err) {
      setError(errorText(err));
      if (err instanceof ApiError) setErrors(err.errors);
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      {header}

      {info.already_joined && info.pending ? (
        <Card id="register">
          <PendingNotice />
        </Card>
      ) : info.already_joined ? (
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

          <Card id="register" className="scroll-mt-24">
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
                    {busy ? t.common.loading : info.requires_approval ? t.join.submitApproval : t.join.submit}
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
