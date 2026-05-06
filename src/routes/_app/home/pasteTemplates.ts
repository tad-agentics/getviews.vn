/**
 * Studio Home composer paste-template helpers.
 *
 * The "Dán link video" / "Dán @handle" buttons under the composer fill
 * the textarea with a Vietnamese template the user is supposed to
 * complete with a real URL or @handle. L1.5 audit follow-up flagged
 * two related bugs in the original templates:
 *
 *   1. The handle template included a literal ``@handle`` token. When
 *      the user clicked the chip and submitted without replacing it,
 *      ``detectIntent`` parsed ``@handle`` as a real TikTok handle and
 *      confidently routed to ``/app/channel?handle=handle`` (a 404).
 *      Fix: switch to ``@…`` (Vietnamese ellipsis) which the regex
 *      ``/@([a-zA-Z0-9_.]+)/`` cannot match.
 *
 *   2. The URL template fell through to ``follow_up_unclassifiable``
 *      → generic answer. Less wrong than a 404 but still confusing —
 *      the user expected to paste a URL.
 *
 * The fix here addresses both: cleaner placeholders + a submit-time
 * guard that detects unfilled templates and returns a Vietnamese hint
 * the caller surfaces inline.
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
