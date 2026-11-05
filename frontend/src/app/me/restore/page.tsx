"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { useT } from "@/components/lang";
import { Alert, Button, Card, Field, Input, PageTitle, useErrorText } from "@/components/ui";

export default function Restore() {
  const t = useT();
  const router = useRouter();
  const errorText = useErrorText();
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  return (
    <div className="mx-auto max-w-xl">
      <PageTitle lead={t.me.restoreLead}>{t.me.restoreTitle}</PageTitle>
      <Card>
        <Alert>{error}</Alert>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setError("");
            try {
              await api("restore", { method: "POST", body: { url } });
              router.push("/me/");
            } catch (err) {
              setError(errorText(err));
            }
          }}
        >
          <Field label={t.me.restoreLabel} htmlFor="url">
            <Input id="url" dir="ltr" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…/s/…/mcp" />
          </Field>
          <Button type="submit" disabled={!url.trim()}>
            {t.me.restoreButton}
          </Button>
        </form>
      </Card>
    </div>
  );
}
