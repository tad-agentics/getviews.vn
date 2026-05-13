/**
 * Phase 4.4.6 — v5 compatibility shim.
 *
 * Detects whether a VideoReportPayload was produced by the v5 BE pipeline
 * and provides typed helpers that components use to decide which render path
 * to take. v4 responses fall back gracefully; no hard dependency on v5 fields.
 *
 * Detection priority (first match wins):
 *   1. _schema_version === "v5"  ← definitive BE marker (Phase 4.4.6 fix)
 *   2. channel_context.per_format_views  ← structural v5 field (Phase 4.1)
 *   3. creator_comparison.format_match   ← structural v5 field (Phase 4.2)
 *   4. narrative_vi.van_de_chinh ≥100 chars AND ≥2 punctuation clusters
 *      ← last-resort fallback for sessions cached before the marker was deployed.
 *      Length guard prevents exclamatory v4 one-liners ("Tuyệt vời!!! Video tốt....")
 *      from triggering false positives: they match 2 punctuation groups but are
 *      always < 60 chars, whereas a proper 3-sentence v5 lead is always ≥ 100 chars.
 *
 * This module is pure computation — no side effects, no React.
 */

type AnyRecord = Record<string, unknown>;

/**
 * Minimum character length for the sentence-count fallback.
 * A proper v5 van_de_chinh (3 full Vietnamese sentences with channel metrics)
 * is always ≥ 100 chars. Short exclamatory strings are always < 60 chars.
 */
const V5_VAN_DE_CHINH_MIN_LEN = 100;

/**
 * Count consecutive punctuation clusters as sentence-boundary proxies.
 * The `+` quantifier groups "!!!" and "..." as single clusters, which is
 * correct: repeated punctuation marks one sentence end, not multiple.
 * Requires V5_VAN_DE_CHINH_MIN_LEN guard to filter short exclamatory strings
 * that happen to produce ≥2 clusters (e.g. "Tuyệt vời!!! Video tốt....").
 */
function countPunctuationClusters(text: string): number {
  return (text.match(/[.!?…]+/g) ?? []).length;
}

/**
 * Returns true when the response has at least one v5 indicator.
 * Used to opt into v5 layout in VideoBody without breaking v4 sessions.
 */
export function isV5Report(report: AnyRecord): boolean {
  // 1. Definitive marker emitted by the v5 pipeline (both on-demand + corpus paths).
  if (report._schema_version === "v5") return true;

  // 2–3. Structural fields only present in v5 responses.
  const channelCtx = report.channel_context as AnyRecord | null | undefined;
  if (channelCtx?.per_format_views) return true;

  const creatorComparison = report.creator_comparison as AnyRecord | null | undefined;
  if (creatorComparison?.format_match) return true;

  // 4. Last-resort heuristic for sessions cached before the _schema_version marker.
  //    Requires both minimum length (rules out v4 one-liners / short exclamatory
  //    strings) AND ≥2 punctuation clusters (rules out single-sentence text).
  const narrativeVi = report.narrative_vi as AnyRecord | null | undefined;
  const vanDeChinhText = narrativeVi?.van_de_chinh as string | null | undefined;
  if (
    vanDeChinhText &&
    vanDeChinhText.length >= V5_VAN_DE_CHINH_MIN_LEN &&
    countPunctuationClusters(vanDeChinhText) >= 2
  ) return true;

  return false;
}

/**
 * Returns the effective errors list for the FE.
 * - v5: already capped at 3 by BE; returned as-is.
 * - v4: cap at 3 on the FE side (Phase 4.4.2 slice already handles this).
 *
 * This helper exists so tests and higher-level components have a single
 * source of truth rather than duplicating the cap logic.
 */
export function resolveDisplayErrors(
  errors: AnyRecord[],
  isV5: boolean,
): AnyRecord[] {
  if (isV5) return errors; // BE already capped
  return errors.slice(0, 3);  // FE cap for v4 responses
}
