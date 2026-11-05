"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useLang, useT } from "./lang";
import { Alert, Button, Card, Field, Input, PageTitle, Spinner, useErrorText } from "./ui";

/** Only same-site paths, never "//host" or absolute URLs. */
export function safeNext(next: string | null, fallback = "/me/"): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : fallback;
}

function Form({ mode }: { mode: "login" | "signup" }) {
  const t = useT();
  const lang = useLang();
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"));
  const errorText = useErrorText();
  const [v, setV] = useState({ name: "", email: "", password: "", password1: "", password2: "" });
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof v) => (e: React.ChangeEvent<HTMLInputElement>) => setV({ ...v, [k]: e.target.value });
  const other = `${mode === "login" ? "/student/signup/" : "/student/login/"}${next !== "/me/" ? `?next=${encodeURIComponent(next)}` : ""}`;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setErrors({});
    try {
      if (mode === "login") await api("auth/student/login", { method: "POST", body: { email: v.email, password: v.password } });
      else
        await api("auth/student/signup", {
          method: "POST",
          body: { name: v.name, email: v.email, password1: v.password1, password2: v.password2, lang },
        });
      router.push(next);
      router.refresh();
    } catch (err) {
      setError(errorText(err));
      if (err instanceof ApiError) setErrors(err.errors);
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <PageTitle lead={mode === "signup" ? t.student.signupLead : undefined}>
        {mode === "login" ? t.student.loginTitle : t.student.signupTitle}
      </PageTitle>
      <Card>
        <Alert>{error}</Alert>
        <form onSubmit={submit}>
          {mode === "signup" && (
            <Field label={t.student.name} htmlFor="name" error={errors.name}>
              <Input id="name" autoComplete="name" value={v.name} onChange={set("name")} required />
            </Field>
          )}
          <Field label={t.student.email} htmlFor="email" error={errors.email}>
            <Input id="email" type="email" dir="ltr" autoComplete="email" value={v.email} onChange={set("email")} required />
          </Field>
          {mode === "login" ? (
            <Field label={t.student.password} htmlFor="password">
              <Input id="password" type="password" dir="ltr" autoComplete="current-password" value={v.password} onChange={set("password")} required />
            </Field>
          ) : (
            <>
              <Field label={t.student.password} htmlFor="password1" error={errors.password1}>
                <Input id="password1" type="password" dir="ltr" autoComplete="new-password" value={v.password1} onChange={set("password1")} required />
              </Field>
              <Field label={t.student.password2} htmlFor="password2" error={errors.password2}>
                <Input id="password2" type="password" dir="ltr" autoComplete="new-password" value={v.password2} onChange={set("password2")} required />
              </Field>
            </>
          )}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? t.common.loading : mode === "login" ? t.student.login : t.student.signup}
          </Button>
        </form>
        <p className="mt-4 flex flex-wrap justify-between gap-2 text-sm">
          <span>
            {mode === "login" ? t.student.noAccount : t.student.haveAccount}{" "}
            <Link href={other}>{mode === "login" ? t.student.signup : t.student.login}</Link>
          </span>
          <Link href="/login/" className="text-quiet">
            {t.student.instructorLink}
          </Link>
        </p>
      </Card>
    </div>
  );
}

export function StudentAuthForm({ mode }: { mode: "login" | "signup" }) {
  return (
    <Suspense fallback={<Spinner />}>
      <Form mode={mode} />
    </Suspense>
  );
}

/** "Check your inbox" box with a resend button, for logged-in students whose email isn't confirmed. */
export function VerifyNotice({ email }: { email: string }) {
  const t = useT();
  const errorText = useErrorText();
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="rounded-xl border border-saffron/40 bg-saffron/10 p-4">
      <h3 className="mb-1 font-bold text-ink">{t.student.verifyTitle}</h3>
      <p className="mb-3 text-sm">{t.student.verifyText(email)}</p>
      <Alert kind="ok">{msg}</Alert>
      <Alert>{error}</Alert>
      <Button
        variant="secondary"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setMsg("");
          setError("");
          try {
            await api("auth/verify-email/resend", { method: "POST" });
            setMsg(t.student.resent);
          } catch (err) {
            setError(errorText(err));
          }
          setBusy(false);
        }}
      >
        {busy ? t.common.loading : t.student.resend}
      </Button>
    </div>
  );
}
