"use client";

import Link from "next/link";
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
  return <section className={`rounded-xl border border-line bg-surface p-5 shadow-sm sm:p-6 ${className}`}>{children}</section>;
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

/* ------------------------------------------------------------------ icons (Lucide paths, MIT) */

const ICONS: Record<string, React.ReactNode> = {
  users: (
    <>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </>
  ),
  moon: <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />,
  check: <path d="M20 6 9 17l-5-5" />,
  checkCircle: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  x: <path d="M18 6 6 18M6 6l12 12" />,
  xCircle: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="m15 9-6 6M9 9l6 6" />
    </>
  ),
  alert: (
    <>
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
      <path d="M12 9v4M12 17h.01" />
    </>
  ),
  flag: (
    <>
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
      <path d="M4 22v-7" />
    </>
  ),
  clipboard: (
    <>
      <rect width="8" height="4" x="8" y="2" rx="1" />
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <path d="m9 14 2 2 4-4" />
    </>
  ),
  eye: (
    <>
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  plug: (
    <>
      <path d="M12 22v-5M9 8V2M15 8V2" />
      <path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z" />
    </>
  ),
  sparkles: (
    <>
      <path d="M9.94 14.06 8 20l-1.94-5.94L0 12l6.06-1.94L8 4l1.94 6.06L16 12z" transform="translate(4 -1) scale(.85)" />
      <path d="M20 3v4M22 5h-4" />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </>
  ),
  chevron: <path d="m6 9 6 6 6-6" />,
  book: <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />,
};

export function Icon({ name, className = "h-5 w-5" }: { name: keyof typeof ICONS | string; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={`shrink-0 ${className}`}
    >
      {ICONS[name]}
    </svg>
  );
}

/* ------------------------------------------------------------------ data display */

export function StatCard({
  icon,
  label,
  value,
  tone = "default",
  href,
}: {
  icon: string;
  label: string;
  value: React.ReactNode;
  tone?: "default" | "danger" | "warn" | "ok";
  href?: string;
}) {
  const tones = {
    default: "bg-lapis/10 text-lapis",
    danger: "bg-danger/10 text-danger",
    warn: "bg-saffron/20 text-[#8a5a12]",
    ok: "bg-ok/10 text-ok",
  }[tone];
  const body = (
    <div className="lift flex h-full items-center gap-3 rounded-xl border border-line bg-surface px-4 py-3 shadow-sm hover:border-lapis/40">
      <span className={`grid h-10 w-10 place-items-center rounded-lg ${tones}`}>
        <Icon name={icon} />
      </span>
      <div className="min-w-0">
        <dd className="text-2xl font-bold leading-tight text-ink">{value}</dd>
        <dt className="truncate text-sm text-quiet">{label}</dt>
      </div>
    </div>
  );
  return href ? (
    <Link href={href} className="block no-underline hover:no-underline">
      {body}
    </Link>
  ) : (
    body
  );
}

export function scoreTone(p: number | null | undefined) {
  if (p === null || p === undefined) return { bar: "bg-line", text: "text-quiet" };
  if (p >= 80) return { bar: "bg-ok", text: "text-ok" };
  if (p >= 50) return { bar: "bg-saffron", text: "text-[#8a5a12]" };
  return { bar: "bg-danger", text: "text-danger" };
}

export function ScoreBar({ value, className = "" }: { value: number | null | undefined; className?: string }) {
  const tone = scoreTone(value);
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="h-2 w-full min-w-[3rem] overflow-hidden rounded-full bg-mist" role="presentation">
        <div className={`bar-grow h-full rounded-full ${tone.bar}`} style={{ width: `${Math.max(0, Math.min(100, value ?? 0))}%` }} />
      </div>
      <span className={`w-11 shrink-0 text-end text-sm font-semibold tabular-nums ${tone.text}`}>
        {value === null || value === undefined ? "—" : `${value}%`}
      </span>
    </div>
  );
}

export function Chip({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "danger" | "warn" | "ok" | "info" }) {
  const tones = {
    default: "bg-mist text-ink border-line",
    danger: "bg-danger/10 text-danger border-danger/20",
    warn: "bg-saffron/15 text-[#7a4f0f] border-saffron/30",
    ok: "bg-ok/10 text-ok border-ok/20",
    info: "bg-turquoise/10 text-turquoise border-turquoise/20",
  }[tone];
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium ${tones}`} dir="auto">
      {children}
    </span>
  );
}

export function SeverityChip({ severity }: { severity: string }) {
  const t = useT();
  const tone = severity === "high" ? "danger" : severity === "low" ? "default" : "warn";
  return <Chip tone={tone}>{t.teach.problems.severity[severity] ?? severity}</Chip>;
}

export function SectionTitle({ icon, children, aside }: { icon?: string; children: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
      <h2 className="flex items-center gap-2 text-lg font-bold text-lapis">
        {icon && <Icon name={icon} className="h-5 w-5 text-turquoise" />}
        {children}
      </h2>
      {aside}
    </div>
  );
}
