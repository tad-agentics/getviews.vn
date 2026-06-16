import { memo, useCallback, useRef, useState } from "react";
import { Bookmark, Play } from "lucide-react";

import type { DouyinVideo } from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";

import {
  DOUYIN_SUB_VN_GREEN,
  douyinCardSubText,
  formatDuration,
  formatRelativeIso,
  formatRisePct,
} from "./douyinFormatters";

/**
 * D4b (2026-06-04) — Kho Douyin · single video card.
 *
 * Hover: muted loop preview when ``playback_url`` is banked on R2.
 * Click: opens ``DouyinVideoModal`` for full playback + metadata.
 */

function formatCardViews(views: number): string {
  if (!Number.isFinite(views) || views <= 0) return "—";
  return formatViews(views);
}

export type DouyinVideoCardProps = {
  video: DouyinVideo;
  saved: boolean;
  onToggleSave: (videoId: string) => void;
  onOpen?: (video: DouyinVideo) => void;
};

export const DouyinVideoCard = memo(function DouyinVideoCard({
  video,
  saved,
  onToggleSave,
  onOpen,
}: DouyinVideoCardProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [hoverClip, setHoverClip] = useState(false);
  const playbackSrc = video.playback_url?.trim() ?? "";
  const hasPlayback = Boolean(playbackSrc);

  const duration = formatDuration(video.video_duration);
  const relTime = formatRelativeIso(video.indexed_at);
  const rise = formatRisePct(video.cn_rise_pct);
  const viewsLabel = formatCardViews(video.views);
  const subText = douyinCardSubText(video);

  const startHoverClip = useCallback(() => {
    if (!hasPlayback) return;
    const el = videoRef.current;
    if (!el) return;
    if (!el.getAttribute("src")) {
      el.src = playbackSrc;
      el.load();
    }
    void el.play()
      .then(() => setHoverClip(true))
      .catch(() => setHoverClip(false));
  }, [hasPlayback, playbackSrc]);

  const stopHoverClip = useCallback(() => {
    setHoverClip(false);
    const el = videoRef.current;
    if (!el) return;
    el.pause();
    el.currentTime = 0;
  }, []);

  const handleCardClick = (): void => {
    if (onOpen) {
      onOpen(video);
      return;
    }
    if (video.douyin_url) {
      window.open(video.douyin_url, "_blank", "noopener,noreferrer");
    }
  };

  const handleSaveClick = (e: React.MouseEvent<HTMLButtonElement>): void => {
    e.stopPropagation();
    onToggleSave(video.video_id);
  };

  return (
    <article
      role="button"
      tabIndex={0}
      data-douyin-card
      onClick={handleCardClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleCardClick();
        }
      }}
      className="group flex flex-col cursor-pointer overflow-hidden rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] transition-[transform,box-shadow] duration-150 hover:-translate-y-0.5 hover:shadow-[0_10px_24px_rgba(0,0,0,0.10)]"
    >
      <div
        className="relative aspect-[9/16] w-full overflow-hidden bg-[color:var(--gv-ink)]"
        onMouseEnter={startHoverClip}
        onMouseLeave={stopHoverClip}
      >
        {hasPlayback ? (
          <video
            ref={videoRef}
            muted
            loop
            playsInline
            preload="none"
            className={
              "pointer-events-none absolute inset-0 z-[5] h-full w-full object-cover transition-opacity duration-200 ease-out " +
              (hoverClip ? "opacity-100" : "opacity-0")
            }
            aria-hidden
          />
        ) : null}

        <div
          className={
            "absolute inset-0 z-[8] transition-opacity duration-200 ease-out " +
            (hoverClip && hasPlayback ? "opacity-0" : "opacity-100")
          }
          style={
            video.thumbnail_url
              ? {
                  backgroundImage: `url(${video.thumbnail_url})`,
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                }
              : undefined
          }
        />

        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 z-10"
          style={{
            background:
              "linear-gradient(180deg, rgba(0,0,0,0.4) 0%, transparent 25%, transparent 60%, rgba(0,0,0,0.85) 100%)",
          }}
        />

        <div className="absolute left-2 right-2 top-2 z-20 flex items-start justify-between">
          <span
            className="gv-mono rounded px-1.5 py-0.5 text-[11px] gv-kicker tracking-[0.05em] text-white"
            style={{ background: "var(--gv-accent-deep)" }}
            aria-label="Nguồn Douyin Trung Quốc"
          >
            CN
          </span>
          {duration ? (
            <span
              className="gv-mono rounded px-1.5 py-0.5 text-[11px] text-white"
              style={{ background: "rgba(0,0,0,0.6)" }}
            >
              {duration}
            </span>
          ) : null}
        </div>

        <button
          type="button"
          onClick={handleSaveClick}
          aria-pressed={saved}
          aria-label={saved ? "Đã lưu — bấm để bỏ lưu" : "Lưu vào kho"}
          className={
            "absolute right-2 top-9 z-20 flex h-7 w-7 items-center justify-center rounded-full transition-colors " +
            (saved
              ? "bg-[color:var(--gv-accent)] text-white"
              : "bg-[color:rgba(0,0,0,0.55)] text-white hover:bg-[color:rgba(0,0,0,0.75)]")
          }
        >
          <Bookmark className="h-3.5 w-3.5" strokeWidth={2} />
        </button>

        {subText ? (
          <div
            className="absolute left-2 right-2 z-20 rounded p-1.5 text-center"
            style={{
              bottom: 60,
              background: "rgba(0,0,0,0.55)",
            }}
          >
            <p className="line-clamp-2 text-[11px] font-medium leading-[1.25] text-white">
              &quot;{subText}&quot;
            </p>
          </div>
        ) : null}

        <div className="absolute bottom-2 left-2.5 right-2.5 z-20 text-white">
          {video.creator_handle ? (
            <p className="gv-mono mb-0.5 truncate text-[11px] opacity-85">
              抖音 @{video.creator_handle}
            </p>
          ) : null}
          <div className="flex items-center justify-between gap-2 text-[11px]">
            <span className="gv-mono min-w-0 truncate font-semibold tabular-nums">
              {viewsLabel} view
            </span>
            {rise ? (
              <span
                className="gv-mono shrink-0"
                style={{ color: DOUYIN_SUB_VN_GREEN }}
                aria-label={`Tăng ${rise} so với 14 ngày trước`}
              >
                {rise}
              </span>
            ) : null}
          </div>
        </div>

        <span
          aria-hidden
          className={
            "pointer-events-none absolute left-1/2 top-1/2 z-20 flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white/80 transition-opacity duration-150 " +
            (hoverClip && hasPlayback ? "opacity-0" : "opacity-80 group-hover:opacity-100")
          }
        >
          <Play className="h-3.5 w-3.5 text-[color:var(--gv-ink)]" fill="currentColor" />
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-2 p-3">
        <div>
          <p className="line-clamp-2 text-sm leading-snug text-[color:var(--gv-ink)]">
            {video.title_vi || video.title_zh || ""}
          </p>
          {video.title_zh && video.title_vi ? (
            <p className="gv-mono mt-1 truncate text-[11px] italic text-[color:var(--gv-ink-3)]">
              {video.title_zh}
            </p>
          ) : null}
        </div>

        {relTime ? (
          <p className="gv-kicker mt-auto text-[color:var(--gv-ink-4)]">{relTime}</p>
        ) : null}
      </div>
    </article>
  );
});
