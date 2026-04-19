/**
 * detectIntent — maps a raw user message to a pipeline intent.
 *
 * Two tiers only:
 *   Tier 1 (high)   — structural signals: TikTok URL → video_diagnosis / competitor_profile
 *                     @handle → competitor_profile / own_channel
 *   Tier 2 (medium) — explicit keyword patterns for specialized pipelines
 *
 * Everything else → follow_up (free), which routes to the Gemini chat backend.
 * Natural language, general questions, greetings, and anything ambiguous all
 * land here so the chat behaves like a real LLM assistant rather than a broken
 * intent router.
 *
 * Extracted from ChatScreen.tsx so the routing logic is unit-testable without
 * mounting the chat component. Lives here (not src/lib) because it's only used
 * by the app route — pathwise co-location.
 *
 * **B.3.4:** ``competitor_profile`` / ``own_channel`` are still detected here for
 * tests and clarity, but ChatScreen short-circuits sends to ``/app/channel``
 * instead of the paid chat / Cloud Run channel pipelines.
 */

export type IntentDecision = {
  intentType: string;
  isFree: boolean;
  confidence: "high" | "medium" | "low";
};

export function detectIntent(
  query: string,
  priorAssistant: boolean,
): IntentDecision {
  const q = query.trim();
  const ql = q.toLowerCase();

  // ── 1. URL DETECTION (highest confidence — structural) ────────────────────
  if (/https?:\/\/[^\s]*tiktok\.com/i.test(q)) {
    const hasTiktokProfileUrl = /tiktok\.com\/@[^\s/]+(?:\/(?!video|photo)[^\s]*)?(?:\s|$)/i.test(q)
      && !/\/video\//i.test(q)
      && !/\/photo\//i.test(q);
    return hasTiktokProfileUrl
      ? { intentType: "competitor_profile", isFree: false, confidence: "high" }
      : { intentType: "video_diagnosis", isFree: false, confidence: "high" };
  }

  // ── 2. HANDLE DETECTION (structural) ─────────────────────────────────────
  // Default when a @handle is present = competitor_profile — that's the
  // seller/creator research flow. own_channel only wins when an explicit
  // self-reference ("mình / tôi / tao / tui / channel của tao") is present.
  //
  // Historical bug: a bare "Soi kênh" matched ownChannelHandle and forced
  // "Soi kênh đối thủ @handle" (the card prompt) to route to own_channel.
  // Fix: require self-reference pronoun in the "soi kênh" branch, and short-
  // circuit to competitor_profile whenever "đối thủ" / "competitor" is named.
  if (/@\w/.test(q)) {
    const explicitCompetitor = /đối\s*thủ|competitor|rival|vs\.?\s*(mình|tôi)/i.test(ql);
    const ownChannelHandle = !explicitCompetitor && (
      /soi\s+kênh\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
      || /kênh\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
      || /channel\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
      || /\b(my|của\s+mình|của\s+tôi)\s+channel\b/i.test(ql)
      || /(review|phân\s+tích|đánh\s+giá)\s+kênh\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
    );
    return ownChannelHandle
      ? { intentType: "own_channel", isFree: false, confidence: "high" }
      : { intentType: "competitor_profile", isFree: false, confidence: "high" };
  }

  // ── 3. SHOT LIST ──────────────────────────────────────────────────────────
  if (/shot list|kịch bản|cách quay|hướng dẫn quay|quay như nào|quay thế nào|quay video|lên ý tưởng quay|plan quay|danh sách cảnh|cảnh quay/i.test(ql)) {
    return { intentType: "shot_list", isFree: false, confidence: "medium" };
  }

  // ── 4. CREATOR SEARCH (paid — EnsembleData query) ─────────────────────────
  if (/tìm\s*(creator|kol|koc|influencer|người.*quay)|gợi\s*ý\s*(kol|koc|creator)|creator\s*nào|kol\s*nào|thuê\s*(creator|kol)|ai đang làm tốt|koc nào|giới thiệu creator/i.test(ql)) {
    return { intentType: "creator_search", isFree: false, confidence: "medium" };
  }

  // ── 5. OWN CHANNEL (no handle given) ──────────────────────────────────────
  // Same guardrail as branch 2 — require an explicit self-reference. Without
  // either a @handle or a self-pronoun, we can't know whose channel the user
  // means, so we fall through to intent-agnostic follow_up rather than
  // hijacking the query.
  if (
    /soi\s+kênh\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
    || /kênh\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
    || /channel\s+(của\s+)?(mình|tôi|tao)/i.test(ql)
    || /\b(my|của\s+mình|của\s+tôi)\s+channel\b/i.test(ql)
    || /(review|phân\s+tích|đánh\s+giá)\s+kênh\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
  ) {
    return { intentType: "own_channel", isFree: false, confidence: "medium" };
  }

  // ── 6. CONTENT_DIRECTIONS + TREND disambiguation ──────────────────────────
  const isTrend = /đang viral|video viral|viral rồi|xu hướng|đang lên|bùng nổ|đang nổ|gì đang chạy|trend|tuần này|7 ngày|gần đây|đang trending|mới nổi/i.test(ql)
    || /\b(trending|viral)\b/i.test(ql);

  const isContent = /nên quay gì|quay gì|làm gì|video gì|format nào|hook nào|kiểu video|đang chạy tốt|đang work|đang hiệu quả|hướng content|content direction|hướng nội dung|nên làm gì|nên làm video|ý tưởng video|gì đang hot|gợi ý nội dung|loại video/i.test(ql);

  // trend_spike checked first — "tuần này / đang hot" is more specific than
  // generic content-direction keywords like "hook nào / format nào".
  // A prompt can match both (e.g. "xu hướng tuần này — hook nào đang chạy?"),
  // and trend_spike is the correct intent in that case.
  if (isTrend) return { intentType: "trend_spike", isFree: true, confidence: "medium" };
  if (isContent) return { intentType: "content_directions", isFree: false, confidence: "medium" };

  // ── 7. DEFAULT ────────────────────────────────────────────────────────────
  // Anything that doesn't match a structural signal or an explicit keyword is
  // treated as natural-language chat and routed to the Gemini follow_up handler.
  return {
    intentType: "follow_up",
    isFree: true,
    confidence: priorAssistant ? "medium" : "low",
  };
}
