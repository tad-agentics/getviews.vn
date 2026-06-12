/**
 * Fix-chip labelling for diagnosis findings.
 *
 * Live audit (2026-06-12): positive/keep findings rendered "Sửa: Tiếp tục
 * sử dụng…" — a "fix" chip prefixed onto advice that says *keep doing this*.
 * When ``fix_vi`` opens with a keep-verb the chip must read "Giữ" with a
 * positive tone instead of the corrective "Sửa".
 */

// NOTE: \b is unreliable after Vietnamese letters (non-ASCII ⇒ non-\w in JS),
// so the boundary is an explicit whitespace/punctuation lookahead.
const KEEP_VERB_RE = /^\s*(?:tiếp tục|giữ|nhân bản|duy trì)(?=[\s,.:;!—–-]|$)/i;

export interface FixChipMeta {
  /** Chip label — "Giữ" for keep-advice, "Sửa" for corrective fixes. */
  label: "Giữ" | "Sửa";
  /** True when the finding is a keep/positive — render with positive tone. */
  positive: boolean;
}

export function fixChipMeta(fixVi: string | null | undefined): FixChipMeta {
  if (fixVi && KEEP_VERB_RE.test(fixVi)) {
    return { label: "Giữ", positive: true };
  }
  return { label: "Sửa", positive: false };
}
