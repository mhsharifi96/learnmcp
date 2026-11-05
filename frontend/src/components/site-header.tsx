"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LangSwitch, useT } from "./lang";

export function SiteHeader() {
  const t = useT();
  const path = usePathname();
  const links = [
    { href: "/join/", label: t.nav.join },
    { href: "/me/", label: t.nav.me },
    { href: "/teach/", label: t.nav.teach },
  ];
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
        <Link href="/" className="font-display text-2xl text-lapis hover:no-underline" dir="ltr">
          learn<span className="text-turquoise">mcp</span>
        </Link>
        <nav className="flex flex-1 flex-wrap items-center gap-1" aria-label="main">
          {links.map((l) => {
            const active = path.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-md px-3 py-1 text-[0.95rem] hover:no-underline ${
                  active ? "bg-mist font-semibold text-lapis" : "text-ink hover:bg-mist"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
        <LangSwitch />
      </div>
    </header>
  );
}
