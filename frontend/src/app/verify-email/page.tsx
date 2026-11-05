"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useT } from "@/components/lang";
import { Alert, Card, Icon, PageTitle, Spinner, useErrorText } from "@/components/ui";

function Verify() {
  const t = useT();
  const errorText = useErrorText();
  const token = useSearchParams().get("token") || "";
  const [state, setState] = useState<"busy" | "ok" | "error">("busy");
  const [error, setError] = useState("");
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    api("auth/verify-email", { method: "POST", body: { token } })
      .then(() => setState("ok"))
      .catch((e) => {
        setError(errorText(e));
        setState("error");
      });
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="mx-auto max-w-md">
      <PageTitle>{t.student.verifyTitle}</PageTitle>
      <Card>
        {state === "busy" && <p className="text-quiet">{t.student.verifying}</p>}
        {state === "error" && (
          <>
            <Alert>{error}</Alert>
            <Link href="/me/">{t.nav.me}</Link>
          </>
        )}
        {state === "ok" && (
          <>
            <p className="mb-1 flex items-center gap-2 text-lg font-bold text-ok">
              <Icon name="checkCircle" /> {t.student.verified}
            </p>
            <p className="mb-4">{t.student.verifiedText}</p>
            <p className="flex flex-wrap gap-4">
              <Link href="/join/">{t.student.goJoin}</Link>
              <Link href="/me/">{t.nav.me}</Link>
            </p>
          </>
        )}
      </Card>
    </div>
  );
}

export default function VerifyEmail() {
  return (
    <Suspense fallback={<Spinner />}>
      <Verify />
    </Suspense>
  );
}
