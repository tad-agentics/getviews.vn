import type {
  DiagnosisSectionVi,
  VideoContextAxisBlock,
  VideoContextAxisId,
} from "@/lib/api-types";

/** Unified FE block for metadata + boost_attribution + channel_pattern. */
export const VIDEO_CONTEXT_SECTION_TITLE = "Phân tích bối cảnh & diễn biến";

export const CONTEXT_AXIS_TITLES: Record<VideoContextAxisId, string> = {
  context: "Bối cảnh & khán giả",
  distribution: "Diễn biến phân phối",
  channel: "So với kênh của bạn",
};

const MERGE_SOURCE_IDS = new Set(["metadata", "boost_attribution", "channel_pattern"]);

function sectionBody(s: DiagnosisSectionVi): string {
  return (s.text_vi || s.text || "").trim();
}

function buildAxisBlock(
  axisId: VideoContextAxisId,
  section: DiagnosisSectionVi | undefined,
): VideoContextAxisBlock | null {
  if (!section) return null;
  const text = sectionBody(section);
  const findings = section.findings ?? [];
  const tiles = Array.isArray(section.embedded_tiles) ? section.embedded_tiles : [];
  if (!text && findings.length === 0 && tiles.length === 0) {
    return null;
  }
  return {
    axis_id: axisId,
    title_vi: CONTEXT_AXIS_TITLES[axisId],
    text_vi: text,
    text,
    findings: findings.length > 0 ? findings : undefined,
    embedded_tiles: tiles.length > 0 ? tiles : undefined,
  };
}

function buildContextAxes(
  metadata: DiagnosisSectionVi | undefined,
  boost: DiagnosisSectionVi | undefined,
  channel: DiagnosisSectionVi | undefined,
  hasStatsHistory: boolean,
): VideoContextAxisBlock[] {
  const axes: VideoContextAxisBlock[] = [];
  const contextAxis = buildAxisBlock("context", metadata);
  if (contextAxis) axes.push(contextAxis);
  const distributionAxis = buildAxisBlock("distribution", boost);
  if (distributionAxis) {
    axes.push(distributionAxis);
  } else if (hasStatsHistory) {
    // Stats-history strip lives on the distribution axis (rendered from `meta`,
    // not section fields). Keep the axis even when no boost section exists so the
    // post-publish timeline never vanishes.
    axes.push({
      axis_id: "distribution",
      title_vi: CONTEXT_AXIS_TITLES.distribution,
      text_vi: "",
      text: "",
    });
  }
  const channelAxis = buildAxisBlock("channel", channel);
  if (channelAxis) axes.push(channelAxis);
  return axes;
}

export interface MergeVideoContextSectionsResult {
  sections: DiagnosisSectionVi[];
  /** True when metadata + at least one adjunct source were folded into context_axes. */
  hasContextBlock: boolean;
  /** Source section_ids folded into the context block (for suppressing standalone fallbacks). */
  foldedSources: Set<string>;
}

/**
 * Collapse «Phân tích bối cảnh & diễn biến», «Có dấu hiệu ads/seeding», and
 * «Video này so với kênh bạn» into one multi-axis metadata block.
 *
 * Gate: metadata must be present AND at least one of boost_attribution or
 * channel_pattern — metadata is the host block (Trục 1).
 */
export function mergeVideoContextSections(
  sections: DiagnosisSectionVi[],
  options: { hasStatsHistory?: boolean } = {},
): MergeVideoContextSectionsResult {
  if (!sections.length) {
    return { sections, hasContextBlock: false, foldedSources: new Set() };
  }

  const metadata = sections.find((s) => String(s.section_id) === "metadata");
  const boost = sections.find((s) => String(s.section_id) === "boost_attribution");
  const channel = sections.find((s) => String(s.section_id) === "channel_pattern");

  const hasAdjunct = Boolean(boost || channel);
  if (!metadata || !hasAdjunct) {
    return { sections, hasContextBlock: false, foldedSources: new Set() };
  }

  const contextAxes = buildContextAxes(
    metadata,
    boost,
    channel,
    options.hasStatsHistory ?? false,
  );
  if (contextAxes.length < 2) {
    return { sections, hasContextBlock: false, foldedSources: new Set() };
  }

  const foldedSources = new Set<string>(["metadata"]);
  if (boost) foldedSources.add("boost_attribution");
  if (channel) foldedSources.add("channel_pattern");

  const rest = sections.filter((s) => !MERGE_SOURCE_IDS.has(String(s.section_id)));

  const merged: DiagnosisSectionVi = {
    section_id: "metadata",
    title_vi: metadata.title_vi || VIDEO_CONTEXT_SECTION_TITLE,
    title: metadata.title || VIDEO_CONTEXT_SECTION_TITLE,
    text_vi: "",
    text: "",
    context_axes: contextAxes,
    findings: metadata.findings?.length ? metadata.findings : undefined,
    embedded_tiles: metadata.embedded_tiles?.length ? metadata.embedded_tiles : undefined,
  };

  const sourceIndices = sections
    .map((s, i) => (MERGE_SOURCE_IDS.has(String(s.section_id)) ? i : -1))
    .filter((i) => i >= 0);
  const earliestSourceIdx = Math.min(...sourceIndices);
  const insertAt = sections
    .slice(0, earliestSourceIdx)
    .filter((s) => !MERGE_SOURCE_IDS.has(String(s.section_id))).length;

  const out = [...rest];
  out.splice(insertAt, 0, merged);

  return { sections: out, hasContextBlock: true, foldedSources };
}
