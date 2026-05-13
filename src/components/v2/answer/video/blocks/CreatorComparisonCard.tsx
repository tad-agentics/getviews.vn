import type { CreatorComparison, CreatorComparisonVideo } from "@/lib/api-types";

function atHandle(raw: string | null | undefined): string {
  const s = (raw ?? "").trim();
  if (!s) return "";
  return s.startsWith("@") ? s : `@${s}`;
}

export function CreatorComparisonUnavailable({ creator }: { creator: string }) {
  const at = atHandle(creator);
  return (
    <div className="mt-6 rounded-xl border border-dashed border-[var(--gv-rule)] bg-[var(--gv-canvas-2)] p-4 text-[12.5px] text-[var(--gv-ink-3)]">
      <p className="gv-mono mb-1 text-[10px] uppercase tracking-wider text-[var(--gv-ink-3)]">
        SO SÁNH TRONG KÊNH · {at}
      </p>
      <p className="m-0 leading-relaxed">
        Chưa đủ video gần nhất của creator để so sánh hit/flop.
        {" "}Cần tối thiểu 2 video có lượng view rõ ràng để dựng được
        cặp đối chiếu.
      </p>
    </div>
  );
}

function fmtViews(v: number): string {
  return v >= 1_000_000
    ? `${(v / 1_000_000).toFixed(1)}M`
    : v >= 1_000
      ? `${Math.round(v / 1_000)}K`
      : v.toLocaleString("vi-VN");
}

function CreatorComparisonEvidenceCell({
  label,
  video,
  accent,
}: {
  label: string;
  video: CreatorComparisonVideo;
  accent: "hit" | "flop";
}) {
  const borderCls =
    accent === "hit" ? "border-[var(--gv-pos)]" : "border-[var(--gv-rule)]";
  const labelCls =
    accent === "hit" ? "text-[var(--gv-pos)]" : "text-[var(--gv-ink-3)]";
  const url = video.tiktok_url?.trim();
  const captionHint = video.hook_type?.trim();

  return (
    <div
      className={`flex flex-col gap-2 rounded-lg border ${borderCls} bg-[var(--gv-canvas)] p-3`}
    >
      <span
        className={`gv-mono text-[9px] font-semibold uppercase tracking-wider ${labelCls}`}
      >
        {label}
      </span>
      {video.thumbnail_url ? (
        <div className="relative mx-auto aspect-[9/16] w-full max-w-[120px] overflow-hidden rounded-md bg-[var(--gv-canvas-2)]">
          <img
            src={video.thumbnail_url}
            alt=""
            className="h-full w-full object-cover"
            loading="lazy"
            decoding="async"
          />
        </div>
      ) : null}
      <span className="gv-mono text-[22px] font-bold leading-none text-[var(--gv-ink)]">
        {fmtViews(video.views)}
      </span>
      <span className="text-[10px] text-[var(--gv-ink-3)]">lượt xem</span>
      {captionHint ? (
        <p className="m-0 line-clamp-2 text-[11px] leading-snug text-[var(--gv-ink-2)]">
          {captionHint}
        </p>
      ) : null}
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-auto pt-1 text-[11px] font-semibold text-[color:var(--gv-accent)] underline underline-offset-2 hover:opacity-90"
        >
          Xem video →
        </a>
      ) : (
        <p className="m-0 mt-auto pt-1 text-[10px] text-[var(--gv-ink-4)]">
          Chưa có link TikTok cho video này.
        </p>
      )}
    </div>
  );
}

export function CreatorComparisonCard({ data }: { data: CreatorComparison }) {
  return (
    <div className="mt-6 rounded-xl border border-[var(--gv-rule)] bg-[var(--gv-canvas-2)] p-4">
      <p className="gv-mono mb-3 text-[10px] uppercase tracking-wider text-[var(--gv-ink-3)]">
        SO SÁNH TRONG KÊNH · {data.creator_handle}
      </p>

      <div className="grid grid-cols-2 gap-3">
        <CreatorComparisonEvidenceCell
          label="Video có views cao nhất"
          video={data.hit}
          accent="hit"
        />
        <CreatorComparisonEvidenceCell
          label="Video có views thấp nhất"
          video={data.flop}
          accent="flop"
        />
      </div>

      <div className="mt-3 flex items-center justify-between gap-3 rounded-lg bg-[var(--gv-canvas)] px-3 py-2.5">
        <span className="min-w-0 text-[12px] leading-snug text-[var(--gv-ink-2)]">
          Tỉ lệ views cao nhất so với thấp nhất trong mẫu
        </span>
        <span className="gv-mono shrink-0 text-[13px] font-bold text-[var(--gv-ink)]">
          {data.delta.toLocaleString("vi-VN")}×
        </span>
      </div>

      <p className="mt-2 text-[11px] text-[var(--gv-ink-3)]">
        Video này đang ở{" "}
        <span className="font-medium text-[var(--gv-ink)]">{data.target_percentile}</span> so với{" "}
        <span className="font-medium text-[var(--gv-ink)]">{data.total_posts_analyzed} video</span> gần
        nhất của {data.creator_handle} (median: {fmtViews(data.median_views)} views).
      </p>
    </div>
  );
}
