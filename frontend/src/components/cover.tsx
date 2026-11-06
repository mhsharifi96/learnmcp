import { COVERS, coverTheme } from "@/lib/covers";

/** A class cover: the uploaded photo, or an automatic gradient with a subject icon. Works in server and client components. */
export function Cover({
  image,
  theme,
  alt = "",
  className = "",
}: {
  image?: string | null;
  theme?: string | null;
  alt?: string;
  className?: string;
}) {
  if (image) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={image} alt={alt} loading="lazy" className={`aspect-[1200/630] w-full object-cover ${className}`} />;
  }
  const c = COVERS[coverTheme(theme)];
  return (
    <div
      role={alt ? "img" : undefined}
      aria-label={alt || undefined}
      aria-hidden={alt ? undefined : true}
      className={`relative flex aspect-[1200/630] w-full items-center justify-center overflow-hidden ${className}`}
      style={{ backgroundImage: `linear-gradient(135deg, ${c.from}, ${c.to})` }}
    >
      <span className="absolute -end-10 -top-10 h-40 w-40 rounded-full bg-white/10" />
      <span className="absolute -bottom-12 -start-8 h-36 w-36 rounded-full bg-white/10" />
      <svg viewBox="0 0 24 24" className="relative h-1/3 w-auto" fill="none" stroke="white" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
        {c.shapes.map((s, i) =>
          s.rect ? <rect key={i} {...s.rect} /> : s.points ? <polyline key={i} points={s.points} /> : <path key={i} d={s.d} />,
        )}
      </svg>
    </div>
  );
}
