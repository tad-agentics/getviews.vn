import { memo } from "react";
import { Bookmark, Play } from "lucide-react";

import type { DouyinVideo } from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";

import {
  ADAPT_META,
  DOUYIN_SUB_VN_GREEN,
  PENDING_ADAPT_META,
  formatDuration,
  formatRelativeIso,
  formatRisePct,
} from "./douyinFormatters";

/**
 * D4b (2026-06-04) — Kho Douyin · single video card.
 *
 * Per design pack ``screens/douyin.jsx`` lines 829-948: 9:16 thumbnail
 * with overlays (CN flag chip top-left, duration top-right, save
 * toggle below duration, mock VN sub band centered, handle + views
 * bottom, play hint center) plus a body section with title VN + title
 * ZH (italic) + adapt chip + relative time.
 *
 * Card click is currently a no-op (D4d ships the modal). Until then,
 * if a ``douyin_url`` is present we open it in a new tab as a graceful
 * fallback so the user can at least see the original Douyin page.
 *
 * Save toggle stops propagation so it doesn't bubble into the card
 * click. localStorage persistence lives on the parent screen via
 * ``useDouyinSavedSet``.
 */

// ADAPT_META + PENDING_ADAPT_META + formatters live in
// ``./douyinFormatters`` (D6b consolidation — audit finding H4).


// ── Card ────────────────────────────────────────────────────────────


export type DouyinVideoCardProps = {
  video: DouyinVideo;
  saved: boolean;
  onToggleSave: (videoId: string) => void;
  /** D4d wires this to the modal. Until then the card opens
   *  ``douyin_url`` externally as a fallback. */
  onOpen?: (video: DouyinVideo) => void;
};

export const DouyinVideoCard = memo(function DouyinVideoCard({
  video,
  saved,
  onToggleSave,
  onOpen,
}: DouyinVideoCardProps) {
  const meta = video.adapt_level ? ADAPT_META[video.adapt_level] : PENDING_ADAPT_META;
  const duration = formatDuration(video.video_duration);
  const relTime = formatRelativeIso(video.indexed_at);
  const rise = formatRisePct(video.cn_rise_pct);
  const subText = (video.sub_vi || video.title_vi || video.title_zh || "").trim();

  const handleCardClick = (): void => {
    if (onOpen) {
      onOpen(video);
      return;
    }
    // D4d-pending fallback: open the Douyin source in a new tab.
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
      onClick={handleCardClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleCardClick();
        }
      }}
      className="group flex flex-col cursor-pointer overflow-hidden rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] transition-[transform,box-shadow] duration-150 hover:-translate-y-0.5 hover:shadow-[0_10px_24px_rgba(0,0,0,0.10)]"
    >
      {/* 9:16 thumbnail with overlays */}
      <div
        className="relative aspect-[9/16] w-full overflow-hidden bg-[color:var(--gv-ink)]"
        style={
          video.thumbnail_url
            ? {
                backgroundImage: `url(${video.thumbnail_url})`,
                backgroundSize: "cover",
                backgroundPosition: "center",
              }
            : undefined
        }
      >
        {/* Vertical gradient — top dim → middle clear → bottom dark
            for legibility of overlays. */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "linear-gradient(180deg, rgba(0,0,0,0.4) 0%, transparent 25%, transparent 60%, rgba(0,0,0,0.85) 100%)",
          }}
        />

        {/* Top row — CN flag + duration */}
        <div className="absolute left-2 right-2 top-2 flex items-start justify-between">
          <span
            className="gv-mono rounded px-1.5 py-0.5 text-[9px] uppercase tracking-[0.05em] text-white"
            style={{ background: "var(--gv-accent-deep)" }}
            aria-label="Nguồn Douyin Trung Quốc"
          >
            🇨🇳
          </span>
          {duration ? (
            <span
              className="gv-mono rounded px-1.5 py-0.5 text-[10px] text-white"
              style={{ background: "rgba(0,0,0,0.6)" }}
            >
              {duration}
            </span>
          ) : null}
        </div>

        {/* Save toggle — top-right, below duration */}
        <button
          type="button"
          onClick={handleSaveClick}
          aria-pressed={saved}
          aria-label={saved ? "Đã lưu — bấm để bỏ lưu" : "Lưu vào kho"}
          className={
            "absolute right-2 top-9 flex h-7 w-7 items-center justify-center rounded-full transition-colors " +
            (saved
              ? "bg-[color:var(--gv-accent)] text-white"
              : "bg-[color:rgba(0,0,0,0.55)] text-white hover:bg-[color:rgba(0,0,0,0.75)]")
          }
        >
          <Bookmark className="h-3.5 w-3.5" strokeWidth={2} />
        </button>

        {/* Mock VN sub band — centered */}
        {subText ? (
          <div
            className="absolute left-2 right-2 rounded p-1.5 text-center"
            style={{
              bottom: 60,
              background: "rgba(0,0,0,0.55)",
            }}
          >
            <p
              className="gv-mono mb-0.5 text-[7px] uppercase tracking-[0.05em]"
              style={{ color: DOUYIN_SUB_VN_GREEN }}
            >
              Sub VN
            </p>
            <p className="line-clamp-2 text-[11px] font-medium leading-[1.25] text-white">
              &quot;{subText}&quot;
            </p>
          </div>
        ) : null}

        {/* Bottom — handle + views + rise */}
        <div className="absolute bottom-2 left-2.5 right-2.5 text-white">
          {video.creator_handle ? (
            <p className="gv-mono mb-0.5 truncate text-[9.5px] opacity-85">
              抖音 @{video.creator_handle}
            </p>
          ) : null}
          <div className="flex items-center justify-between text-[10px]">
            <span className="gv-mono">↑ {formatViews(video.views)}</span>
            {rise ? (
              <span
                className="gv-mono"
                style={{ color: DOUYIN_SUB_VN_GREEN }}
                aria-label={`Tăng ${rise} so với 14 ngày trước`}
              >
                {rise}
              </span>
            ) : null}
          </div>
        </div>

        {/* Play hint — center, only on hover-capable devices to avoid
            chrome on touch */}
        <span
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-1/2 flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white/80 opacity-80 transition-opacity duration-150 group-hover:opacity-100"
        >
          <Play className="h-3.5 w-3.5 text-[color:var(--gv-ink)]" fill="currentColor" />
        </span>
      </div>

      {/* Body */}
      <div className="flex flex-1 flex-col gap-2 p-3">
        <div>
          <p className="line-clamp-2 text-[13.5px] leading-snug text-[color:var(--gv-ink)]">
            {video.title_vi || video.title_zh || ""}
          </p>
          {video.title_zh && video.title_vi ? (
            <p className="gv-mono mt-1 truncate text-[10px] italic text-[color:var(--gv-ink-4)]">
              {video.title_zh}
            </p>
          ) : null}
        </div>

        {/* Adapt chip + relative time */}
        <div className="mt-auto flex flex-wrap items-center gap-2">
          <span
            className={
              "gv-mono inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.05em] " +
              meta.toneClass
            }
            data-adapt-level={video.adapt_level ?? "pending"}
          >
            <span
              aria-hidden
              className="block h-1 w-1 rounded-full bg-current"
            />
            {meta.short}
          </span>
          {relTime ? (
            <span className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">
              {relTime}
            </span>
          ) : null}
        </div>
      </div>
    </article>
  );
});

// ADAPT_META + PENDING_ADAPT_META are exported from
// ``./douyinFormatters`` (D6b). Toolbar / Modal / PatternCard import
// directly from there; no re-export needed here.
