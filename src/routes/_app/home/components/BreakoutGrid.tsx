import { memo, useRef, useState, useCallback } from "react";
import { Link } from "react-router";
import { ArrowRight } from "lucide-react";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { VideoThumbnail } from "@/components/VideoThumbnail";
import { formatViews } from "@/lib/formatters";
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

/** Single breakout tile with hover-to-play video preview. */
function BreakoutTile({ v, idx }: { v: BreakoutVideo; idx: number }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);

  const dur = formatDuration(v.video_duration ?? undefined);
  const isBreakout = v.breakout_multiplier != null;
  const panelClass = v.thumbnail_url
    ? ""
    : (FALLBACK_PANEL[idx % FALLBACK_PANEL.length] ?? "bg-[color:var(--gv-ink-2)]");
  const hookShort =
    v.hook_phrase && v.hook_phrase.length > 48 ? `${v.hook_phrase.slice(0, 48)}…` : v.hook_phrase;

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
    <a
      key={v.video_id}
      href={v.tiktok_url}
      target="_blank"
      rel="noreferrer"
      className="group block text-left"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div
        className={`relative aspect-[4/5] w-full overflow-hidden rounded-[10px] border border-[color:var(--gv-rule)] ${!v.thumbnail_url ? panelClass : "bg-[color:var(--gv-ink)]"}`}
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

        {/* Hover-to-play hint — only shown when video is available and not playing */}
        {v.video_url && !playing ? (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-0 transition-opacity duration-200 group-hover:opacity-100">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-black/50 backdrop-blur-sm">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="white" aria-hidden>
                <path d="M3 2.5l10 5.5-10 5.5V2.5z" />
              </svg>
            </div>
          </div>
        ) : null}

        {v.thumbnail_url || playing ? (
          <div
            className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/75 via-black/20 to-transparent"
            aria-hidden
          />
        ) : null}
        <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-3.5 text-white">
          <div className="flex items-start justify-between gap-2">
            <span className="rounded px-2 py-0.5 gv-kicker text-white bg-[color:var(--gv-accent)]">
              {isBreakout ? "BỨT PHÁ" : "ĐANG THỊNH HÀNH"}
            </span>
            {dur ? <span className="gv-kicker opacity-95">{dur}</span> : null}
          </div>
          <div className="min-h-0 flex-1 flex flex-col justify-end pt-8">
            {v.hook_phrase ? (
              <p
                className="gv-tight line-clamp-4 text-[22px] leading-[1.1] text-white"
                style={{ textShadow: "0 2px 12px rgba(0,0,0,0.5)" }}
              >
                &ldquo;{v.hook_phrase}&rdquo;
              </p>
            ) : (
              <p className="gv-tight text-[22px] leading-[1.1] text-white/90" style={{ textShadow: "0 2px 12px rgba(0,0,0,0.5)" }}>
                @{v.creator_handle}
              </p>
            )}
          </div>
        </div>
      </div>
      <div className="mt-3 space-y-1">
        <div className="flex items-center justify-between gap-2">
          <span className="gv-kicker text-[color:var(--gv-ink-3)]">
            @{v.creator_handle}
          </span>
          <span className="gv-kicker text-[color:var(--gv-pos-deep)]">
            ↑ {formatViews(v.views)}
          </span>
        </div>
        {v.hook_phrase ? (
          <p className="text-[12px] text-[color:var(--gv-ink-3)]">
            Hook ·{" "}
            <span className="font-semibold text-[color:var(--gv-ink-2)]">
              &ldquo;{hookShort}&rdquo;
            </span>
          </p>
        ) : v.hook_type ? (
          <p className="text-[12px] text-[color:var(--gv-ink-3)]">
            Hook · <span className="font-semibold text-[color:var(--gv-ink-2)]">{v.hook_type}</span>
          </p>
        ) : null}
      </div>
    </a>
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
            <div key={i} className="flex flex-col gap-3">
              <div className="aspect-[4/5] animate-pulse rounded-[10px] bg-[color:var(--gv-canvas-2)]" />
              <div className="h-10 animate-pulse rounded-md bg-[color:var(--gv-canvas-2)]" />
            </div>
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
