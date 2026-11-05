"use client";

import { useState } from "react";
import { ApiError } from "@/lib/api";
import { useT } from "./lang";

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost" };

export function Button({ variant = "primary", className = "", ...props }: BtnProps) {
  const styles = {
    primary: "bg-saffron text-ink hover:brightness-95 font-semibold",
    secondary: "bg-surface text-lapis border border-line hover:border-lapis",
    danger: "bg-surface text-danger border border-danger/40 hover:bg-danger hover:text-white",
    ghost: "text-lapis hover:bg-mist",
  }[variant];
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-[0.95rem] transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
    />
  );
}

export function Card({ className = "", children }: { className?: string; children: React.ReactNode }) {
  return <section className={`rounded-xl border border-line bg-surface p-5 sm:p-6 ${className}`}>{children}</section>;
}

export function Field({
  label,
  help,
  error,
  children,
  htmlFor,
}: {
  label: string;
  help?: string;
  error?: string[] | string;
  children: React.ReactNode;
  htmlFor?: string;
}) {
  const err = Array.isArray(error) ? error.join(" ") : error;
  return (
    <div className="mb-4">
      <label htmlFor={htmlFor} className="mb-1 block font-medium text-ink">
        {label}
      </label>
      {children}
      {help && <p className="mt-1 text-sm text-quiet">{help}</p>}
      {err && <p className="mt-1 text-sm text-danger">{err}</p>}
    </div>
  );
}

export const inputClass =
  "w-full rounded-lg border border-line bg-white px-3 py-2 text-ink placeholder:text-quiet/70 focus:border-turquoise";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputClass} ${props.className ?? ""}`} />;
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea rows={4} {...props} className={`${inputClass} leading-7 ${props.className ?? ""}`} />;
}

export function Alert({ kind = "error", children }: { kind?: "error" | "ok" | "info"; children: React.ReactNode }) {
  if (!children) return null;
  const styles = {
    error: "border-danger/40 bg-danger/5 text-danger",
    ok: "border-ok/40 bg-ok/5 text-ok",
    info: "border-turquoise/40 bg-turquoise/5 text-lapis",
  }[kind];
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`mb-4 rounded-lg border px-4 py-3 ${styles}`}>
      {children}
    </div>
  );
}

export function useErrorText() {
  const t = useT();
  return (e: unknown) => {
    if (e instanceof ApiError) return e.status === 0 ? t.common.networkError : e.message;
    return t.common.networkError;
  };
}

export function CopyBox({ value, id }: { value: string; id: string }) {
  const t = useT();
  const [copied, setCopied] = useState(false);
  return (
    <div className="flex gap-2" dir="ltr">
      <input id={id} readOnly value={value} className={`${inputClass} font-mono text-sm`} onFocus={(e) => e.target.select()} />
      <Button
        type="button"
        variant="secondary"
        onClick={() =>
          navigator.clipboard.writeText(value).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          })
        }
      >
        {copied ? t.common.copied : t.common.copy}
      </Button>
    </div>
  );
}

export function StatusTag({ status }: { status: string }) {
  const t = useT();
  const styles: Record<string, string> = {
    correct: "bg-ok/10 text-ok",
    incorrect: "bg-danger/10 text-danger",
    needs_review: "bg-saffron/20 text-ink",
  };
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-sm ${styles[status] ?? "bg-mist"}`}>
      {(t.status as Record<string, string>)[status] ?? status}
    </span>
  );
}

export function Spinner() {
  const t = useT();
  return <p className="py-8 text-center text-quiet">{t.common.loading}</p>;
}

export function PageTitle({ children, lead }: { children: React.ReactNode; lead?: React.ReactNode }) {
  return (
    <header className="mb-6">
      <h1 className="font-display text-3xl leading-tight text-lapis sm:text-4xl">{children}</h1>
      {lead && <p className="mt-2 max-w-prose text-quiet">{lead}</p>}
    </header>
  );
}
