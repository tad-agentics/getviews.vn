import { memo, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import {
  ArrowRight,
  Bookmark,
  ExternalLink,
  Play,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { Btn } from "@/components/v2/Btn";
import type {
  DouyinTranslatorNote,
  DouyinVideo,
} from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";
import { scriptPrefillFromDeeplink } from "@/lib/scriptPrefill";

import {
  DOUYIN_SUB_VN_GREEN,
  formatDuration,
  formatRisePct,
} from "./douyinFormatters";

/**
 * D4d — Kho Douyin · video modal.
 *
 * Two-column shell: phone preview (R2 playback or thumb) + stats,
 * translator notes, and CTAs (lưu / mở Douyin / chuyển thể → Kịch bản).
 */

export type DouyinVideoModalProps = {
  video: DouyinVideo | null;
  open: boolean;
  onOpenChange: (next: boolean) => void;
  saved: boolean;
  onToggleSave: (videoId: string) => void;
};

export const DouyinVideoModal = memo(function DouyinVideoModal({
  video,
  open,
  onOpenChange,
  saved,
  onToggleSave,
}: DouyinVideoModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        overlayClassName="z-[400]"
        className="!z-[401] !max-w-[960px] gap-0 overflow-hidden border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] p-0"
      >
        {video ? (
          <DouyinVideoModalBody
            video={video}
            saved={saved}
            onToggleSave={onToggleSave}
            onClose={() => onOpenChange(false)}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
});


function DouyinVideoModalBody({
  video,
  saved,
  onToggleSave,
  onClose,
}: {
  video: DouyinVideo;
  saved: boolean;
  onToggleSave: (videoId: string) => void;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const titleVI = video.title_vi || video.title_zh || "(không có tiêu đề)";
  const subVI = video.sub_vi?.trim() || video.title_vi?.trim() || "";

  const handleAdaptToScript = (): void => {
    const topic = (video.title_vi || video.title_zh || "").slice(0, 200);
    const path =
      scriptPrefillFromDeeplink({
        topic: topic || null,
        hook: subVI ? subVI.slice(0, 240) : null,
        duration_sec:
          video.video_duration && Number.isFinite(video.video_duration)
            ? Math.round(video.video_duration)
            : null,
      }) ?? "/app/answer";
    onClose();
    navigate(path);
  };

  const handleOpenSource = (): void => {
    if (!video.douyin_url) return;
    window.open(video.douyin_url, "_blank", "noopener,noreferrer");
  };

  const handleSaveToggle = (): void => onToggleSave(video.video_id);

  return (
    <div className="grid max-h-[88vh] grid-cols-1 overflow-hidden md:grid-cols-[minmax(0,260px)_minmax(0,1fr)]">
      {/* ── Phone preview ─────────────────────────────────────────── */}
      <DouyinPhonePreview video={video} subVI={subVI} />

      {/* ── Info panel ────────────────────────────────────────────── */}
      <div className="flex max-h-[88vh] flex-col overflow-hidden">
        <header className="flex items-start justify-between gap-3 border-b border-[color:var(--gv-rule)] px-6 py-5">
          <div className="min-w-0 flex-1">
            <p className="gv-mono mb-1 text-[11px] gv-kicker tracking-[0.06em] text-[color:var(--gv-accent-deep)]">
              Video Douyin
            </p>
            <DialogTitle
              className="gv-tight m-0 text-[22px] font-medium leading-tight text-[color:var(--gv-ink)]"
              style={{ fontFamily: "var(--gv-font-display)" }}
            >
              {titleVI}
            </DialogTitle>
            {video.title_zh && video.title_vi ? (
              <p className="gv-mono mt-1 text-[11px] italic text-[color:var(--gv-ink-3)]">
                {video.title_zh}
              </p>
            ) : null}
          </div>
          <DialogClose asChild>
            <button
              type="button"
              aria-label="Đóng"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[color:var(--gv-ink-3)] transition-colors hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink)]"
            >
              <X className="h-4 w-4" strokeWidth={2} aria-hidden />
            </button>
          </DialogClose>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <StatsGrid video={video} />
          <TranslatorNotesSection notes={video.translator_notes} />
        </div>

        <footer className="flex flex-wrap items-center gap-2 border-t border-[color:var(--gv-rule)] px-6 py-4">
          <button
            type="button"
            onClick={handleSaveToggle}
            aria-pressed={saved}
            aria-label={saved ? "Bỏ lưu" : "Lưu vào kho"}
            className={
              "inline-flex h-9 items-center gap-1.5 rounded-full border px-3.5 text-[12px] transition-colors " +
              (saved
                ? "border-[color:var(--gv-accent)] bg-[color:var(--gv-accent)] font-semibold text-white"
                : "border-[color:var(--gv-rule)] bg-transparent font-medium text-[color:var(--gv-ink-2)] hover:border-[color:var(--gv-ink-4)]")
            }
          >
            <Bookmark className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
            {saved ? "Đã lưu" : "Lưu vào kho"}
          </button>

          {video.douyin_url ? (
            <Btn variant="ghost" size="sm" type="button" onClick={handleOpenSource}>
              <ExternalLink className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
              Mở trên Douyin
            </Btn>
          ) : null}

          <div className="ml-auto">
            <Btn variant="ink" size="sm" type="button" onClick={handleAdaptToScript}>
              Chuyển thể sang VN → Kịch bản
              <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
            </Btn>
          </div>
        </footer>
      </div>
    </div>
  );
}


function DouyinPhonePreview({
  video,
  subVI,
}: {
  video: DouyinVideo;
  subVI: string;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [muted, setMuted] = useState(true);
  const [autoplayBlocked, setAutoplayBlocked] = useState(false);
  const playbackSrc = video.playback_url?.trim() ?? "";
  const hasPlayback = Boolean(playbackSrc);

  useEffect(() => {
    if (!hasPlayback) return;
    const el = videoRef.current;
    if (!el) return;
    void el.play().catch(() => setAutoplayBlocked(true));
  }, [hasPlayback, playbackSrc]);

  const handleManualPlay = useCallback(() => {
    setAutoplayBlocked(false);
    void videoRef.current?.play().catch(() => setAutoplayBlocked(true));
  }, []);

  return (
    <div className="relative bg-[color:var(--gv-ink)] md:min-h-[480px]">
      <div className="relative aspect-[9/16] w-full overflow-hidden">
        {hasPlayback ? (
          <video
            ref={videoRef}
            key={playbackSrc}
            src={playbackSrc}
            poster={video.thumbnail_url ?? undefined}
            autoPlay
            loop
            playsInline
            muted={muted}
            controls
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : (
          <div
            className="absolute inset-0"
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
        )}

        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "linear-gradient(180deg, rgba(0,0,0,0.4) 0%, transparent 28%, transparent 60%, rgba(0,0,0,0.85) 100%)",
          }}
        />

        <span
          className="gv-mono absolute left-2 top-2 z-10 rounded px-1.5 py-0.5 text-[11px] gv-kicker tracking-[0.05em] text-white"
          style={{ background: "var(--gv-accent-deep)" }}
          aria-label="Nguồn Douyin Trung Quốc"
        >
          CN
        </span>

        {hasPlayback ? (
          <button
            type="button"
            onClick={() => setMuted((v) => !v)}
            aria-label={muted ? "Bật tiếng" : "Tắt tiếng"}
            aria-pressed={!muted}
            className="absolute right-2 top-2 z-20 flex h-9 w-9 items-center justify-center rounded-full bg-black/45 text-white backdrop-blur-sm"
          >
            {muted ? (
              <VolumeX className="h-4 w-4" strokeWidth={2} aria-hidden />
            ) : (
              <Volume2 className="h-4 w-4" strokeWidth={2} aria-hidden />
            )}
          </button>
        ) : null}

        {autoplayBlocked && hasPlayback ? (
          <button
            type="button"
            onClick={handleManualPlay}
            aria-label="Phát video"
            className="absolute inset-0 z-[15] flex items-center justify-center bg-black/35 text-white"
          >
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white/85 text-[color:var(--gv-ink)]">
              <Play className="h-4 w-4" fill="currentColor" aria-hidden />
            </span>
          </button>
        ) : null}

        {subVI ? (
          <div
            className="pointer-events-none absolute left-2 right-2 z-10 rounded p-1.5 text-center"
            style={{ bottom: 60, background: "rgba(0,0,0,0.55)" }}
          >
            <p
              className="gv-mono mb-0.5 text-[11px] gv-kicker tracking-[0.05em]"
              style={{ color: DOUYIN_SUB_VN_GREEN }}
            >
              Sub VN
            </p>
            <p className="line-clamp-2 text-[11px] font-medium leading-[1.25] text-white">
              &quot;{subVI}&quot;
            </p>
          </div>
        ) : null}

        <div className="pointer-events-none absolute bottom-2 left-2.5 right-2.5 z-10 text-white">
          {video.creator_handle ? (
            <p className="gv-mono mb-0.5 truncate text-[11px] opacity-85">
              抖音 @{video.creator_handle}
            </p>
          ) : null}
          <div className="flex items-center justify-between text-[11px]">
            <span className="gv-mono">↑ {formatViews(video.views)}</span>
          </div>
        </div>

        {!hasPlayback ? (
          <span
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-1/2 flex h-12 w-12 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white/85"
          >
            <Play className="h-4 w-4 text-[color:var(--gv-ink)]" fill="currentColor" />
          </span>
        ) : null}
      </div>
    </div>
  );
}


// ── Stats grid ──────────────────────────────────────────────────────


/**
 * D7 (2026-06-06) — stat grid aligned with design pack
 * ``screens/douyin.jsx`` lines 1078-1086. Design specifies a 2×2
 * grid with VIEW / SAVE / TĂNG 14N / THỜI LƯỢNG. The earlier 4-up
 * grid (VIEW / LIKE / LƯU / ER%) duplicated the rise figure (also
 * shown on the adapt strip) and dropped the duration entirely.
 */
function StatsGrid({ video }: { video: DouyinVideo }) {
  const rise = formatRisePct(video.cn_rise_pct);
  const duration = formatDuration(video.video_duration);
  return (
    <section
      className="mb-5 grid grid-cols-2 gap-x-4 gap-y-3 border-b border-[color:var(--gv-rule)] pb-5"
      aria-label="Chỉ số gốc"
    >
      <Stat label="View" value={formatViews(video.views)} />
      <Stat label="Save" value={formatViews(video.saves)} />
      <Stat
        label="Tăng 14N"
        value={rise ?? "—"}
        valueClassName={
          rise ? "text-[color:var(--gv-pos-deep)]" : undefined
        }
      />
      <Stat label="Thời lượng" value={duration ?? "—"} />
    </section>
  );
}


function Stat({
  label,
  value,
  valueClassName,
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div>
      <p className="gv-mono mb-1 text-[11px] gv-kicker tracking-[0.06em] text-[color:var(--gv-ink-3)]">
        {label}
      </p>
      <p
        className={
          "gv-tight m-0 text-[22px] leading-none " +
          (valueClassName ?? "text-[color:var(--gv-ink)]")
        }
        style={{ fontFamily: "var(--gv-font-display)" }}
      >
        {value}
      </p>
    </div>
  );
}


// ── Translator notes ────────────────────────────────────────────────


function TranslatorNotesSection({ notes }: { notes: DouyinTranslatorNote[] }) {
  if (!notes || notes.length === 0) return null;
  return (
    <section aria-label="Chú thích văn hóa">
      <p className="gv-mono mb-2 text-[11px] font-semibold gv-kicker tracking-[0.06em] text-[color:var(--gv-accent-deep)]">
        Chú thích văn hóa ({notes.length})
      </p>
      <ul className="space-y-2">
        {notes.map((note, idx) => (
          <li
            key={`${note.tag}-${idx}`}
            className="flex items-start gap-2 rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] p-3"
          >
            <span
              className="gv-mono inline-flex shrink-0 items-center rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2 py-0.5 text-[11px] font-semibold gv-kicker tracking-[0.05em] text-[color:var(--gv-ink-2)]"
              data-tag={note.tag}
            >
              {note.tag}
            </span>
            <p className="text-[12px] leading-snug text-[color:var(--gv-ink-2)]">
              {note.note}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}


// Formatters live in ``./douyinFormatters`` (D6b consolidation).
