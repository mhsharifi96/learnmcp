"use client";

import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Problem } from "@/lib/types";
import { useFormatDate, useT } from "./lang";
import { Button, Chip, Icon, SeverityChip, Textarea, useErrorText } from "./ui";

const CATEGORY_ICON: Record<string, string> = {
  concept: "alert",
  repeated_mistake: "target",
  quiz_mistakes: "clipboard",
  prerequisite: "book",
  engagement: "moon",
  technical: "plug",
  other: "flag",
};

type Filter = "open" | "resolved" | "all";

export function ProblemList({
  problems,
  onChange,
  showStudent = true,
}: {
  problems: Problem[];
  onChange: (p: Problem) => void;
  showStudent?: boolean;
}) {
  const t = useT();
  const [filter, setFilter] = useState<Filter>("open");
  const shown = problems.filter((p) => (filter === "all" ? true : filter === "open" ? !p.resolved_at : !!p.resolved_at));
  const counts = {
    open: problems.filter((p) => !p.resolved_at).length,
    resolved: problems.filter((p) => p.resolved_at).length,
    all: problems.length,
  };

  return (
    <div>
      <div role="tablist" className="mb-4 inline-flex rounded-lg border border-line bg-mist p-1 text-sm">
        {(["open", "resolved", "all"] as Filter[]).map((f) => (
          <button
            key={f}
            role="tab"
            type="button"
            aria-selected={filter === f}
            onClick={() => setFilter(f)}
            className={`min-h-[36px] rounded-md px-3 transition-colors ${
              filter === f ? "bg-surface font-semibold text-lapis shadow-sm" : "text-quiet hover:text-ink"
            }`}
          >
            {t.teach.problems[f]} <span className="tabular-nums opacity-70">({counts[f]})</span>
          </button>
        ))}
      </div>
      {shown.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line px-4 py-6 text-center text-quiet">
          {problems.length === 0 ? t.teach.noStuck : t.teach.problems.empty}
        </p>
      ) : (
        <ul key={filter} className="stagger space-y-3">
          {shown.map((p) => (
            <ProblemItem key={p.id} p={p} onChange={onChange} showStudent={showStudent} />
          ))}
        </ul>
      )}
    </div>
  );
}

function ProblemItem({ p, onChange, showStudent }: { p: Problem; onChange: (p: Problem) => void; showStudent: boolean }) {
  const t = useT();
  const fmt = useFormatDate();
  const errorText = useErrorText();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(p.instructor_note);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const resolved = !!p.resolved_at;

  async function patch(body: Record<string, unknown>) {
    setBusy(true);
    setError("");
    try {
      onChange(await api<Problem>(`teach/problems/${p.id}`, { method: "PATCH", body }));
      setEditing(false);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  const accent = resolved ? "border-s-line" : p.severity === "high" ? "border-s-danger" : p.severity === "low" ? "border-s-turquoise" : "border-s-saffron";

  return (
    <li className={`fade-up rounded-lg border border-line border-s-4 ${accent} bg-surface p-4 ${resolved ? "opacity-70" : ""}`}>
      <div className="flex flex-wrap items-start gap-3">
        <span className="mt-0.5 grid h-9 w-9 place-items-center rounded-lg bg-mist text-lapis">
          <Icon name={CATEGORY_ICON[p.category] ?? "flag"} className="h-[18px] w-[18px]" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {showStudent && (
              <Link href={`/teach/students/${p.enrollment_id}/`} className="font-semibold">
                {p.student}
              </Link>
            )}
            <Chip>{t.teach.problems.category[p.category] ?? p.category}</Chip>
            <SeverityChip severity={p.severity} />
            {resolved && (
              <span className="pop-in"><Chip tone="ok">
                <Icon name="check" className="h-3 w-3" />
                {t.teach.problems.resolved}
              </Chip></span>
            )}
          </div>
          <p className="mt-1 font-medium text-ink" dir="auto">
            {p.concept}
          </p>
          {p.note && (
            <p className="text-sm text-quiet" dir="auto">
              {p.note}
            </p>
          )}
          <p className="mt-1 text-xs text-quiet">
            {fmt(p.created_at)}
            {p.lesson && ` · ${p.lesson}`}
            {p.quiz && ` · ${t.teach.problems.fromQuiz}: ${p.quiz}`}
          </p>
          {p.instructor_note && !editing && (
            <p className="mt-2 rounded-md bg-mist px-3 py-2 text-sm" dir="auto">
              <span className="font-semibold">{t.teach.problems.note}: </span>
              {p.instructor_note}
            </p>
          )}
          {editing && (
            <div className="mt-2 space-y-2">
              <Textarea
                rows={2}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={t.teach.problems.notePh}
                aria-label={t.teach.problems.note}
              />
              <div className="flex gap-2">
                <Button type="button" disabled={busy} onClick={() => patch({ instructor_note: note })}>
                  {t.teach.problems.saveNote}
                </Button>
                <Button type="button" variant="ghost" onClick={() => setEditing(false)}>
                  {t.common.cancel}
                </Button>
              </div>
            </div>
          )}
          {error && <p className="mt-1 text-sm text-danger">{error}</p>}
        </div>
        <div className="flex shrink-0 gap-2">
          {!editing && (
            <Button type="button" variant="ghost" className="min-h-[40px] px-3 text-sm" onClick={() => setEditing(true)}>
              {t.teach.problems.note}
            </Button>
          )}
          <Button
            type="button"
            variant={resolved ? "secondary" : "primary"}
            className="min-h-[40px] px-3 text-sm"
            disabled={busy}
            onClick={() => patch({ resolved: !resolved })}
          >
            {!resolved && <Icon name="check" className="h-4 w-4" />}
            {resolved ? t.teach.problems.reopen : t.teach.problems.resolve}
          </Button>
        </div>
      </div>
    </li>
  );
}
