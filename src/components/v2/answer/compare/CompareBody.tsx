/**
 * Wave 4 PR #3 — Compare flow body.
 *
 * Renders the ``ComparePayload`` from /stream as a side-by-side video
 * diagnosis with a brutalist delta bar pinned at the top.
 *
 * Layout:
 *   - ``min-[900px]:`` two-column grid (side panels share width).
 *   - below 900px: stacked, with sticky "A" / "B" labels at the top of
 *     each panel so the user always knows which video they're scrolled
 *     into.
 *
 * Per-side rendering is deliberately minimal — creator chip + niche +
 * key analysis numbers + the diagnosis prose. We do NOT reuse
 * ``DiagnosticBody`` because that component is bound to the URL-less
 * 5-category ``DiagnosticReportPayload`` shape; compare carries
 * URL-bearing run_video_diagnosis dicts which have no overlap.
 *
 * The delta bar is the load-bearing surface — that's the "what's
 * different" insight the creator paid for. Numeric chips (breakout
 * gap, scene-count diff, hook alignment) live next to the verdict so
 * the prose has receipts.
 */

import type {
  CompareDelta,
  CompareHigherSide,
  CompareHookAlignment,
  ComparePayload,
  VideoDiagnosisStreamSide,
} from "@/lib/api-types";

// ── Vietnamese labels (deterministic) ────────────────────────────────

const HIGHER_LABEL_VN: Record<CompareHigherSide, string> = {
  left: "Video trái mạnh hơn",
  right: "Video phải mạnh hơn",
  tie: "Tương đương",
  unknown: "Chưa đủ data",
};

const HOOK_LABEL_VN: Record<CompareHookAlignment, string> = {
  match: "Cùng kiểu hook",
  conflict: "Hook khác kiểu",
  unknown: "Chưa rõ hook",
};

// ── Side label header ────────────────────────────────────────────────

function SideHeader({
  letter,
  side,
}: {
  letter: "A" | "B";
  side: VideoDiagnosisStreamSide;
}) {
  const handle = side.metadata?.author?.username ?? "";
  return (
    <header
      // ``sticky top-0`` only kicks in below the 900px breakpoint where
      // the panels stack vertically — at >= 900px the columns sit
      // side-by-side and the labels naturally stay in view.
      className="sticky top-0 z-10 -mx-4 mb-3 flex items-center gap-2 border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]/95 px-4 py-2.5 backdrop-blur min-[900px]:static min-[900px]:mx-0 min-[900px]:rounded-none min-[900px]:bg-transparent min-[900px]:px-0 min-[900px]:py-0 min-[900px]:backdrop-blur-none"
    >
      <span
        className="gv-mono inline-flex h-6 w-6 items-center justify-center rounded-full border-2 border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] text-[10px] font-bold text-[color:var(--gv-ink)]"
        aria-label={`Video ${letter}`}
      >
        {letter}
      </span>
      {handle ? (
        <span className="gv-mono text-[12px] text-[color:var(--gv-ink-3)]">
          @{handle.replace(/^@/, "")}
        </span>
      ) : null}
    </header>
  );
}

// ── Per-side video stat chips ────────────────────────────────────────

function StatChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2.5 py-1.5">
      <div className="gv-mono gv-uc text-[9px] tracking-[0.16em] text-[color:var(--gv-ink-4)]">
        {label}
      </div>
      <div className="gv-mono mt-0.5 text-[13px] font-semibold text-[color:var(--gv-ink)]">
        {value}
      </div>
    </div>
  );
}

function _formatNum(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("vi-VN").format(Math.round(n));
}

function VideoSidePanel({
  letter,
  side,
}: {
  letter: "A" | "B";
  side: VideoDiagnosisStreamSide;
}) {
  const meta = side.metadata ?? {};
  const analysis = side.analysis ?? {};
  const views = meta.metrics?.views ?? null;
  const breakout = meta.breakout ?? meta.breakout_multiplier ?? null;
  // Empty scenes array → null (matches BE _stats semantics: an
  // unanalysed video shouldn't render as "0 scenes" — that's a
  // valid number that misrepresents missing data).
  const sceneCount = analysis.scenes?.length || null;
  const hookType = analysis.hook_analysis?.hook_type ?? null;
  const diagnosis = side.diagnosis ?? "";

  return (
    <article className="flex flex-col rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
      <SideHeader letter={letter} side={side} />

      <div className="grid grid-cols-2 gap-2">
        <StatChip label="Views" value={_formatNum(views)} />
        <StatChip
          label="Breakout"
          value={breakout != null ? `${breakout.toFixed(2)}x` : "—"}
        />
        <StatChip label="Scene" value={sceneCount != null ? String(sceneCount) : "—"} />
        <StatChip label="Hook" value={hookType ?? "—"} />
      </div>

      {diagnosis ? (
        <div className="gv-serif mt-4 whitespace-pre-line text-[14px] leading-[1.5] text-[color:var(--gv-ink)]">
          {diagnosis}
        </div>
      ) : null}
    </article>
  );
}

// ── Delta bar (the headline surface) ─────────────────────────────────

function DeltaBar({ delta }: { delta: CompareDelta }) {
  const breakoutGap = delta.breakout_gap;
  const sceneDiff = delta.scene_count_diff;

  return (
    <section
      className="gv-surface-brutal gv-surface-brutal--compact mb-6 p-4"
      data-testid="compare-delta-bar"
    >
      <div className="gv-mono gv-uc mb-1.5 text-[10px] tracking-[0.16em] text-[color:var(--gv-ink-4)]">
        Khác biệt chính
      </div>
      <p className="gv-serif text-[16px] leading-[1.45] text-[color:var(--gv-ink)]">
        {delta.verdict}
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        <DeltaChip label={HIGHER_LABEL_VN[delta.higher_breakout_side]} />
        <DeltaChip label={HOOK_LABEL_VN[delta.hook_alignment]} />
        {breakoutGap != null && delta.higher_breakout_side !== "unknown" ? (
          <DeltaChip
            label={`Δ breakout ${breakoutGap > 0 ? "+" : ""}${breakoutGap.toFixed(2)}x`}
          />
        ) : null}
        {sceneDiff != null ? (
          <DeltaChip
            label={`Δ scene ${sceneDiff > 0 ? "+" : ""}${sceneDiff}`}
          />
        ) : null}
      </div>

      {delta.verdict_fallback ? (
        <p
          className="gv-mono mt-2 text-[10px] text-[color:var(--gv-ink-4)]"
          data-testid="compare-delta-fallback"
        >
          (tổng hợp tự động — chưa qua mô hình)
        </p>
      ) : null}
    </section>
  );
}

function DeltaChip({ label }: { label: string }) {
  return (
    <span className="gv-mono inline-flex items-center rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2.5 py-1 text-[11px] text-[color:var(--gv-ink-2)]">
      {label}
    </span>
  );
}

// ── Main body ────────────────────────────────────────────────────────

export function CompareBody({ payload }: { payload: ComparePayload }) {
  return (
    <div className="text-sm text-[color:var(--gv-ink-2)]">
      <DeltaBar delta={payload.delta} />

      <div className="grid grid-cols-1 gap-4 min-[900px]:grid-cols-2">
        <VideoSidePanel letter="A" side={payload.left} />
        <VideoSidePanel letter="B" side={payload.right} />
      </div>
    </div>
  );
}
