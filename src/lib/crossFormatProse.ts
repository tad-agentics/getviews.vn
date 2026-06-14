import type { CrossFormatSignal } from "@/lib/api-types";

/** Deterministic cross-format strip prose when BE signal is present (claim-tier gated upstream). */
export function buildCrossFormatStripProse(signal: CrossFormatSignal): string {
  const n = signal.niches_with_format;
  const label = signal.format_label_vi?.trim() || signal.format_axis;
  const top = signal.top_hooks?.[0];
  const hookPart = top
    ? ` Hook mạnh nhất trong mẫu: ${top.hook_type_vi || top.hook_type} (TB ~${Math.round(top.avg_views / 1000)}K view, lan ${top.niche_spread} ngách).`
    : "";
  return `Format «${label}» đang chạy ở ${n} ngách (${signal.total_sample_size} video mẫu).${hookPart} → Thử lặp lại hook/format này cho video kế tiếp, giữ payoff trong 3 giây đầu.`;
}

export function shouldShowCrossFormatSignal(
  signal: CrossFormatSignal | null | undefined,
): signal is CrossFormatSignal {
  if (!signal) return false;
  return signal.niches_with_format >= 3 && signal.total_sample_size >= 20;
}
