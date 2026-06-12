/**
 * Belt-and-braces ordering for the next_video shot script.
 *
 * The v6 prompt requires bullets in chronological order (Hook → Beat 1 →
 * Beat 2 → CTA) but Gemini occasionally emits them shuffled (live audit
 * 2026-06-12). When ≥2 lines carry a "(Ns-Ms)" timestamp, re-order just
 * those lines by their start second — lines without timestamps (e.g. a
 * trailing CTA) keep their original slots.
 */

// "(0-1s)", "(2s-4s)", "(0.5–3s)" — start seconds is group 1.
const SCRIPT_TS_RE = /\(\s*(\d+(?:[.,]\d+)?)\s*s?\s*[-–—]\s*\d+(?:[.,]\d+)?\s*s\s*\)/i;

export function scriptLineStartSec(line: string): number | null {
  const m = line.match(SCRIPT_TS_RE);
  if (!m) return null;
  const t = Number.parseFloat(m[1].replace(",", "."));
  return Number.isFinite(t) ? t : null;
}

export function sortScriptBulletsByTimestamp(text: string): string {
  const lines = text.split("\n");
  const stampedIdx: number[] = [];
  const stamped: { t: number; line: string }[] = [];
  for (let i = 0; i < lines.length; i++) {
    const t = scriptLineStartSec(lines[i]);
    if (t !== null) {
      stampedIdx.push(i);
      stamped.push({ t, line: lines[i] });
    }
  }
  if (stamped.length < 2) return text;
  // Array.prototype.sort is stable — equal timestamps keep authored order.
  const sorted = [...stamped].sort((a, b) => a.t - b.t);
  if (sorted.every((s, k) => s.line === stamped[k].line)) return text;
  const out = [...lines];
  stampedIdx.forEach((lineIdx, k) => {
    out[lineIdx] = sorted[k].line;
  });
  return out.join("\n");
}
