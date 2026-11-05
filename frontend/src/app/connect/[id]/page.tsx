"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useT } from "@/components/lang";
import { Alert, Button, Card, CopyBox, PageTitle, Spinner, useErrorText } from "@/components/ui";

type Info = { enrollment_id: number; course: string; mcp_url: string | null; token_hint: string; other_classes: number };

export default function Connect() {
  const t = useT();
  const errorText = useErrorText();
  const { id } = useParams<{ id: string }>();
  const [info, setInfo] = useState<Info | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<Info>(`connect/${id}`).then(setInfo).catch((e) => setError(errorText(e)));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(load, [load]);

  if (error) return <Alert>{error}</Alert>;
  if (!info) return <Spinner />;

  return (
    <div className="space-y-5">
      <PageTitle>
        {t.connect.title} {info.course}
      </PageTitle>
      <Card>
        {info.mcp_url ? (
          <>
            <p className="mb-3">{t.connect.personal}</p>
            <CopyBox id="mcp-url" value={info.mcp_url} />
            <p className="mt-2 text-sm text-quiet">{t.connect.onceNote}</p>
          </>
        ) : (
          <>
            <p className="mb-3">{t.connect.hidden}</p>
            <Button
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await api(`enrollments/${id}/regenerate`, { method: "POST" });
                  load();
                } catch (e) {
                  setError(errorText(e));
                }
                setBusy(false);
              }}
            >
              {t.connect.regenerate}
            </Button>
          </>
        )}
        {info.other_classes > 0 && <Alert kind="info">{t.connect.otherClasses}</Alert>}
      </Card>
      <div className="grid gap-5 md:grid-cols-2">
        {[
          { title: t.connect.claudeTitle, steps: t.connect.claudeSteps, note: t.connect.claudeNote },
          { title: t.connect.gptTitle, steps: t.connect.gptSteps, note: "" },
        ].map((b) => (
          <Card key={b.title}>
            <h2 className="mb-3 text-xl font-bold text-lapis" dir="auto">
              {b.title}
            </h2>
            <ol className="list-decimal space-y-1.5 ps-5">
              {b.steps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ol>
            {b.note && <p className="mt-3 text-sm text-quiet">{b.note}</p>}
          </Card>
        ))}
      </div>
      <Alert kind="info">{t.connect.voiceTip}</Alert>
      <Link href="/me/">{t.connect.toMe}</Link>
    </div>
  );
}
