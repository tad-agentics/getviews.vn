/**
 * D6b (2026-06-06) — Kho Douyin · shared formatters.
 *
 * Canonical duration / relative-time / rise / freshness helpers for
 * VideoCard, VideoModal, and PatternCard surfaces.
 */

import type { DouyinVideo } from "@/lib/api-types";

/** Text shown in the card's centered Sub VN band (matches ``DouyinVideoCard``). */
export function douyinCardSubText(video: DouyinVideo): string {
  return (video.sub_vi || video.title_vi || video.title_zh || "").trim();
}

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
 *  / non-positive. */
export function formatRisePct(pct: number | null): string | null {
  if (pct == null || !Number.isFinite(pct) || pct <= 0) return null;
  return `+${Math.round(pct)}%`;
}

/**
 * "CẬP NHẬT N NGÀY TRƯỚC" / "CẬP NHẬT HÔM QUA" / "VỪA CẬP NHẬT" from
 * an ISO timestamp. ``null`` when the input is missing or unparseable.
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
