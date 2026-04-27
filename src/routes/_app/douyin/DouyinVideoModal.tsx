import { memo } from "react";
import { useNavigate } from "react-router";
import {
  ArrowRight,
  Bookmark,
  ExternalLink,
  Play,
  X,
} from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { Btn } from "@/components/v2/Btn";
import type {
  DouyinAdaptLevel,
  DouyinTranslatorNote,
  DouyinVideo,
} from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";

import {
  ADAPT_META,
  DOUYIN_SUB_VN_GREEN,
  PENDING_ADAPT_META,
  formatEngagementPct,
  formatEtaWeeks,
  formatRisePct,
} from "./douyinFormatters";

/**
 * D4d (2026-06-04) — Kho Douyin · video modal.
 *
 * Per design pack ``screens/douyin.jsx`` lines 949-1240. Two-column
 * shell:
 *   • Left: 9:16 phone preview with thumbnail / overlays / Sub VN band.
 *   • Right: title VN + ZH, mini stat grid, adapt strip with reason +
 *           ETA + cn_rise_pct, NOTE VĂN HOÁ section (one row per
 *           translator note tagged TỪ NGỮ / BỐI CẢNH / NHẠC NỀN /
 *           ĐẠO CỤ / KHÔNG LỜI / TITLE), and a 3-button CTA row.
 *
 * The "Adapt sang VN → Kịch bản" CTA navigates to ``/app/script`` with
 * the ``title_vi`` pre-filled as ``topic`` and ``sub_vi`` (or
 * ``title_vi`` fallback) as ``hook``. The script screen already
 * handles ``?topic=&hook=&duration=&niche_id=`` query-prefill from
 * Trends / Channel / Video.
 *
 * Synth-pending rows (``adapt_level=null``) render the CHỜ chip and
 * suppress the reason / ETA / cn_rise lines + translator notes section
 * — they have no graded content yet.
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
        className="!max-w-[960px] gap-0 overflow-hidden border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] p-0"
        onInteractOutside={() => onOpenChange(false)}
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
    const params = new URLSearchParams();
    const topic = (video.title_vi || video.title_zh || "").slice(0, 200);
    if (topic) params.set("topic", topic);
    if (subVI) params.set("hook", subVI.slice(0, 240));
    if (video.video_duration && Number.isFinite(video.video_duration)) {
      params.set("duration", String(Math.round(video.video_duration)));
    }
    onClose();
    navigate(`/app/script?${params.toString()}`);
  };

  const handleOpenSource = (): void => {
    if (!video.douyin_url) return;
    window.open(video.douyin_url, "_blank", "noopener,noreferrer");
  };

  const handleSaveToggle = (): void => onToggleSave(video.video_id);

  return (
    <div className="grid max-h-[88vh] grid-cols-1 overflow-hidden md:grid-cols-[minmax(0,260px)_minmax(0,1fr)]">
      {/* ── Phone preview ─────────────────────────────────────────── */}
      <div className="relative bg-[color:var(--gv-ink)] md:min-h-[480px]">
        <div
          className="relative aspect-[9/16] w-full overflow-hidden"
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
          {/* Top dim → bottom dark gradient for overlay legibility */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "linear-gradient(180deg, rgba(0,0,0,0.4) 0%, transparent 28%, transparent 60%, rgba(0,0,0,0.85) 100%)",
            }}
          />

          {/* CN flag top-left */}
          <span
            className="gv-mono absolute left-2 top-2 rounded px-1.5 py-0.5 text-[9px] uppercase tracking-[0.05em] text-white"
            style={{ background: "var(--gv-accent-deep)" }}
            aria-label="Nguồn Douyin Trung Quốc"
          >
            🇨🇳
          </span>

          {/* Sub VN band */}
          {subVI ? (
            <div
              className="absolute left-2 right-2 rounded p-1.5 text-center"
              style={{ bottom: 60, background: "rgba(0,0,0,0.55)" }}
            >
              <p
                className="gv-mono mb-0.5 text-[7px] uppercase tracking-[0.05em]"
                style={{ color: DOUYIN_SUB_VN_GREEN }}
              >
                Sub VN
              </p>
              <p className="line-clamp-2 text-[11px] font-medium leading-[1.25] text-white">
                &quot;{subVI}&quot;
              </p>
            </div>
          ) : null}

          {/* Bottom — handle + views */}
          <div className="absolute bottom-2 left-2.5 right-2.5 text-white">
            {video.creator_handle ? (
              <p className="gv-mono mb-0.5 truncate text-[9.5px] opacity-85">
                抖音 @{video.creator_handle}
              </p>
            ) : null}
            <div className="flex items-center justify-between text-[10px]">
              <span className="gv-mono">↑ {formatViews(video.views)}</span>
            </div>
          </div>

          {/* Center play hint */}
          <span
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-1/2 flex h-12 w-12 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white/85"
          >
            <Play className="h-4 w-4 text-[color:var(--gv-ink)]" fill="currentColor" />
          </span>
        </div>
      </div>

      {/* ── Info panel ────────────────────────────────────────────── */}
      <div className="flex max-h-[88vh] flex-col overflow-hidden">
        <header className="flex items-start justify-between gap-3 border-b border-[color:var(--gv-rule)] px-6 py-5">
          <div className="min-w-0 flex-1">
            <p className="gv-mono mb-1 text-[10px] uppercase tracking-[0.06em] text-[color:var(--gv-accent-deep)]">
              Video Douyin
            </p>
            <DialogTitle
              className="gv-tight m-0 text-[22px] font-medium leading-tight text-[color:var(--gv-ink)]"
              style={{ fontFamily: "var(--gv-font-display)" }}
            >
              {titleVI}
            </DialogTitle>
            {video.title_zh && video.title_vi ? (
              <p className="gv-mono mt-1 text-[11px] italic text-[color:var(--gv-ink-4)]">
                {video.title_zh}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[color:var(--gv-ink-3)] transition-colors hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink)]"
          >
            <X className="h-4 w-4" strokeWidth={2} />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <StatsGrid video={video} />
          <AdaptStrip video={video} />
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
              Adapt sang VN → Kịch bản
              <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
            </Btn>
          </div>
        </footer>
      </div>
    </div>
  );
}


// ── Stats grid ──────────────────────────────────────────────────────


function StatsGrid({ video }: { video: DouyinVideo }) {
  const er = formatEngagementPct(video.engagement_rate);
  return (
    <section
      className="mb-5 grid grid-cols-4 gap-3 border-b border-[color:var(--gv-rule)] pb-5"
      aria-label="Chỉ số gốc"
    >
      <Stat label="View" value={formatViews(video.views)} />
      <Stat label="Like" value={formatViews(video.likes)} />
      <Stat label="Lưu" value={formatViews(video.saves)} />
      <Stat label="ER %" value={er} />
    </section>
  );
}


function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="gv-mono mb-1 text-[9px] uppercase tracking-[0.06em] text-[color:var(--gv-ink-4)]">
        {label}
      </p>
      <p
        className="gv-tight m-0 text-[20px] leading-none text-[color:var(--gv-ink)]"
        style={{ fontFamily: "var(--gv-font-display)" }}
      >
        {value}
      </p>
    </div>
  );
}


// ── Adapt strip ─────────────────────────────────────────────────────


function AdaptStrip({ video }: { video: DouyinVideo }) {
  const meta =
    video.adapt_level !== null
      ? ADAPT_META[video.adapt_level as DouyinAdaptLevel]
      : null;
  const eta = formatEtaWeeks(video.eta_weeks_min, video.eta_weeks_max);
  const rise = formatRisePct(video.cn_rise_pct);

  return (
    <section
      className="mb-5 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4"
      aria-label="Đánh giá khả năng adapt"
    >
      <p className="gv-mono mb-2 text-[9px] font-semibold uppercase tracking-[0.06em] text-[color:var(--gv-accent-deep)]">
        Khả năng adapt sang VN
      </p>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span
          className={
            "gv-mono inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.05em] " +
            (meta ? meta.toneClass : PENDING_ADAPT_META.toneClass)
          }
          data-adapt-level={video.adapt_level ?? "pending"}
        >
          <span aria-hidden className="block h-1 w-1 rounded-full bg-current" />
          {meta ? meta.short : "CHỜ"}
        </span>
        <span className="text-[12px] text-[color:var(--gv-ink-2)]">
          {meta ? meta.label : "Đang chờ duyệt — synth chưa chấm row này."}
        </span>
      </div>

      {video.adapt_reason ? (
        <p className="mb-2 text-[13px] leading-snug text-[color:var(--gv-ink-2)]">
          {video.adapt_reason}
        </p>
      ) : null}

      {(eta || rise) && video.adapt_level !== null ? (
        <dl className="mt-2 grid grid-cols-2 gap-3 text-[11px]">
          {eta ? (
            <div>
              <dt className="gv-mono text-[9px] uppercase tracking-[0.06em] text-[color:var(--gv-ink-4)]">
                ETA về VN
              </dt>
              <dd className="gv-mono mt-0.5 text-[12px] text-[color:var(--gv-ink)]">
                {eta}
              </dd>
            </div>
          ) : null}
          {rise ? (
            <div>
              <dt className="gv-mono text-[9px] uppercase tracking-[0.06em] text-[color:var(--gv-ink-4)]">
                Đà ở CN (14 ngày)
              </dt>
              <dd
                className="gv-mono mt-0.5 text-[12px]"
                style={{ color: "var(--gv-pos-deep)" }}
              >
                {rise}
              </dd>
            </div>
          ) : null}
        </dl>
      ) : null}
    </section>
  );
}


// ── Translator notes ────────────────────────────────────────────────


function TranslatorNotesSection({ notes }: { notes: DouyinTranslatorNote[] }) {
  if (!notes || notes.length === 0) return null;
  return (
    <section aria-label="Note văn hoá">
      <p className="gv-mono mb-2 text-[9px] font-semibold uppercase tracking-[0.06em] text-[color:var(--gv-accent-deep)]">
        Note văn hoá ({notes.length})
      </p>
      <ul className="space-y-2">
        {notes.map((note, idx) => (
          <li
            key={`${note.tag}-${idx}`}
            className="flex items-start gap-2 rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] p-3"
          >
            <span
              className="gv-mono inline-flex shrink-0 items-center rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.05em] text-[color:var(--gv-ink-2)]"
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
