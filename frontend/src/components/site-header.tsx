"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LangSwitch, useT } from "./lang";

export function SiteHeader() {
  const t = useT();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const links = [
    { href: "/classes/", label: t.nav.classes },
    { href: "/join/", label: t.nav.join },
    { href: "/me/", label: t.nav.me },
    { href: "/teach/", label: t.nav.teach },
  ];

  // Close the mobile menu on navigation and on Escape.
  useEffect(() => setOpen(false), [path]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const linkClass = (active: boolean) =>
    `whitespace-nowrap rounded-lg px-3 py-2 text-[0.95rem] transition-colors hover:no-underline ${
      active ? "bg-mist font-semibold text-lapis" : "text-ink hover:bg-mist"
    }`;

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface/90 backdrop-blur supports-[backdrop-filter]:bg-surface/80">
      <div className="mx-auto flex h-16 max-w-5xl items-center gap-4 px-4">
        <Link href="/" className="shrink-0 text-2xl font-extrabold text-lapis hover:no-underline" dir="ltr">
          learn<span className="text-turquoise">mcp</span>
        </Link>

        <nav className="hidden flex-1 items-center gap-1 md:flex" aria-label="main">
          {links.map((l) => {
            const active = path.startsWith(l.href);
            return (
              <Link key={l.href} href={l.href} aria-current={active ? "page" : undefined} className={linkClass(active)}>
                {l.label}
              </Link>
            );
          })}
        </nav>

        <div className="ms-auto flex items-center gap-1 md:ms-0">
          <LangSwitch />
          <button
            type="button"
            className="grid h-11 w-11 place-items-center rounded-lg text-lapis transition-colors hover:bg-mist md:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((v) => !v)}
          >
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden="true">
              <path className={`menu-line ${open ? "menu-top-open" : ""}`} d="M4 7h16" />
              <path className={`menu-line ${open ? "opacity-0" : ""}`} d="M4 12h16" />
              <path className={`menu-line ${open ? "menu-bottom-open" : ""}`} d="M4 17h16" />
            </svg>
          </button>
        </div>
      </div>

      <nav
        id="mobile-nav"
        aria-label="main"
        className={`mobile-nav md:hidden ${open ? "is-open" : ""}`}
        aria-hidden={!open}
      >
        <div className="mx-auto flex max-w-5xl flex-col gap-1 px-4 pb-4 pt-1">
          {links.map((l) => {
            const active = path.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                tabIndex={open ? 0 : -1}
                aria-current={active ? "page" : undefined}
                className={`${linkClass(active)} min-h-[44px] flex items-center`}
              >
                {l.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </header>
  );
}
