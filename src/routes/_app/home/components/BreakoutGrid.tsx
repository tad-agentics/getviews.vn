import { memo, useRef, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowRight } from "lucide-react";
import { CarouselBadge } from "@/components/CarouselBadge";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { VideoThumbnail } from "@/components/VideoThumbnail";
import { formatViews } from "@/lib/formatters";
import { logUsage } from "@/lib/logUsage";
import { useTopBreakouts, type BreakoutVideo } from "@/hooks/useTopBreakouts";

/**
 * BreakoutGrid — UIUX `home.jsx`: 4/5 tiles, gap 18px, BREAKOUT + duration,
 * 22px quoted title on panel, mono row + ↑ views in pos-deep below.
 */

function formatDuration(sec: number | string | null | undefined): string | null {
  const n = sec == null ? NaN : Number(sec);
  if (!Number.isFinite(n) || n <= 0) return null;
  const m = Math.floor(n / 60);
  const s = Math.floor(n % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const FALLBACK_PANEL = [
  "bg-[color:var(--gv-avatar-2)]",
  "bg-[color:var(--gv-avatar-6)]",
  "bg-[color:var(--gv-avatar-4)]",
] as const;

/** Answer-session handoff for a corpus breakout tile (mirrors Explore preview analyze). */
export function breakoutAnalyzePath(v: Pick<BreakoutVideo, "video_id" | "tiktok_url" | "creator_handle">): string {
  const handle = v.creator_handle.replace(/^@/, "");
  const q =
    v.tiktok_url?.trim() ||
    (handle
      ? `https://www.tiktok.com/@${handle}/video/${v.video_id}`
      : v.video_id);
  return `/app/answer?q=${encodeURIComponent(q)}&depth=basic&mode=win&from=home-breakout`;
}

/** Single breakout tile with hover-to-play video preview. */
function BreakoutTile({ v, idx }: { v: BreakoutVideo; idx: number }) {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);

  const dur = formatDuration(v.video_duration ?? undefined);
  const isBreakout = v.breakout_multiplier != null;
  const panelClass = v.thumbnail_url
    ? ""
    : (FALLBACK_PANEL[idx % FALLBACK_PANEL.length] ?? "bg-[color:var(--gv-ink-2)]");
  const hookShort =
    v.hook_phrase && v.hook_phrase.length > 48 ? `${v.hook_phrase.slice(0, 48)}…` : v.hook_phrase;
  const handleLabel = v.creator_handle.startsWith("@")
    ? v.creator_handle
    : `@${v.creator_handle}`;
  const analyzeLabel = v.hook_phrase
    ? `Phân tích video ${handleLabel}: ${v.hook_phrase}`
    : `Phân tích video ${handleLabel}`;

  const handleMouseEnter = useCallback(() => {
    if (!v.video_url || !videoRef.current) return;
    videoRef.current.currentTime = 0;
    void videoRef.current.play().then(() => setPlaying(true)).catch(() => {});
  }, [v.video_url]);

  const handleMouseLeave = useCallback(() => {
    if (!videoRef.current) return;
    videoRef.current.pause();
    videoRef.current.currentTime = 0;
    setPlaying(false);
  }, []);

  return (
    <div className="flex w-full flex-col">
      <div
        className={`relative aspect-[4/5] w-full overflow-hidden rounded-[10px] border border-[color:var(--gv-rule)] transition-colors duration-[120ms] hover:border-[color:var(--gv-ink)] ${!v.thumbnail_url ? panelClass : "bg-[color:var(--gv-ink)]"}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {/* Thumbnail — fades out when video is playing */}
        <div className={`absolute inset-0 transition-opacity duration-300 ${playing ? "opacity-0" : "opacity-100"}`}>
          <VideoThumbnail
            thumbnailUrl={v.thumbnail_url}
            videoId={v.video_id}
            className="h-full w-full"
            placeholderClassName=""
          />
        </div>

        {/* Video — renders only when a URL is available */}
        {v.video_url ? (
          <video
            ref={videoRef}
            src={v.video_url}
            muted
            loop
            playsInline
            preload="none"
            className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-300 ${playing ? "opacity-100" : "opacity-0"}`}
          />
        ) : null}

        <div
          className="pointer-events-none absolute inset-0 z-[15] bg-gradient-to-b from-transparent from-40% to-black/70"
          aria-hidden
        />
        <div className="pointer-events-none absolute inset-0 z-20 flex flex-col justify-between p-3.5 text-white">
          <div className="flex items-start justify-between gap-2">
            <span
              className={
                isBreakout
                  ? "rounded-[3px] px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-[color:var(--gv-paper)] bg-[color:var(--gv-accent)]"
                  : "rounded-[3px] px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-[color:var(--gv-ink)] bg-[color:var(--gv-accent-2)]"
              }
            >
              {isBreakout ? "BỨT PHÁ" : "ĐANG THỊNH HÀNH"}
            </span>
            {v.content_type === "carousel" ? (
              <CarouselBadge className="border-white/40 bg-black/45 text-white" />
            ) : dur ? (
              <span className="gv-kicker opacity-95">{dur}</span>
            ) : null}
          </div>
          <div className="min-h-0">
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="min-w-0 truncate gv-kicker text-[11px] text-white">{handleLabel}</span>
              <span className="shrink-0 gv-mono text-[11px] font-semibold tabular-nums text-white">
                ↑ {formatViews(v.views)} view
              </span>
            </div>
            {v.hook_phrase ? (
              <p className="line-clamp-2 text-[12px] font-medium leading-tight">
                Hook · &ldquo;{hookShort}&rdquo;
              </p>
            ) : v.hook_type ? (
              <p className="line-clamp-2 text-[12px] font-medium leading-tight">
                Hook · {v.hook_type}
              </p>
            ) : null}
            <button
              type="button"
              aria-label={analyzeLabel}
              onClick={(e) => {
                e.stopPropagation();
                logUsage("home_breakout_analyze_click", { video_id: v.video_id });
                navigate(breakoutAnalyzePath(v));
              }}
              className="pointer-events-auto mt-1.5 flex min-h-[32px] w-full cursor-pointer items-center rounded-md border border-white/25 bg-black/45 px-2 py-1 text-left text-[11px] leading-tight text-white/90 backdrop-blur-[2px] transition-colors duration-[120ms] hover:border-[color:color-mix(in_srgb,var(--gv-accent)_70%,white)] hover:bg-[color:color-mix(in_srgb,var(--gv-accent)_42%,transparent)] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--gv-accent)]"
            >
              Phân tích video →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export const BreakoutGrid = memo(function BreakoutGrid({
  creatorNicheId,
  embedded = false,
}: {
  creatorNicheId: number | null;
  embedded?: boolean;
}) {
  const { data: videos, isPending } = useTopBreakouts(creatorNicheId, 3);

  const headerRight = (
    <Link
      to="/app/trends"
      className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1.5 text-xs font-medium text-[color:var(--gv-ink-2)] transition-colors hover:border-[color:var(--gv-ink)] hover:text-[color:var(--gv-ink)]"
    >
      Xem tất cả
      <ArrowRight className="h-3 w-3" aria-hidden />
    </Link>
  );

  if (isPending) {
    return (
      <section>
        {!embedded ? (
          <SectionHeader
            kicker="BIÊN TẬP CHỌN"
            title="3 video bứt phá"
            caption="Lượng xem vượt trội gấp 10 lần so với trung bình kênh trong 48 giờ qua."
            right={headerRight}
          />
        ) : null}
        <div className="grid [grid-template-columns:repeat(auto-fit,minmax(280px,1fr))] gap-[18px]">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="aspect-[4/5] animate-pulse rounded-[10px] bg-[color:var(--gv-canvas-2)]"
            />
          ))}
        </div>
      </section>
    );
  }

  if (!videos || videos.length === 0) {
    return (
      <section>
        {!embedded ? (
          <SectionHeader
            kicker="BIÊN TẬP CHỌN"
            title="3 video bứt phá"
            caption="Lượng xem vượt trội gấp 10 lần so với trung bình kênh trong 48 giờ qua."
            right={headerRight}
          />
        ) : null}
        <p className="mt-0 max-w-prose text-[14px] leading-relaxed text-[color:var(--gv-ink-3)]">
          Chưa có video bứt phá nào trong kho dữ liệu tuần này. Khi hệ thống cập nhật các video bứt phá mới nhất,
          nội dung sẽ xuất hiện tại đây. Bạn có thể xem các video thịnh hành khác ở mục{" "}
          <Link to="/app/trends" className="font-semibold text-[color:var(--gv-ink)] underline-offset-2 hover:underline">
            Xu hướng
          </Link>
          .
        </p>
      </section>
    );
  }

  return (
    <section>
      {!embedded ? (
        <SectionHeader
          kicker="BIÊN TẬP CHỌN"
          title="3 video bứt phá"
          caption="Lượng xem vượt trội gấp 10 lần so với trung bình kênh trong 48 giờ qua."
          right={headerRight}
        />
      ) : null}
      <div className="grid [grid-template-columns:repeat(auto-fit,minmax(280px,1fr))] gap-[18px]">
        {videos.map((v: BreakoutVideo, idx: number) => (
          <BreakoutTile key={v.video_id} v={v} idx={idx} />
        ))}
      </div>
    </section>
  );
});
