import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import type { StepEvent } from "@/lib/types/sse-events";
import {
  VIDEO_PIPELINE_ANALYSIS_HARD_TIMEOUT_MS,
  VIDEO_PIPELINE_SLOW_HINT_MS,
} from "@/lib/videoPipelineTimeouts";

const STEPS = ["Quét", "Phân tích", "Tìm pattern", "Tóm tắt"] as const;

/** Four-step research narrative (Phase C.1.3). */
export function ResearchStepStrip({
  stage,
  done = false,
}: {
  /** 0–3 current highlight while loading; `done` styles all steps complete. */
  stage: number;
  done?: boolean;
}) {
  const activeIndex = done ? STEPS.length : Math.min(Math.max(stage, 0), STEPS.length - 1);
  return (
    <ol className="mt-4 flex flex-wrap gap-2" aria-label="Tiến trình nghiên cứu">
      {STEPS.map((label, i) => {
        const isDone = done || i < activeIndex;
        const isActive = !done && i === activeIndex;
        return (
          <li
            key={label}
            className={`rounded-full border px-2.5 py-1 gv-kicker transition-colors ${
              isDone
                ? "border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-ink)]"
                : isActive
                  ? "border-[color:var(--gv-accent)] bg-[var(--gv-canvas-2)] text-[color:var(--gv-ink)]"
                  : "border-[var(--gv-rule)] text-[var(--gv-ink-4)]"
            }`}
          >
            {label}
          </li>
        );
      })}
    </ol>
  );
}

/**
 * Thanh tiến trình ngang theo reference báo cáo — copy chi tiết + pill hoàn tất.
 */
export function ResearchProcessBar({
  loading,
  stage,
  done,
  videoCount,
  channelCount,
}: {
  loading: boolean;
  stage: number;
  done: boolean;
  videoCount?: number | null;
  channelCount?: number | null;
}) {
  const step = Math.min(Math.max(stage, 0), 3);
  const fmt = (n: number | null | undefined) =>
    n != null && n > 0 ? n.toLocaleString("vi-VN") : null;
  const v = fmt(videoCount);
  const c = fmt(channelCount);

  const labels = [
    v ? `Quét ${v} video` : "Quét video",
    c ? `Phân tích ${c} kênh top` : "Phân tích kênh top",
    "Tìm pattern chung",
    "Viết tóm tắt",
  ] as const;

  return (
    <div
      className="mt-5 flex flex-col gap-3 border-y border-[color:var(--gv-rule)] py-4 min-[700px]:flex-row min-[700px]:items-center min-[700px]:justify-between"
      aria-label="Tiến trình nghiên cứu"
    >
      <ol className="flex min-w-0 flex-1 flex-wrap items-center gap-x-1 gap-y-2 text-sm leading-snug text-[color:var(--gv-ink-2)]">
        {labels.map((label, i) => {
          const isDone = done;
          const isActive = !done && loading && i === step;
          return (
            <li key={label} className="flex items-center gap-1">
              {i > 0 ? (
                <span className="mx-1 text-[color:var(--gv-ink-4)]" aria-hidden>
                  ·
                </span>
              ) : null}
              <span
                className={`inline-flex items-center gap-1 ${
                  isDone
                    ? "font-medium text-[color:var(--gv-ink)]"
                    : isActive
                      ? "font-medium text-[color:var(--gv-accent)]"
                      : "text-[color:var(--gv-ink-3)]"
                }`}
              >
                {isDone ? (
                  <Check className="h-3.5 w-3.5 shrink-0 text-[color:var(--gv-pos)]" strokeWidth={2.5} aria-hidden />
                ) : null}
                {label}
              </span>
            </li>
          );
        })}
      </ol>
      {done && !loading ? (
        <p className="shrink-0 rounded-full bg-[color:var(--gv-pos)] px-3 py-1 gv-kicker text-white">
          Hoàn tất
        </p>
      ) : loading ? (
        <p className="shrink-0 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 gv-kicker text-[color:var(--gv-ink-3)]">
          Đang chạy…
        </p>
      ) : null}
    </div>
  );
}

/** Cycles stages 0→3 while `active`; resets when inactive. */
export function useResearchStage(active: boolean): number {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    if (!active) {
      setStage(0);
      return;
    }
    const id = window.setInterval(() => {
      setStage((s) => (s >= 3 ? 0 : s + 1));
    }, 450);
    return () => window.clearInterval(id);
  }, [active]);
  return active ? stage : 0;
}

export function ProgressPill({
  loading,
  stepIndex,
  total = 4,
}: {
  loading: boolean;
  stepIndex: number;
  total?: number;
}) {
  if (!loading) return null;
  const n = Math.min(stepIndex + 1, total);
  return (
    <span className="inline-flex items-center rounded-full border border-[var(--gv-rule)] bg-[var(--gv-canvas-2)] px-2 py-0.5 gv-kicker text-[var(--gv-ink-3)]">
      Đang nghiên cứu… {n}/{total}
    </span>
  );
}

// ── Tool card state ──────────────────────────────────────────────────────────
// Keyed by `${iteration}-${index}` for parallel card tracking.

interface ToolCardState {
  key: string;
  label: string;
  tool: string;
  done: boolean;
  found: number;
  thumbnails: string[];
  /** Awemes returned by upstream but discarded by the tool (e.g.,
   *  blocklist). Audit Pass-2 fix #6 — surfaces the gap between
   *  "search returned nothing" and "search returned only filtered
   *  results". */
  filtered?: number;
}

// ── ThumbnailStrip ────────────────────────────────────────────────────────────

function ThumbnailStrip({ urls }: { urls: string[] }) {
  if (!urls.length) return null;
  return (
    <div className="mt-1.5 flex items-center gap-1 overflow-x-auto">
      {urls.slice(0, 5).map((url, i) => (
        <img
          key={i}
          src={url}
          alt=""
          className="h-7 w-7 shrink-0 rounded-full border border-[var(--gv-rule)] bg-[var(--gv-canvas-2)] object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      ))}
    </div>
  );
}

// ── SourceBadge ───────────────────────────────────────────────────────────────

function SourceBadge({ tool }: { tool: string }) {
  const isTiktok = tool === "tiktok_live";
  return (
    <span
      className={`shrink-0 rounded-full px-1.5 py-0.5 gv-kicker ${
        isTiktok
          ? "bg-[color:var(--gv-ink)] text-white"
          : "border border-[var(--gv-rule)] bg-[var(--gv-canvas-2)] text-[var(--gv-ink-3)]"
      }`}
    >
      {isTiktok ? "TikTok Live" : tool === "corpus" ? "Kho video" : tool === "synthesis" ? "Phân tích" : tool === "creator_posts" ? "TikTok" : tool}
    </span>
  );
}

// ── ToolCard ─────────────────────────────────────────────────────────────────

function ToolCard({ card }: { card: ToolCardState }) {
  return (
    <div className="flex flex-col gap-0.5 border-b border-[var(--gv-rule)] py-2 last:border-0">
      <div className="flex min-w-0 items-center gap-2">
        {card.done ? (
          <span className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full bg-[var(--gv-pos)]">
            <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
              <path d="M1.5 4L3 5.5L6.5 2" stroke="white" strokeWidth="1.2" strokeLinecap="round" />
            </svg>
          </span>
        ) : (
          <span className="h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-[var(--gv-accent)] border-t-transparent" />
        )}
        <span className="truncate text-[12px] text-[var(--gv-ink-2)]">{card.label}</span>
        <SourceBadge tool={card.tool} />
        {card.done && card.found > 0 && (
          <span className="ml-auto shrink-0 gv-kicker text-[var(--gv-ink-3)]">
            {card.found.toLocaleString("vi-VN")} video
            {card.filtered && card.filtered > 0
              ? ` · lọc ${card.filtered.toLocaleString("vi-VN")}`
              : ""}
          </span>
        )}
        {card.done && card.found === 0 && card.filtered && card.filtered > 0 && (
          <span className="ml-auto shrink-0 gv-kicker text-[var(--gv-ink-4)]">
            {card.filtered.toLocaleString("vi-VN")} bị lọc (kênh tin tức)
          </span>
        )}
      </div>
      {card.done && card.thumbnails.length > 0 && (
        <ThumbnailStrip urls={card.thumbnails} />
      )}
    </div>
  );
}

// ── StatusRow ────────────────────────────────────────────────────────────────

function StatusRow({ text, iteration }: { text: string; iteration: number }) {
  return (
    <div className="flex items-center gap-2 pb-1 pt-3 first:pt-0">
      <span className="shrink-0 gv-kicker text-[var(--gv-ink-4)]">
        {iteration}
      </span>
      <span className="text-[11px] font-medium gv-kicker tracking-wide text-[var(--gv-ink)]">
        {text}
      </span>
    </div>
  );
}

// ── Cache-hit detection ───────────────────────────────────────────────────────

const CACHE_HIT_LABEL = "Đang đọc kết quả phân tích đã lưu...";

/**
 * Phase 5.7.1 — returns true when the step stream matches the single-step
 * cache-hit pattern emitted by the BE (_try_on_demand_cache_hit).
 *
 * Pattern: exactly one step event, type=step_process, label matching the
 * Vietnamese cache-hit string.  Any additional step events (e.g., a slow
 * hint or error) disqualify the pattern — treat as a normal stream.
 */
export function isCacheHitPattern(steps: StepEvent[]): boolean {
  if (steps.length !== 1) return false;
  const only = steps[0];
  return only.type === "step_process" && only.label === CACHE_HIT_LABEL;
}

/**
 * Phase 5.7.2 — cache-hit badge shown instead of LivePipelineStrip.
 *
 * Shows "Đã phân tích trước" with a computed_at timestamp when present.
 * Accepts an optional `computedAt` ISO string from the cached response
 * payload (report.computed_at or meta.computed_at).
 */
export function CacheHitBadge({
  computedAt,
}: {
  computedAt?: string | null;
}) {
  const timeStr = (() => {
    if (!computedAt) return null;
    try {
      const d = new Date(computedAt);
      if (Number.isNaN(d.getTime())) return null;
      return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
    } catch {
      return null;
    }
  })();

  return (
    <p className="mt-3 gv-mono inline-flex items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-3 py-1 text-[11px] text-[color:var(--gv-ink-3)]">
      <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--gv-pos)]" aria-hidden />
      Đã phân tích trước
      {timeStr ? <> · cập nhật lúc {timeStr}</> : null}
    </p>
  );
}

// ── LivePipelineStrip ─────────────────────────────────────────────────────────

/**
 * Renders real-time pipeline events as parallel tool cards.
 *
 * Replaces timer-based ResearchProcessBar for answer sessions that
 * emit step events. Matches Lightreel's pipeline transparency UX:
 * - Status header per iteration
 * - Tool cards with spinner → found count + thumbnail strip
 * - Multiple cards per iteration complete out of order
 *
 * Falls back to ResearchProcessBar when steps array is empty (legacy
 * builders not yet updated to emit step events).
 *
 * Phase 5.7.1 — short-circuits to null when cache-hit pattern detected.
 */
export function LivePipelineStrip({
  steps,
  done,
  loading,
  stage,
  videoCount,
  channelCount,
  heartbeatElapsedSec,
}: {
  steps: StepEvent[];
  done: boolean;
  loading: boolean;
  stage?: number;
  videoCount?: number | null;
  channelCount?: number | null;
  /** Seconds elapsed since last real step event, derived from backend heartbeat pings. */
  heartbeatElapsedSec?: number;
}) {
  const [slowWarning, setSlowWarning] = useState(false);
  const [clientTimedOut, setClientTimedOut] = useState(false);

  useEffect(() => {
    if (!loading || done) {
      setSlowWarning(false);
      setClientTimedOut(false);
      return;
    }
    const t1 = window.setTimeout(() => setSlowWarning(true), VIDEO_PIPELINE_SLOW_HINT_MS);
    const t2 = window.setTimeout(() => setClientTimedOut(true), VIDEO_PIPELINE_ANALYSIS_HARD_TIMEOUT_MS);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, [loading, done]);

  const longWaitHints =
    loading && !done ? (
      <>
        {slowWarning && !clientTimedOut ? (
          <p className="mt-2 text-sm leading-snug text-[color:var(--gv-ink-3)]">
            Video này cần thêm thời gian phân tích. Vui lòng chờ hoặc thử lại sau 2 phút.
          </p>
        ) : null}
        {clientTimedOut ? (
          <p className="mt-2 text-sm leading-snug text-[color:var(--gv-accent)]">
            Phân tích mất quá lâu.{" "}
            <button
              type="button"
              className="font-medium underline decoration-dotted underline-offset-2"
              onClick={() => window.location.reload()}
            >
              Tải lại trang
            </button>{" "}
            hoặc dán link khác.
          </p>
        ) : null}
      </>
    ) : null;

  // Phase 5.7.1 — single-step cache-hit: suppress the 4-stage strip entirely.
  // The CacheHitBadge is rendered by the caller (AnswerScreen) alongside the result.
  if (isCacheHitPattern(steps)) return null;

  if (steps.length === 0 && loading) {
    return (
      <>
        <ResearchProcessBar
          loading={loading}
          stage={stage ?? 0}
          done={done}
          videoCount={videoCount}
          channelCount={channelCount}
        />
        {longWaitHints}
      </>
    );
  }

  if (steps.length === 0 && done) return null;

  const cardMap = new Map<string, ToolCardState>();
  const statusByIteration = new Map<number, string>();
  const iterationOrder: number[] = [];

  // Audit fix #3: also surface ``step_error`` (red banner) and the
  // legacy sequential events (``step_start``/``step_search``/
  // ``step_count``/``step_process``/``step_done``) the chat-mode
  // pipelines emit. Without these branches the strip shows a spinner
  // until the outer ``done:true`` token, dropping the Vietnamese
  // error message and leaving chat-path users with an empty strip.
  // Audit Pass-2 fix #3 — collect ALL step_error events and render the
  // FIRST one (root cause). live_search.py emits one per failed term
  // (up to 3 in a row); the previous single-slot capture overwrote
  // earlier, more-diagnostic errors with the last one in the stream.
  const errorEvents: import("@/lib/types/sse-events").StepError[] = [];
  const legacyLines: string[] = [];

  for (const event of steps) {
    if (event.type === "step_status") {
      statusByIteration.set(event.iteration, event.text);
      if (!iterationOrder.includes(event.iteration)) {
        iterationOrder.push(event.iteration);
      }
    } else if (event.type === "step_tool_start") {
      const key = `${event.iteration}-${event.index}`;
      cardMap.set(key, {
        key,
        label: event.label,
        tool: event.tool,
        done: false,
        found: 0,
        thumbnails: [],
      });
      if (!iterationOrder.includes(event.iteration)) {
        iterationOrder.push(event.iteration);
      }
    } else if (event.type === "step_tool_complete") {
      const key = `${event.iteration}-${event.index}`;
      const existing = cardMap.get(key);
      if (existing) {
        cardMap.set(key, {
          ...existing,
          done: true,
          found: event.found,
          thumbnails: event.thumbnails,
          filtered: event.filtered,
        });
      }
    } else if (event.type === "step_error") {
      errorEvents.push(event);
    } else if (event.type === "step_start" || event.type === "step_process") {
      legacyLines.push(event.label);
    } else if (event.type === "step_search") {
      legacyLines.push(`Tìm kiếm ${event.source}: "${event.query}"`);
    } else if (event.type === "step_creator") {
      legacyLines.push(`Phân tích kênh @${event.handle}`);
    } else if (event.type === "step_count") {
      legacyLines.push(`Đã tìm ${event.count} mẫu`);
    } else if (event.type === "step_done") {
      legacyLines.push(event.summary);
    }
  }

  const cardsByIteration = new Map<number, ToolCardState[]>();
  for (const [, card] of cardMap) {
    const iter = Number.parseInt(card.key.split("-")[0] ?? "0", 10);
    const arr = cardsByIteration.get(iter) ?? [];
    arr.push(card);
    cardsByIteration.set(iter, arr);
  }

  return (
    <div className="mt-5 border-y border-[var(--gv-rule)] py-4">
      {iterationOrder.map((iter) => (
        <div key={iter}>
          {statusByIteration.has(iter) && (
            <StatusRow text={statusByIteration.get(iter)!} iteration={iter} />
          )}
          <div className="pl-5">
            {(cardsByIteration.get(iter) ?? [])
              .sort(
                (a, b) =>
                  Number.parseInt(a.key.split("-")[1] ?? "0", 10) -
                  Number.parseInt(b.key.split("-")[1] ?? "0", 10),
              )
              .map((card) => (
                <ToolCard key={card.key} card={card} />
              ))}
          </div>
        </div>
      ))}

      {/* Legacy sequential events (chat-mode pipelines.py emitters).
          Audit Pass-2 fix #2 — render alongside iteration cards, not
          gated on `iterationOrder.length === 0`. Some pipelines emit
          BOTH step_status (parallel) AND step_done (legacy summary
          like "Xong — đang hiển thị kết quả"); the previous gate
          silently dropped the summary on every video diagnosis +
          diagnostic answer. */}
      {legacyLines.length > 0 && (
        <ul
          className={
            "space-y-1.5 pl-5 text-xs leading-snug text-[var(--gv-ink-3)] " +
            (iterationOrder.length > 0 ? "mt-3" : "")
          }
        >
          {legacyLines.map((line, i) => (
            <li key={`${i}-${line.slice(0, 24)}`} className="flex items-start gap-2">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-[var(--gv-ink-4)]" />
              <span>{line}</span>
            </li>
          ))}
        </ul>
      )}

      {/* step_error — surface the Vietnamese message_vi (root cause:
          first error in the stream) so the user sees a concrete
          failure instead of a never-resolving spinner. */}
      {errorEvents.length > 0 && (
        <div
          role="alert"
          className="mt-2 flex items-start gap-2 rounded-md border border-[color:var(--gv-neg)]/40 bg-[color:var(--gv-neg)]/8 px-3 py-2 text-xs text-[color:var(--gv-neg-deep)]"
        >
          <span aria-hidden className="font-mono">✕</span>
          <div className="flex flex-col gap-0.5">
            <span className="font-medium">{errorEvents[0]!.message_vi}</span>
            <span className="gv-kicker opacity-70">
              {errorEvents[0]!.code}
              {errorEvents.length > 1 ? ` · +${errorEvents.length - 1} thêm` : ""}
            </span>
          </div>
        </div>
      )}

      {loading && !done && errorEvents.length === 0 && steps.some((s) => s.type === "step_tool_complete") && (
        <div className="flex items-center gap-2 pt-2 text-[11px] text-[var(--gv-ink-3)]">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--gv-accent)]" />
          Đang tổng hợp báo cáo…
        </div>
      )}

      {loading && !done && errorEvents.length === 0 && heartbeatElapsedSec && heartbeatElapsedSec > 0 ? (
        <div className="mt-2 flex items-center gap-1.5 gv-kicker text-[var(--gv-ink-4)]">
          <span className="h-1 w-1 animate-pulse rounded-full bg-[var(--gv-ink-4)]" />
          Vẫn đang xử lý · {heartbeatElapsedSec}s…
        </div>
      ) : null}

      {done && errorEvents.length === 0 && (
        <div className="mt-2 flex items-center gap-1.5 text-[11px] font-medium text-[var(--gv-pos)]">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <circle cx="6" cy="6" r="5" fill="currentColor" opacity="0.15" />
            <path d="M3.5 6L5 7.5L8.5 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          </svg>
          Hoàn tất
        </div>
      )}

      {longWaitHints}
    </div>
  );
}
