/**
 * Render helper for ActionCard forecast rows.
 *
 * BUG-15 (QA audit 2026-04-22): two of the three "Bước tiếp theo" cards
 * (Soi kênh đối thủ, Theo dõi trend) showed ``Dự kiến: — view (kênh TB —)``
 * because the backend left ``expected_range`` / ``baseline`` as em-dashes
 * when no prediction was available. A row of em-dashes makes a CTA look
 * broken. Now: if both values are missing the caller suppresses the line
 * entirely. If only the baseline is missing we show the expected range
 * alone. Only when both are populated do we render the full "(kênh TB X)"
 * suffix.
 *
 * Returns ``null`` when there's nothing meaningful to show so callers can
 * skip rendering the whole bordered row.
 */
export type ForecastLike = {
  expected_range?: string | null;
  baseline?: string | null;
};

function isMissing(v: string | null | undefined): boolean {
  if (v == null) return true;
  const t = v.trim();
  if (!t) return true;
  if (/^[—\-]+$/.test(t)) return true;
  return false;
}

export function renderForecastLine(
  forecast: ForecastLike | null | undefined,
  opts?: { prefix?: string; unit?: string },
): string | null {
  if (!forecast) return null;
  const { expected_range, baseline } = forecast;
  const prefix = opts?.prefix ?? "Dự kiến:";
  const unit = opts?.unit ?? "view";
  const rangeMissing = isMissing(expected_range);
  const baselineMissing = isMissing(baseline);
  if (rangeMissing && baselineMissing) return null;
  if (rangeMissing) {
    // Range is the headline number. Without it we'd have only a baseline
    // which is meaningless in isolation — suppress.
    return null;
  }
  const head = `${prefix} ${(expected_range ?? "").trim()} ${unit}`.trim();
  if (baselineMissing) return head;
  return `${head} (kênh TB ${(baseline ?? "").trim()})`;
}
