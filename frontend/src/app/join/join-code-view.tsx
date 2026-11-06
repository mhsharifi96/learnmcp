"use client";

import { CodeForm } from "@/components/code-form";
import { useT } from "@/components/lang";
import { Card, PageTitle } from "@/components/ui";

export default function JoinCode() {
  const t = useT();
  return (
    <div className="mx-auto max-w-lg">
      <PageTitle>{t.join.codeTitle}</PageTitle>
      <Card>
        <p className="mb-3 text-quiet">{t.home.studentText}</p>
        <CodeForm autoFocus />
      </Card>
    </div>
  );
}
