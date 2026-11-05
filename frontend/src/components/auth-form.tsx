"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useT } from "./lang";
import { Alert, Button, Card, Field, Input, PageTitle, useErrorText } from "./ui";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const t = useT();
  const router = useRouter();
  const errorText = useErrorText();
  const [v, setV] = useState({ username: "", password: "", email: "", display_name: "", password1: "", password2: "" });
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof v) => (e: React.ChangeEvent<HTMLInputElement>) => setV({ ...v, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setErrors({});
    try {
      if (mode === "login") await api("auth/login", { method: "POST", body: { username: v.username, password: v.password } });
      else
        await api("auth/signup", {
          method: "POST",
          body: { username: v.username, email: v.email, display_name: v.display_name, password1: v.password1, password2: v.password2 },
        });
      router.push("/teach/");
      router.refresh();
    } catch (err) {
      setError(errorText(err));
      if (err instanceof ApiError) setErrors(err.errors);
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <PageTitle>{mode === "login" ? t.auth.loginTitle : t.auth.signupTitle}</PageTitle>
      <Card>
        <Alert>{error}</Alert>
        <form onSubmit={submit}>
          <Field label={t.auth.username} htmlFor="username" error={errors.username}>
            <Input id="username" dir="ltr" autoComplete="username" value={v.username} onChange={set("username")} required />
          </Field>
          {mode === "signup" && (
            <>
              <Field label={t.auth.displayName} htmlFor="display_name" error={errors.display_name}>
                <Input id="display_name" value={v.display_name} onChange={set("display_name")} required />
              </Field>
              <Field label={t.join.email} htmlFor="email" error={errors.email}>
                <Input id="email" type="email" dir="ltr" autoComplete="email" value={v.email} onChange={set("email")} required />
              </Field>
            </>
          )}
          {mode === "login" ? (
            <Field label={t.auth.password} htmlFor="password">
              <Input id="password" type="password" dir="ltr" autoComplete="current-password" value={v.password} onChange={set("password")} required />
            </Field>
          ) : (
            <>
              <Field label={t.auth.password} htmlFor="password1" error={errors.password1}>
                <Input id="password1" type="password" dir="ltr" autoComplete="new-password" value={v.password1} onChange={set("password1")} required />
              </Field>
              <Field label={t.auth.password2} htmlFor="password2" error={errors.password2}>
                <Input id="password2" type="password" dir="ltr" autoComplete="new-password" value={v.password2} onChange={set("password2")} required />
              </Field>
            </>
          )}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? t.common.loading : mode === "login" ? t.auth.login : t.auth.signup}
          </Button>
        </form>
        <p className="mt-4 text-sm">
          {mode === "login" ? (
            <>
              {t.auth.noAccount} <Link href="/signup/">{t.home.signup}</Link>
            </>
          ) : (
            <>
              {t.home.haveAccount} <Link href="/login/">{t.nav.login}</Link>
            </>
          )}
        </p>
      </Card>
    </div>
  );
}
