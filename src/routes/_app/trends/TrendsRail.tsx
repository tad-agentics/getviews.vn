import { memo } from "react";
import { useNavigate } from "react-router";

import {
  useTrendsRailVideos,
  type RailVideo,
} from "@/hooks/useTrendsRailVideos";
import { VideoThumbnail } from "@/components/VideoThumbnail";
import { formatRelativeSinceVi, formatViews } from "@/lib/formatters";

/** Stable per-video pick so placeholders don’t flicker on re-render. */
function railThumbPlaceholderStyle(videoId: string): {
  wrapClass: string;
  placeholderClassName: string;
} {
  let h = 0;
  for (let i = 0; i < videoId.length; i++) h = (h * 33 + videoId.charCodeAt(i)) >>> 0;
  const cyan = (h & 1) === 1;
  if (cyan) {
    return {
      wrapClass: "bg-[color:var(--gv-accent-2-soft)]",
      placeholderClassName:
        "bg-[color:var(--gv-accent-2-soft)] ring-1 ring-inset ring-[color:color-mix(in_srgb,var(--gv-accent-2)_22%,transparent)]",
    };
  }
  return {
    wrapClass: "bg-[color:var(--gv-accent-soft)]",
    placeholderClassName:
      "bg-[color:var(--gv-accent-soft)] ring-1 ring-inset ring-[color:color-mix(in_srgb,var(--gv-accent)_22%,transparent)]",
  };
}

/**
 * Trends right rail (PR-T6).
 *
 * Replaces the previous 3-section rail (videos / sounds / format) with
 * the design pack's 2-section rail (``screens/trends.jsx`` lines
 * 432-446): VIDEO NÊN THAM KHẢO · Đang nổi lên (top 5 7d) and VIDEO
 * LEO ĐỈNH · Đang Viral (top 5 all-time).
 *
 * Each row is a clickable card: 9:16 vertical thumbnail (height 56) +
 * 2-line title (hook phrase or "Video N") + mono caption with
 * ``@handle · ↑views · age``. Click navigates to /app/video.
 *
 * Hidden when ``nicheId`` is null — the empty rail would just be two
 * stubs; better to give the column some breathing room until the
 * creator picks a niche.
 */

export const TrendsRail = memo(function TrendsRail({
  nicheId,
}: {
  nicheId: number | null;
}) {
  const { data, isPending } = useTrendsRailVideos(nicheId);
  if (nicheId == null) return null;
  return (
    <div className="flex flex-col gap-7">
      <RailSection
        kicker="VIDEO NÊN THAM KHẢO"
        title="Đang nổi lên"
        sub="Top 5 view 7 ngày qua"
        videos={data?.breakouts7d ?? []}
        isPending={isPending}
        emptyText="Chưa đủ dữ liệu — quay lại sau."
      />
      <RailSection
        kicker="VIDEO LEO ĐỈNH"
        title="Đang Viral"
        sub="Top 5 Viral Video trong ngách của bạn"
        videos={data?.virals ?? []}
        isPending={isPending}
        emptyText="Chưa có video trong corpus."
      />
    </div>
  );
});

function RailSection({
  kicker,
  title,
  sub,
  videos,
  isPending,
  emptyText,
}: {
  kicker: string;
  title: string;
  sub: string;
  videos: ReadonlyArray<RailVideo>;
  isPending: boolean;
  emptyText: string;
}) {
  return (
    <section aria-labelledby={`rail-${slug(title)}`}>
      <p className="gv-mono mb-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
        {kicker}
      </p>
      <h3
        id={`rail-${slug(title)}`}
        className="gv-tight m-0 mb-1 border-b border-[color:var(--gv-ink)] pb-2 text-[22px] font-semibold leading-none tracking-[-0.02em] text-[color:var(--gv-ink)]"
      >
        {title}
      </h3>
      <p className="gv-mono mb-3 text-[10px] text-[color:var(--gv-ink-4)]">
        {sub}
      </p>
      {isPending ? (
        <div className="flex flex-col gap-2.5">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-16 animate-pulse rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]"
            />
          ))}
        </div>
      ) : videos.length === 0 ? (
        <p className="m-0 rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-3 text-[12px] text-[color:var(--gv-ink-3)]">
          {emptyText}
        </p>
      ) : (
        <ul className="flex flex-col gap-2.5">
          {videos.map((v) => (
            <RailRow key={v.video_id} video={v} />
          ))}
        </ul>
      )}
    </section>
  );
}

function RailRow({ video }: { video: RailVideo }) {
  const navigate = useNavigate();
  const title =
    video.hook_phrase?.trim() && video.hook_phrase.trim().length > 0
      ? video.hook_phrase.trim()
      : "Video";
  const handle = video.creator_handle
    ? video.creator_handle.startsWith("@")
      ? video.creator_handle
      : `@${video.creator_handle}`
    : null;
  const ageLabel = video.posted_at
    ? formatRelativeSinceVi(new Date(), new Date(video.posted_at))
    : null;
  const thumbPh = railThumbPlaceholderStyle(video.video_id);
  return (
    <li>
      <button
        type="button"
        onClick={() =>
          navigate("/app/answer", {
            state: {
              prefillUrl: video.creator_handle
                ? `https://www.tiktok.com/@${video.creator_handle.replace(/^@/, "")}/video/${video.video_id}`
                : video.video_id,
            },
          })
        }
        className="grid w-full grid-cols-[44px_1fr] items-center gap-2.5 rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2.5 py-2 text-left transition-colors hover:border-[color:var(--gv-ink)]"
      >
        <span
          className={`relative overflow-hidden rounded ${thumbPh.wrapClass}`}
          style={{ aspectRatio: "9 / 16", height: 56 }}
          aria-hidden
        >
          <VideoThumbnail
            thumbnailUrl={video.thumbnail_url}
            className="absolute inset-0 h-full w-full"
            loading="lazy"
            placeholderClassName={thumbPh.placeholderClassName}
          />
        </span>
        <span className="min-w-0">
          <span className="m-0 line-clamp-2 text-[12px] leading-[1.3] text-[color:var(--gv-ink)]">
            {title}
          </span>
          <span className="gv-mono mt-1 block text-[10px] text-[color:var(--gv-ink-4)]">
            {[handle, video.views > 0 ? `↑${formatViews(video.views)}` : null, ageLabel]
              .filter(Boolean)
              .join(" · ")}
          </span>
        </span>
      </button>
    </li>
  );
}

function slug(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-");
}
