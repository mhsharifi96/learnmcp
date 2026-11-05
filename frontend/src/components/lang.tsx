"use client";

import { createContext, useContext } from "react";
import { useRouter } from "next/navigation";
import { dictionaries, LANG_COOKIE, type Dict, type Lang } from "@/lib/i18n";

const LangContext = createContext<Lang>("fa");

export function LangProvider({ lang, children }: { lang: Lang; children: React.ReactNode }) {
  return <LangContext.Provider value={lang}>{children}</LangContext.Provider>;
}

export function useLang(): Lang {
  return useContext(LangContext);
}

export function useT(): Dict {
  return dictionaries[useLang()];
}

export function useFormatDate() {
  const lang = useLang();
  const locale = lang === "fa" ? "fa-IR" : "en-GB";
  return (iso: string | null | undefined, withTime = true) => {
    if (!iso) return "—";
    return new Intl.DateTimeFormat(locale, {
      year: "numeric",
      month: "short",
      day: "numeric",
      ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
    }).format(new Date(iso));
  };
}

export function LangSwitch() {
  const lang = useLang();
  const t = useT();
  const router = useRouter();
  const next: Lang = lang === "fa" ? "en" : "fa";
  return (
    <button
      type="button"
      className="rounded-md px-2 py-1 text-sm text-lapis hover:bg-mist"
      lang={next}
      onClick={() => {
        document.cookie = `${LANG_COOKIE}=${next}; path=/; max-age=31536000; samesite=lax`;
        router.refresh();
      }}
    >
      {t.nav.lang}
    </button>
  );
}
