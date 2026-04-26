import { memo, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowRight, Play, X } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Btn } from "@/components/v2/Btn";
import type { PatternVideo, TopPattern } from "@/hooks/useTopPatterns";
import { formatViews } from "@/lib/formatters";
import { lifecycleHint } from "./patternLifecycle";

/**
 * Trends — PatternModal (PR-T4).
 *
 * Mirrors the design pack's PatternModal (``screens/trends.jsx`` lines
 * 652-946): full-deck dialog with phone preview + sample switcher on
 * the left and takeaway / structure / gap-angles on the right.
 *
 * **Scope this PR**: the modal shell + the data we already have
 * (videos, sample_hook, instance_count, avg_views, lifecycle).
 * Fields the design renders that aren't yet on the BE schema —
 * ``structure[]``, ``why``, ``careful``, ``angles[]`` — render an
 * "Đang chuẩn bị" stub. A follow-up BE PR can add a
 * ``video_patterns`` migration + Gemini batch synthesis to fill
 * these without touching the FE shell.
 *
 * Accessibility: built on Radix ``Dialog`` (focus trap, ESC, restore
 * focus, scroll lock).
 */

export const PatternModal = memo(function PatternModal({
  pattern,
  open,
  onOpenChange,
}: {
  pattern: TopPattern | null;
  open: boolean;
  onOpenChange: (next: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="!max-w-[920px] gap-0 overflow-hidden border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] p-0"
        onInteractOutside={() => onOpenChange(false)}
      >
        {pattern ? (
          <PatternModalBody pattern={pattern} onClose={() => onOpenChange(false)} />
        ) : null}
      </DialogContent>
    </Dialog>
  );
});

function PatternModalBody({
  pattern,
  onClose,
}: {
  pattern: TopPattern;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const videos = pattern.videos.length > 0 ? pattern.videos : ([] as PatternVideo[]);
  const [activeIdx, setActiveIdx] = useState(0);
  const active = videos[activeIdx] ?? null;
  const lifecycle = lifecycleHint(
    pattern.weekly_instance_count,
    pattern.weekly_instance_count_prev,
  );
  const avgViewsLabel =
    pattern.avg_views != null ? formatViews(pattern.avg_views) : "—";

  return (
    <>
      {/* Header */}
      <header className="flex items-start justify-between gap-4 border-b border-[color:var(--gv-rule)] px-7 py-[18px]">
        <div className="min-w-0 flex-1">
          <p className="gv-mono mb-1.5 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
            PATTERN · {pattern.instance_count} VIDEO · {avgViewsLabel} VIEW TB · {lifecycle.text.toUpperCase()}
          </p>
          <DialogTitle className="gv-tight m-0 text-[28px] font-semibold leading-[1.05] tracking-[-0.02em] text-[color:var(--gv-ink)]">
            {pattern.display_name}
          </DialogTitle>
          {pattern.sample_hook ? (
            <DialogDescription className="mt-1.5 text-[13px] leading-[1.5] text-[color:var(--gv-ink-3)]">
              &ldquo;{pattern.sample_hook}&rdquo;
            </DialogDescription>
          ) : (
            <DialogDescription className="sr-only">
              Pattern detail
            </DialogDescription>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Đóng"
          className="-mr-2 -mt-1 shrink-0 rounded-md p-2 text-[color:var(--gv-ink-3)] transition-colors hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink)]"
        >
          <X className="h-4 w-4" strokeWidth={2} aria-hidden />
        </button>
      </header>

      {/* Body — 2 col on desktop, stacked < 820px */}
      <div className="grid max-h-[80vh] grid-cols-1 overflow-y-auto min-[820px]:grid-cols-[260px_1fr]">
        {/* Left — phone preview + sample switcher */}
        <aside className="border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-5 min-[820px]:border-b-0 min-[820px]:border-r">
          <p className="gv-mono mb-2.5 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
            VIDEO MẪU
          </p>
          <PhoneTile video={active} />
          <Btn
            variant="ghost"
            size="md"
            type="button"
            className="mt-3.5 w-full justify-center"
            disabled={!active?.video_id}
            onClick={() => {
              if (active?.video_id) {
                navigate(`/app/video?video_id=${encodeURIComponent(active.video_id)}`);
              }
            }}
          >
            Mổ video này → Tại sao nổ
            <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
          </Btn>
          {videos.length > 1 ? (
            <>
              <p className="gv-mono mt-4 mb-2 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
                CHUYỂN VIDEO ({activeIdx + 1}/{videos.length})
              </p>
              <div className="grid grid-cols-4 gap-1.5">
                {videos.map((v, i) => {
                  const isActive = i === activeIdx;
                  return (
                    <button
                      key={v.video_id || i}
                      type="button"
                      onClick={() => setActiveIdx(i)}
                      aria-label={`Mẫu ${i + 1}`}
                      aria-pressed={isActive}
                      className={
                        "relative overflow-hidden rounded-[4px] " +
                        (isActive
                          ? "ring-2 ring-[color:var(--gv-ink)] ring-offset-1 ring-offset-[color:var(--gv-paper)]"
                          : "border border-[color:var(--gv-rule)]")
                      }
                      style={{ aspectRatio: "9 / 16" }}
                    >
                      {v.thumbnail_url ? (
                        <img
                          src={v.thumbnail_url}
                          alt=""
                          loading="lazy"
                          className="absolute inset-0 h-full w-full object-cover"
                        />
                      ) : (
                        <div className="absolute inset-0 bg-[color:var(--gv-canvas-2)]" />
                      )}
                      <span
                        className="absolute inset-0"
                        style={{
                          background: "linear-gradient(180deg, transparent 50%, rgba(0,0,0,0.6))",
                        }}
                        aria-hidden
                      />
                      <span className="gv-mono absolute bottom-0.5 left-0 right-0 truncate px-1 text-center text-[7.5px] text-white">
                        ↑{formatViews(v.views)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </>
          ) : null}
        </aside>

        {/* Right — takeaway / structure / angles */}
        <section className="flex flex-col gap-5 px-7 py-6">
          <Takeaway hookSample={pattern.sample_hook} />
          <StructureBlock />
          <GapAnglesBlock />
        </section>
      </div>
    </>
  );
}

function PhoneTile({ video }: { video: PatternVideo | null }) {
  if (!video) {
    return (
      <div
        className="relative overflow-hidden rounded-[10px] bg-[color:var(--gv-canvas-2)]"
        style={{ aspectRatio: "9 / 16", boxShadow: "0 6px 22px rgba(0,0,0,0.18)" }}
      >
        <div className="flex h-full w-full items-center justify-center text-[12px] text-[color:var(--gv-ink-4)]">
          Chưa có video mẫu
        </div>
      </div>
    );
  }
  return (
    <div
      className="relative overflow-hidden rounded-[10px] bg-[color:var(--gv-canvas-2)]"
      style={{ aspectRatio: "9 / 16", boxShadow: "0 6px 22px rgba(0,0,0,0.18)" }}
    >
      {video.thumbnail_url ? (
        <img
          src={video.thumbnail_url}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : null}
      <span
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.25), transparent 30%, transparent 70%, rgba(0,0,0,0.75))",
        }}
        aria-hidden
      />
      {/* Top — handle */}
      <span className="gv-mono absolute left-3 right-3 top-3 text-[10px] text-white opacity-90">
        {video.creator_handle
          ? video.creator_handle.startsWith("@")
            ? video.creator_handle
            : `@${video.creator_handle}`
          : ""}
      </span>
      {/* Center — play glyph */}
      <span
        className="absolute left-1/2 top-1/2 flex h-12 w-12 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white/90"
        aria-hidden
      >
        <Play className="h-4 w-4 text-[color:var(--gv-ink)]" fill="currentColor" />
      </span>
      {/* Bottom — view count */}
      <span className="gv-mono absolute bottom-3 left-3 right-3 text-[10px] text-white opacity-90">
        ↑ {formatViews(video.views)}
      </span>
    </div>
  );
}

function Takeaway({ hookSample }: { hookSample: string | null }) {
  return (
    <div
      className="rounded-md border-l-[3px] border-[color:var(--gv-accent)] bg-[color:var(--gv-paper)] px-4 py-3.5"
    >
      <p className="gv-mono mb-1.5 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-accent-deep)]">
        Ý CHÍNH
      </p>
      <p className="m-0 text-[13px] leading-[1.55] text-[color:var(--gv-ink)]" style={{ textWrap: "pretty" }}>
        {hookSample
          ? `Pattern này đang chạy mạnh trong ngách. Hook tiêu biểu: "${hookSample}".`
          : "Pattern này đang chạy mạnh trong ngách của bạn."}{" "}
        <span className="text-[color:var(--gv-ink-3)]">
          Cấu trúc chi tiết và góc còn trống đang được biên tập — sẽ có trong vài ngày tới.
        </span>
      </p>
    </div>
  );
}

function StructureBlock() {
  return (
    <div>
      <p className="gv-mono mb-2 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
        CẤU TRÚC ĐIỂN HÌNH
      </p>
      <p className="m-0 rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3 text-[12.5px] leading-[1.5] text-[color:var(--gv-ink-3)]">
        Đang chuẩn bị — biên tập đang tổng hợp 4 bước Hook / Setup / Body / Payoff cho pattern này.
      </p>
    </div>
  );
}

function GapAnglesBlock() {
  return (
    <div>
      <p className="gv-mono mb-2 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
        GÓC CÒN TRỐNG
      </p>
      <p className="m-0 rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3 text-[12.5px] leading-[1.5] text-[color:var(--gv-ink-3)]">
        Đang chuẩn bị — danh sách các góc nội dung chưa creator nào khai thác sẽ xuất hiện ở đây.
      </p>
    </div>
  );
}
