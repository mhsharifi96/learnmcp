"use client";

import Link from "next/link";
import { useT } from "@/components/lang";

export default function NotFound() {
  const t = useT();
  return (
    <div className="py-16 text-center">
      <p className="font-display text-6xl text-lapis">404</p>
      <p className="mt-4">
        <Link href="/">{t.nav.home}</Link>
      </p>
    </div>
  );
}
