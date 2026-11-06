import { ImageResponse } from "next/og";
import { COVERS, coverTheme } from "@/lib/covers";

/** PNG version of the automatic cover (1200x630), for Open Graph and Twitter previews. */
export async function GET(_req: Request, { params }: { params: Promise<{ theme: string }> }) {
  const { theme } = await params;
  const c = COVERS[coverTheme(theme.replace(/\.png$/, ""))];
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          backgroundImage: `linear-gradient(135deg, ${c.from}, ${c.to})`,
        }}
      >
        <div style={{ position: "absolute", top: -120, right: -120, width: 420, height: 420, borderRadius: 9999, background: "rgba(255,255,255,0.10)" }} />
        <div style={{ position: "absolute", bottom: -140, left: -100, width: 380, height: 380, borderRadius: 9999, background: "rgba(255,255,255,0.10)" }} />
        <svg width="240" height="240" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
          {c.shapes.map((s, i) =>
            s.rect ? <rect key={i} {...s.rect} /> : s.points ? <polyline key={i} points={s.points} /> : <path key={i} d={s.d} />,
          )}
        </svg>
      </div>
    ),
    { width: 1200, height: 630, headers: { "Cache-Control": "public, max-age=86400, s-maxage=604800" } },
  );
}
