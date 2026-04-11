/**
 * StepThumbnails — a row of up to 4 circular 24px thumbnail previews.
 * Shown in the "Đã tìm X video" count line.
 * Falls back to a solid purple dot when no thumbnail URL is available.
 */

interface Props {
  thumbnails: string[];
  maxVisible?: number;
}

export function StepThumbnails({ thumbnails, maxVisible = 4 }: Props) {
  const visible = thumbnails.slice(0, maxVisible);
  if (!visible.length) return null;

  return (
    <span className="inline-flex items-center">
      {visible.map((url, i) => (
        <span
          key={i}
          className="inline-block overflow-hidden rounded-full border-2 border-[var(--surface)]"
          style={{
            width: 20,
            height: 20,
            marginLeft: i === 0 ? 0 : -6,
            background: "var(--purple-light)",
            flexShrink: 0,
          }}
        >
          {url ? (
            <img
              src={url}
              alt=""
              className="h-full w-full object-cover"
              loading="lazy"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          ) : (
            <span
              className="block h-full w-full rounded-full"
              style={{ background: "var(--purple)" }}
            />
          )}
        </span>
      ))}
    </span>
  );
}
