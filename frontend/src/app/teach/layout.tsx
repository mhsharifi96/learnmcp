"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";
import { useT } from "@/components/lang";
import { Alert, Button, Spinner, useErrorText } from "@/components/ui";
import { UserContext } from "@/components/user";

export default function TeachLayout({ children }: { children: React.ReactNode }) {
  const t = useT();
  const router = useRouter();
  const errorText = useErrorText();
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ user: User | null }>("auth/me")
      .then((d) => {
        if (!d.user) router.replace("/login/");
        setUser(d.user);
      })
      .catch((e) => setError(errorText(e)));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <Alert>{error}</Alert>;
  if (!user) return <Spinner />;

  return (
    <UserContext.Provider value={user}>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
        <Link href="/teach/" className="font-semibold text-lapis">
          {t.teach.classes}
        </Link>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-quiet">{user.display_name}</span>
          <a href="/admin/" className="text-quiet">
            {t.teach.adminLink}
          </a>
          <Button
            variant="ghost"
            className="px-2 py-1 text-sm"
            onClick={async () => {
              await api("auth/logout", { method: "POST" }).catch(() => undefined);
              router.push("/");
            }}
          >
            {t.nav.logout}
          </Button>
        </div>
      </div>
      {children}
    </UserContext.Provider>
  );
}
