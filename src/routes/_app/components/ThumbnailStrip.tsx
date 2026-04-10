export type ThumbnailItem = { handle: string; views: string; url: string };

export function ThumbnailStrip({ thumbnails }: { thumbnails: ThumbnailItem[] }) {
  return (
    <div className="-mx-4 overflow-x-auto px-4" style={{ scrollbarWidth: "none" }}>
      <div className="flex gap-3 pb-1" style={{ width: "max-content" }}>
        {thumbnails.map((thumb, idx) => (
          <a
            key={`${thumb.url}-${idx}`}
            href={thumb.url}
            target="_blank"
            rel="noopener noreferrer"
            className="relative w-[120px] flex-shrink-0 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] transition-colors duration-[120ms] hover:border-[var(--purple)]"
            style={{ aspectRatio: "9/14" }}
          >
            <div className="absolute inset-0 flex flex-col justify-end bg-gradient-to-t from-black/60 to-transparent p-2">
              <p className="truncate text-xs font-medium text-white">{thumb.handle}</p>
              <p className="font-mono text-xs text-white/80">{thumb.views}</p>
            </div>
          </a>
        ))}
        <div className="w-[60px] flex-shrink-0" />
      </div>
    </div>
  );
}
