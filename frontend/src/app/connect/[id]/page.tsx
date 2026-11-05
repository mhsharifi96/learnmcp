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
      <Card>
        <h2 className="mb-3 text-xl font-bold text-lapis" dir="auto">
          {t.connect.claudeTitle}
        </h2>
        <div className="grid items-start gap-5 lg:grid-cols-[1fr_1.2fr]">
          <div>
            <ol className="list-decimal space-y-1.5 ps-5">
              {t.connect.claudeSteps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ol>
            <p className="mt-3 text-sm text-quiet">{t.connect.claudeNote}</p>
          </div>
          <figure>
            <a href="/help/claude-connectors.png" target="_blank" rel="noopener">
              <img
                src="/help/claude-connectors.png"
                width={2066}
                height={1594}
                loading="lazy"
                alt={t.connect.claudeShot}
                className="h-auto w-full rounded-lg border border-line"
              />
            </a>
            <figcaption className="mt-2 text-sm text-quiet">
              {t.connect.claudeShot}
            </figcaption>
          </figure>
        </div>
      </Card>
      <Card>
        <h2 className="mb-3 text-xl font-bold text-lapis" dir="auto">
          {t.connect.gptTitle}
        </h2>
        <ol className="list-decimal space-y-1.5 ps-5">
          {t.connect.gptSteps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
        <p className="mt-3 text-sm text-quiet">{t.connect.gptNote}</p>
      </Card>
      <Alert kind="info">{t.connect.voiceTip}</Alert>
      <Link href="/me/">{t.connect.toMe}</Link>
    </div>
  );
}
