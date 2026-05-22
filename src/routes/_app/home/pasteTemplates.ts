/**
 * Studio Home composer paste-template helpers (legacy).
 *
 * Paste-template chips were removed from QueryComposer (§4.11.2 depth pills).
 * Guards remain for users who still paste the old template phrases manually.
 */

export const PASTE_VIDEO_TEMPLATE =
  "Tại sao video này nổ/flop? Dán link TikTok vào đây:\n";

// ``@…`` (U+2026 horizontal ellipsis) keeps the visual cue that the
// user should type ``@username`` while breaking the FE classifier
// regex match (… isn't in ``[a-zA-Z0-9_.]``).
export const PASTE_HANDLE_TEMPLATE =
  "Soi kênh đối thủ — dán @… (handle TikTok) vào đây:\n";

const URL_RE = /https?:\/\/\S+/i;
const HANDLE_RE = /@[a-zA-Z0-9_.]+/;

/**
 * Returns a Vietnamese inline hint when the composer contains an
 * unfilled paste-template placeholder, else ``null``. The caller
 * blocks submission and surfaces the hint above/below the composer.
 */
export function unfilledPasteTemplateHint(text: string): string | null {
  const t = text.trim();
  if (!t) return null;
  // URL template — placeholder phrase is present but no actual URL was
  // pasted. We use ``startsWith`` to keep the guard precise; if the
  // user typed their own custom flop question, it shouldn't trigger.
  if (t.startsWith("Tại sao video này nổ/flop?") && !URL_RE.test(t)) {
    return "Dán link TikTok của video bạn muốn phân tích vào composer trước khi gửi.";
  }
  // Handle template — phrase present but no real @handle pasted. Note
  // that the canonical placeholder uses ``@…`` which HANDLE_RE never
  // matches, so a real ``@username`` will short-circuit this check.
  if (t.startsWith("Soi kênh đối thủ") && !HANDLE_RE.test(t)) {
    return "Dán @handle TikTok của kênh đối thủ vào composer trước khi gửi.";
  }
  return null;
}
