/**
 * D6b (2026-06-06) — Kho Douyin · shared formatters + adapt-meta map.
 *
 * Pre-D6 these functions were duplicated across DouyinVideoCard /
 * DouyinVideoModal / DouyinPatternCard with subtly different names
 * (``formatRisePct`` / ``formatRiseFromCnPct`` / ``_formatRiseFromCnPct``)
 * and identical bodies. Audit finding H4 — drift risk. Consolidating
 * here keeps one canonical implementation per format.
 */

import type { DouyinAdaptLevel } from "@/lib/api-types";

// ── Adapt-level meta ────────────────────────────────────────────────


export type DouyinAdaptMeta = {
  label: string;
  short: string;
  /** Tailwind className tail with var(--gv-*) tokens. */
  toneClass: string;
};

export const ADAPT_META: Record<DouyinAdaptLevel, DouyinAdaptMeta> = {
  green: {
    label: "Dịch thẳng",
    short: "XANH",
    toneClass:
      "border-[color:var(--gv-pos-deep)] bg-[color:var(--gv-pos-soft)] text-[color:var(--gv-pos-deep)]",
  },
  yellow: {
    label: "Cần đổi bối cảnh",
    short: "VÀNG",
    toneClass:
      "border-[color:var(--gv-warn)] bg-[color:var(--gv-warn-soft)] text-[color:var(--gv-warn)]",
  },
  red: {
    label: "Khó dịch",
    short: "ĐỎ",
    toneClass:
      "border-[color:var(--gv-accent-deep)] bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]",
  },
};

/** Synth-pending (NULL adapt_level) — neutral tone. Reused by card,
 *  modal, and any future pattern-card surface. */
export const PENDING_ADAPT_META: DouyinAdaptMeta = {
  label: "Đang chờ duyệt",
  short: "CHỜ",
  toneClass:
    "border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]",
};

/**
 * Douyin "Sub VN" caption-on-video green. The GV palette pivoted to
 * magenta+sky with no green-on-dark token; this localized constant
 * keeps the hex out of inline ``style={{}}`` calls and gives one place
 * to swap if the brand ever adds a green tone. Used by VideoCard +
 * VideoModal sub-bands and the small "Sub VN" label above them.
 */
export const DOUYIN_SUB_VN_GREEN = "#7CD9A3";


// ── Formatters ──────────────────────────────────────────────────────


/** ``mm:ss`` from a fractional seconds duration. ``null`` for missing
 *  / invalid / zero-or-negative input. */
export function formatDuration(durationSec: number | null): string | null {
  if (durationSec == null || !Number.isFinite(durationSec) || durationSec <= 0) {
    return null;
  }
  const total = Math.round(durationSec);
  const mm = Math.floor(total / 60);
  const ss = total % 60;
  return `${mm}:${ss.toString().padStart(2, "0")}`;
}

/** Vietnamese relative-time chip ("Hôm nay" / "3 ngày trước" / etc.).
 *  ``null`` for missing / invalid ISO. */
export function formatRelativeIso(iso: string | null): string | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  const days = Math.floor((Date.now() - t) / 86_400_000);
  if (days <= 0) return "Hôm nay";
  if (days === 1) return "Hôm qua";
  if (days < 7) return `${days} ngày trước`;
  if (days < 30) return `${Math.floor(days / 7)} tuần trước`;
  return `${Math.floor(days / 30)} tháng trước`;
}

/** ``+NN%`` rise chip from cn_rise_pct. ``null`` when null / non-finite
 *  / non-positive (cn_rise_pct is an absolute % growth, always >= 0
 *  in practice — see audit N1). */
export function formatRisePct(pct: number | null): string | null {
  if (pct == null || !Number.isFinite(pct) || pct <= 0) return null;
  return `+${Math.round(pct)}%`;
}

/** Engagement-rate display: ``12.5%`` or ``—``. BE stores 0..100. */
export function formatEngagementPct(er: number | null): string {
  if (er == null || !Number.isFinite(er)) return "—";
  return `${er.toFixed(1)}%`;
}

/** ``2 tuần`` / ``2–4 tuần`` / ``null`` from the eta range. */
export function formatEtaWeeks(
  min: number | null,
  max: number | null,
): string | null {
  if (min == null && max == null) return null;
  if (min != null && max != null) {
    if (min === max) return `${min} tuần`;
    return `${min}–${max} tuần`;
  }
  return `${min ?? max} tuần`;
}

/**
 * "CẬP NHẬT N NGÀY TRƯỚC" / "CẬP NHẬT HÔM QUA" / "VỪA CẬP NHẬT" from
 * an ISO timestamp. Used for the §I freshness chip per design pack
 * ``screens/douyin.jsx`` line 588. ``null`` when the input is missing
 * or unparseable so the caller can hide the chip.
 */
export function formatFreshnessVN(iso: string | null): string | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  const days = Math.floor((Date.now() - t) / 86_400_000);
  if (days <= 0) return "VỪA CẬP NHẬT";
  if (days === 1) return "CẬP NHẬT HÔM QUA";
  return `CẬP NHẬT ${days} NGÀY TRƯỚC`;
}
