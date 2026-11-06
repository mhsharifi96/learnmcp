/** Automatic class covers: a gradient and a subject icon (Lucide shapes, ISC licence). Shared by the page and the PNG route. */

export type CoverTheme = "code" | "math" | "career" | "finance" | "science" | "language" | "general";

type Shape = { d?: string; points?: string; rect?: { x: number; y: number; width: number; height: number; rx: number } };

export const COVERS: Record<CoverTheme, { from: string; to: string; shapes: Shape[] }> = {
  code: { from: "#1e3a8a", to: "#0d9488", shapes: [{ points: "16 18 22 12 16 6" }, { points: "8 6 2 12 8 18" }] },
  math: { from: "#6d28d9", to: "#db2777", shapes: [{ d: "M18 7V4H6l6 8-6 8h12v-3" }] },
  career: {
    from: "#334155",
    to: "#0f766e",
    shapes: [{ rect: { x: 2, y: 7, width: 20, height: 14, rx: 2 } }, { d: "M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" }],
  },
  finance: { from: "#065f46", to: "#ca8a04", shapes: [{ points: "22 7 13.5 15.5 8.5 10.5 2 17" }, { points: "16 7 22 7 22 13" }] },
  science: {
    from: "#047857",
    to: "#0284c7",
    shapes: [
      { d: "M10 2v7.527a2 2 0 0 1-.211.896L4.72 20.55a1 1 0 0 0 .9 1.45h12.76a1 1 0 0 0 .9-1.45l-5.069-10.127A2 2 0 0 1 14 9.527V2" },
      { d: "M8.5 2h7" },
      { d: "M7 16h10" },
    ],
  },
  language: {
    from: "#1d4ed8",
    to: "#c2410c",
    shapes: [{ d: "M7.9 20A9 9 0 1 0 4 16.1L2 22Z" }, { d: "M8 12h.01" }, { d: "M12 12h.01" }, { d: "M16 12h.01" }],
  },
  general: {
    from: "#1e40af",
    to: "#b45309",
    shapes: [{ d: "M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" }, { d: "M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" }],
  },
};

export function coverTheme(value: string | null | undefined): CoverTheme {
  return value && value in COVERS ? (value as CoverTheme) : "general";
}
