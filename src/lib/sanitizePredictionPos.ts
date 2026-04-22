/**
 * Strip ``prediction_pos`` placeholders that some older Gemini runs
 * emitted as ``~0`` / ``~—`` before the prompt was tightened in April
 * 2026. Without this sanitizer the QA audit's BUG-06 repro ("Video đạt
 * 1.8M view nhưng ... kênh **~0** cần điều chỉnh...") could still leak
 * from cached payloads stored in ``videos.analysis_json``.
 *
 * Matches any of: ``~0``, ``~ 0``, ``~—``, ``~-``, ``~``. Everything
 * else is passed through untouched so real predictions like ``~34K``
 * keep their leading tilde.
 */
export function sanitizePredictionPos(raw: string | null | undefined): string {
  if (!raw) return "";
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (/^~\s*0\b|^~\s*[—-]+\s*$|^~\s*$/i.test(trimmed)) return "";
  return raw;
}
