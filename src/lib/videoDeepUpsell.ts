/** §4.11.3 — post–Cơ bản upsell: locked deep-only section teasers. */

export type LockedSectionTeaser = {
  section_id: string;
  title_vi: string;
};

/** Fallback Vietnamese labels (§4.2 deep-only sections) when BE omits title_vi. */
export const DEEP_ONLY_SECTION_LABELS_VI: Record<string, string> = {
  distribution: "Phân phối và khám phá",
  boost_attribution: "Có dấu hiệu ads/seeding",
  douyin_origin: "Nguồn gốc Douyin",
  channel_pattern: "Video so với kênh",
  commerce: "Thương mại và chuyển đổi",
  metadata: "Khung an toàn và loại tài khoản",
  editing: "Màu sắc và chữ trên hình",
  sound: "Âm thanh và nhịp điệu",
  persona: "Phong cách và nhân vật",
  script_structure: "Cấu trúc kịch bản",
};

export function labelForLockedSection(sectionId: string, titleVi?: string | null): string {
  const trimmed = titleVi?.trim();
  if (trimmed) return trimmed;
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
    out.push({
      section_id: sid,
      title_vi: labelForLockedSection(sid, row.title_vi),
    });
  }
  return out;
}

export function shouldShowDeepUpsell(
  analysisDepth: "basic" | "deep" | null | undefined,
  reportDepth: "basic" | "deep" | undefined,
): boolean {
  const effective = reportDepth ?? analysisDepth ?? "basic";
  return effective === "basic";
}
