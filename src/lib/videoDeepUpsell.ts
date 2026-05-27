import { formatDiagnosisSectionTitle } from "@/lib/formatters";

/** §4.11.3 — post–Cơ bản upsell: locked deep-only section teasers. */

export type LockedSectionTeaser = {
  section_id: string;
  title_vi: string;
  /** Full manifest signal count for this section (§4.8.1 upsell teaser). */
  signal_count?: number;
  /** Section-specific upsell copy (e.g. boost_attribution on basic). */
  teaser_vi?: string;
};

/** Fallback Vietnamese labels (§4.2 deep-only sections) when BE omits title_vi. */
export const DEEP_ONLY_SECTION_LABELS_VI: Record<string, string> = {
  distribution: "Phân phối và khám phá",
  boost_attribution: "Có dấu hiệu ads/seeding",
  douyin_origin: "Nguồn gốc Douyin",
  channel_pattern: "Video so với kênh",
  commerce: "Thương mại và chuyển đổi",
  metadata: "Bối cảnh phân tích",
  editing: "Màu sắc và chữ trên hình",
  sound: "Âm thanh và nhịp điệu",
  persona: "Phong cách và nhân vật",
  script_structure: "Dòng thời gian · Cấu trúc video",
};

export function labelForLockedSection(sectionId: string, titleVi?: string | null): string {
  const trimmed = titleVi?.trim();
  if (trimmed) return formatDiagnosisSectionTitle(trimmed);
  return DEEP_ONLY_SECTION_LABELS_VI[sectionId] ?? sectionId.replace(/_/g, " ");
}

/** Keep display order stable; drop empty ids. */
export function normalizeLockedSectionTeasers(
  sections: LockedSectionTeaser[] | null | undefined,
): LockedSectionTeaser[] {
  if (!sections?.length) return [];
  const seen = new Set<string>();
  const out: LockedSectionTeaser[] = [];
  for (const row of sections) {
    const sid = String(row.section_id ?? "").trim();
    if (!sid || seen.has(sid)) continue;
    seen.add(sid);
    const teaser = row.teaser_vi?.trim();
    const count =
      typeof row.signal_count === "number" && row.signal_count > 0
        ? row.signal_count
        : undefined;
    out.push({
      section_id: sid,
      title_vi: labelForLockedSection(sid, row.title_vi),
      ...(count !== undefined ? { signal_count: count } : {}),
      ...(teaser ? { teaser_vi: teaser } : {}),
    });
  }
  return out;
}

/** Subtitle under locked-section pill — manifest count or §4.7 boost teaser. */
export function lockedSectionSubtitle(row: LockedSectionTeaser): string | null {
  const teaser = row.teaser_vi?.trim();
  if (teaser) return teaser;
  if (row.signal_count && row.signal_count > 0) {
    return `+${row.signal_count} nhận định`;
  }
  return null;
}

export function shouldShowDeepUpsell(
  analysisDepth: "basic" | "deep" | null | undefined,
  reportDepth: "basic" | "deep" | undefined,
): boolean {
  const effective = reportDepth ?? analysisDepth ?? "basic";
  return effective === "basic";
}
