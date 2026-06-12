/**
 * Legacy script reports often repeat corpus proof in ``ket_luan_nhanh`` (@handle + view)
 * while the answer UI shows the same clips in the corpus strip — drop proof sentences only.
 */
const PROOF_SENTENCE =
  /@\w|(?:\d[\d.,]+\s*view\b)|Format này.*(?:dựa trên|đã được|chứng minh|như @)/iu;

export function scriptVerdictForDisplay(text: string, hasCorpusStrip: boolean): string {
  const trimmed = text.trim();
  if (!trimmed || !hasCorpusStrip) return trimmed;

  const parts = trimmed.split(/(?<=[.!?…])\s+/).map((s) => s.trim()).filter(Boolean);
  const kept = parts.filter((s) => !PROOF_SENTENCE.test(s));
  return (kept.length > 0 ? kept.join(" ") : trimmed).trim();
}

export function shotHasCorpusPacing(
  shot: { corpus_avg?: number; winner_avg?: number },
  sceneRow?: { corpus_avg_duration?: number | null; winner_avg_duration?: number | null } | null,
): boolean {
  if (sceneRow) return true;
  return (
    (typeof shot.corpus_avg === "number" && Number.isFinite(shot.corpus_avg)) ||
    (typeof shot.winner_avg === "number" && Number.isFinite(shot.winner_avg))
  );
}
