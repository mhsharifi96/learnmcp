"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Input } from "./ui";
import { useT } from "./lang";

export function CodeForm({ autoFocus = false }: { autoFocus?: boolean }) {
  const t = useT();
  const router = useRouter();
  const [code, setCode] = useState("");
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        const c = code.trim().toUpperCase();
        if (c) router.push(`/join/${encodeURIComponent(c)}/`);
      }}
    >
      <Input
        aria-label={t.join.codeLabel}
        placeholder={t.home.codePlaceholder}
        value={code}
        onChange={(e) => setCode(e.target.value)}
        dir="ltr"
        autoFocus={autoFocus}
        autoCapitalize="characters"
        className="font-mono uppercase tracking-wider"
        maxLength={16}
      />
      <Button type="submit" className="shrink-0">
        {t.home.codeButton}
      </Button>
    </form>
  );
}
