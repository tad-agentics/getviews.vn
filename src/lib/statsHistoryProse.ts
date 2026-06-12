import type { StatsHistorySnapshot, VideoAnalyzeMeta } from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";

export const STATS_PROSE_IN_SECTION_RE =
  /6 giờ đầu|thuật toán dừng mở rộng|Chưa tốt về phân phối|Tốt — nội dung giữ/i;

const PHASE_RANK: Record<string, number> = { t0: 0, t6h: 1, t24h: 2 };

function erPct(row: StatsHistorySnapshot): number {
  const v = row.views;
  if (v <= 0) return 0;
  return ((row.likes + row.comments + row.shares) / v) * 100;
}

function phaseLabel(phase: string): string {
  if (phase === "t0") return "lúc đăng";
  if (phase === "t6h") return "sau 6 giờ";
  if (phase === "t24h") return "sau 24 giờ";
  return phase;
}

function growthPct(from: number, to: number): number | null {
  if (from <= 0) return null;
  return ((to - from) / from) * 100;
}

export function hasStatsHistorySnapshots(
  history: StatsHistorySnapshot[] | null | undefined,
): boolean {
  const rows = (history ?? []).filter(
    (r) => r && typeof r.views === "number" && r.phase,
  );
  return rows.length >= 2;
}

/** Deterministic prose — explains view/ER evolution for the metadata block. */
export function buildStatsHistoryProse(
  history: StatsHistorySnapshot[] | null | undefined,
  distributionShape?: string | null,
): string {
  const rows = (history ?? []).filter(
    (r) => r && typeof r.views === "number" && r.phase,
  );
  if (rows.length < 2) return "";

  const ordered = [...rows].sort((a, b) => {
    const ra = PHASE_RANK[a.phase] ?? 9;
    const rb = PHASE_RANK[b.phase] ?? 9;
    return ra - rb || a.at.localeCompare(b.at);
  });

  const byPhase = new Map(ordered.map((r) => [r.phase, r]));
  const t0 = byPhase.get("t0") ?? ordered[0];
  const t6 = byPhase.get("t6h");
  const t24 = byPhase.get("t24h") ?? ordered[ordered.length - 1];

  const spikeFlat =
    distributionShape === "spike_then_flat" ||
    (t6 != null &&
      t0.views > 0 &&
      t6.views >= t0.views * 2 &&
      t24.views > 0 &&
      t6.views > 0 &&
      (t24.views - t6.views) / t6.views < 0.08);

  const parts: string[] = [];

  if (t6 && t24 && t6 !== t24) {
    const g06 = growthPct(t0.views, t6.views);
    const g624 = growthPct(t6.views, t24.views);
    const er0 = erPct(t0);
    const er6 = erPct(t6);
    const er24 = erPct(t24);

    if (spikeFlat) {
      parts.push(
        `View tăng mạnh trong 6 giờ đầu (${formatViews(t0.views)} → ${formatViews(t6.views)}${g06 != null ? `, +${Math.round(g06)}%` : ""}) — TikTok đã đẩy thử nghiệm.`,
        `Đến +24h chỉ thêm ${g624 != null && g624 >= 0 ? `${Math.round(g624)}%` : "rất ít"} (${formatViews(t24.views)}) — thuật toán dừng mở rộng phân phối.`,
        er6 > 0 && er24 < er6 * 0.85
          ? `ER giảm từ ${er6.toFixed(1)}% xuống ${er24.toFixed(1)}% — tương tác không đủ để được đẩy tiếp.`
          : `ER ${er24.toFixed(1)}% ở +24h — cần tín hiệu comment/lưu mạnh hơn để vượt cửa sổ thử nghiệm.`,
        "Chưa tốt về phân phối dài hạn. Cải thiện: thêm câu hỏi/CTA kích comment ngay hook, thử caption-hashtag rõ đối tượng, hoặc đăng lại khung giờ FYP cao hơn với hook mạnh hơn 3 giây đầu.",
      );
    } else if (g06 != null && g06 < 15 && (g624 == null || g624 < 20)) {
      parts.push(
        `View gần như đứng sau đăng (${formatViews(t0.views)} → ${formatViews(t24.views)} đến +24h) — thuật toán chưa kích hoạt phân phối rộng.`,
        `ER ${er24.toFixed(1)}% ở mốc cuối.`,
        "Chưa tốt. Cải thiện: làm rõ đối tượng trong 3 giây đầu, tăng contrast thumbnail/caption, và kiểm tra hashtag có khớp ngách không.",
      );
    } else if (
      t24.views > t6.views &&
      t6.views > t0.views &&
      (g624 ?? 0) >= 10
    ) {
      parts.push(
        `View tăng đều qua các mốc (${formatViews(t0.views)} → ${formatViews(t6.views)} → ${formatViews(t24.views)}) — phân phối đang được duy trì.`,
        `ER ${er0.toFixed(1)}% → ${er24.toFixed(1)}%.`,
        er24 >= er0 * 0.9
          ? "Tốt — nội dung giữ được tương tác trong lúc được đẩy. Tiếp tục format và nhịp hook này."
          : "Khá tốt về view nhưng ER giảm dần — thử chèn thêm beat tương tác (hỏi, poll caption) trước CTA để giữ ER khi scale.",
      );
    } else {
      parts.push(
        `Diễn biến: ${formatViews(t0.views)} ${phaseLabel(t0.phase)}`,
        t6 ? `→ ${formatViews(t6.views)} sau 6h` : "",
        `→ ${formatViews(t24.views)} sau 24h.`,
        `ER ${er24.toFixed(1)}% ở mốc cuối.`,
        spikeFlat
          ? "Thuật toán thử nghiệm rồi dừng — ưu tiên tăng tương tác sớm."
          : "So với mốc đầu, tốc độ tăng view cho biết mức độ thuật toán đang đẩy — đối chiếu với ER để biết nội dung hay phân phối là nút thắt.",
      );
    }
  } else {
    const last = ordered[ordered.length - 1];
    const g = growthPct(t0.views, last.views);
    const erLast = erPct(last);
    parts.push(
      `Từ ${formatViews(t0.views)} (${phaseLabel(t0.phase)}) đến ${formatViews(last.views)} (${phaseLabel(last.phase)})${g != null ? ` — thay đổi ${g >= 0 ? "+" : ""}${Math.round(g)}%` : ""}.`,
      `ER ${erLast.toFixed(1)}% ở mốc cuối.`,
      g != null && g < 20
        ? "Chưa tốt — phân phối hạn chế. Cải thiện hook và tín hiệu tương tác sớm."
        : "Xu hướng tích cực — theo dõi thêm mốc +24h nếu có để xác nhận.",
    );
  }

  return parts.filter(Boolean).join(" ");
}

/** Route section/fallback prose to the strip it belongs with. */
export function resolveMetadataStripProse({
  sectionText,
  fallbackProse,
  meta,
}: {
  sectionText: string;
  fallbackProse?: string;
  meta: VideoAnalyzeMeta;
}): { contextProse?: string; statsProse?: string } {
  const fromSection = sectionText.trim();
  const fallback = fallbackProse?.trim() ?? "";

  if (fromSection && STATS_PROSE_IN_SECTION_RE.test(fromSection)) {
    return { contextProse: fallback || undefined, statsProse: fromSection };
  }

  const contextProse = fromSection || fallback || undefined;
  const builtStats = buildStatsHistoryProse(meta.stats_history, meta.distribution_shape);
  const statsProse =
    builtStats && (!fromSection || !STATS_PROSE_IN_SECTION_RE.test(fromSection))
      ? builtStats
      : undefined;

  return { contextProse, statsProse };
}
