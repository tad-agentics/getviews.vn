/**
 * detectIntent — maps a raw user message to a pipeline intent (Phase C §A).
 *
 * Tier 1 (high)   — structural: TikTok URL, @handle
 * Tier 2 (medium) — keyword branches for specialized pipelines
 * Tier 3 (low)    — follow_up_unclassifiable → generic /answer (Gemini classifier on server)
 *
 * `INTENT_DESTINATIONS` + `resolveDestination` are the C.7 routing matrix
 * (post–chat-deletion). See `artifacts/plans/phase-c-plan.md` §C.7.
 */

export type IntentDecision = {
  intentType: string;
  isFree: boolean;
  confidence: "high" | "medium" | "low";
};

/** Post–C.7: every query lands on a concrete screen (no "chat"). */
export type Destination =
  | "video"
  | "channel"
  | "kol"
  | "script"
  | "answer:pattern"
  | "answer:ideas"
  | "answer:timing"
  | "answer:generic";

/** Intents with a fixed row in `INTENT_DESTINATIONS` (excludes dynamic follow_up_classifiable). */
export type FixedIntentId =
  | "video_diagnosis"
  | "competitor_profile"
  | "own_channel"
  | "creator_search"
  | "shot_list"
  | "metadata_only"
  | "comparison"
  | "trend_spike"
  | "content_directions"
  | "subniche_breakdown"
  | "format_lifecycle_optimize"
  | "fatigue"
  | "brief_generation"
  | "hook_variants"
  | "timing"
  | "content_calendar"
  | "series_audit"
  | "own_flop_no_url"
  | "follow_up_unclassifiable";

export const INTENT_DESTINATIONS: Record<FixedIntentId, Destination> = {
  video_diagnosis: "video",
  competitor_profile: "channel",
  own_channel: "channel",
  creator_search: "kol",
  shot_list: "script",
  metadata_only: "video",
  comparison: "kol",
  trend_spike: "answer:pattern",
  content_directions: "answer:pattern",
  subniche_breakdown: "answer:pattern",
  format_lifecycle_optimize: "answer:pattern",
  fatigue: "answer:pattern",
  brief_generation: "answer:ideas",
  hook_variants: "answer:ideas",
  timing: "answer:timing",
  content_calendar: "answer:pattern",
  series_audit: "answer:pattern",
  own_flop_no_url: "answer:pattern",
  follow_up_unclassifiable: "answer:generic",
};

export type ClassifiedIntent =
  | { id: FixedIntentId }
  | { id: "follow_up_classifiable"; subject: "pattern" | "ideas" | "timing" };

export function resolveDestination(intent: ClassifiedIntent): Destination {
  if (intent.id === "follow_up_classifiable") {
    return `answer:${intent.subject}` as const;
  }
  return INTENT_DESTINATIONS[intent.id];
}

function countHandles(q: string): number {
  const m = q.match(/@[\w.]+/g);
  return m?.length ?? 0;
}

export function detectIntent(
  query: string,
  priorAssistant: boolean,
): IntentDecision {
  const q = query.trim();
  const ql = q.toLowerCase();

  // ── 0. MULTI-URL → series audit (before single-URL branch) ──────────────
  const tiktokUrls = q.match(/https?:\/\/[^\s]*tiktok\.com\/[^\s]+/gi) ?? [];
  if (tiktokUrls.length >= 2) {
    return { intentType: "series_audit", isFree: false, confidence: "high" };
  }

  // ── OWN CHANNEL / VIDEO FLOP (no TikTok URL) ─────────────────────────────
  if (
    !/https?:\/\/[^\s]*tiktok\.com/i.test(q)
    && (
      /\b(video|kênh|channel)\s+(của\s+)?(mình|tôi|tao|tui)\b/i.test(ql)
      || /\b(kênh|channel)\s+(mình|tôi)\b/i.test(ql)
      || /\b(my|kênh mình)\s+(video|channel)\b/i.test(ql)
    )
    && /\b(flop|ít view|không lên|low view|dead|underperform|chết)\b/i.test(ql)
  ) {
    return { intentType: "own_flop_no_url", isFree: false, confidence: "medium" };
  }

  // ── 1. URL DETECTION (highest confidence — structural) ────────────────────
  if (/https?:\/\/[^\s]*tiktok\.com/i.test(q)) {
    const hasTiktokProfileUrl = /tiktok\.com\/@[^\s/]+(?:\/(?!video|photo)[^\s]*)?(?:\s|$)/i.test(q)
      && !/\/video\//i.test(q)
      && !/\/photo\//i.test(q);
    if (
      hasTiktokProfileUrl
      && /\b(stats|metrics|lượt xem|view|follow|chỉ số|số liệu)\b/i.test(ql)
      && !/\b(phân tích|analyze|tại sao|why|flop)\b/i.test(ql)
    ) {
      return { intentType: "metadata_only", isFree: false, confidence: "high" };
    }
    return hasTiktokProfileUrl
      ? { intentType: "competitor_profile", isFree: false, confidence: "high" }
      : { intentType: "video_diagnosis", isFree: false, confidence: "high" };
  }

  // ── 2. HANDLE DETECTION (structural) ─────────────────────────────────────
  if (/@\w/.test(q)) {
    const explicitCompetitor = /đối\s*thủ|competitor|rival|vs\.?\s*(mình|tôi)/i.test(ql);
    const ownChannelHandle = !explicitCompetitor && (
      /soi\s+kênh\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
      || /kênh\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
      || /channel\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
      || /\b(my|của\s+mình|của\s+tôi)\s+channel\b/i.test(ql)
      || /(review|phân\s+tích|đánh\s+giá)\s+kênh\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
    );
    if (countHandles(q) >= 2 && /so sánh|compare|versus|hay hơn|ai hơn|\bvs\b/i.test(ql)) {
      return { intentType: "comparison", isFree: false, confidence: "medium" };
    }
    return ownChannelHandle
      ? { intentType: "own_channel", isFree: false, confidence: "high" }
      : { intentType: "competitor_profile", isFree: false, confidence: "high" };
  }

  // ── 3. SHOT LIST ──────────────────────────────────────────────────────────
  if (/shot list|kịch bản|cách quay|hướng dẫn quay|quay như nào|quay thế nào|quay video|lên ý tưởng quay|plan quay|danh sách cảnh|cảnh quay/i.test(ql)) {
    return { intentType: "shot_list", isFree: false, confidence: "medium" };
  }

  // ── 4. CREATOR SEARCH ─────────────────────────────────────────────────────
  if (/tìm\s*(creator|kol|koc|influencer|người.*quay)|gợi\s*ý\s*(kol|koc|creator)|creator\s*nào|kol\s*nào|thuê\s*(creator|kol)|ai đang làm tốt|koc nào|giới thiệu creator/i.test(ql)) {
    return { intentType: "creator_search", isFree: false, confidence: "medium" };
  }

  // ── 5. OWN CHANNEL (no handle given) ─────────────────────────────────────
  if (
    /soi\s+kênh\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
    || /kênh\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
    || /channel\s+(của\s+)?(mình|tôi|tao)/i.test(ql)
    || /\b(my|của\s+mình|của\s+tôi)\s+channel\b/i.test(ql)
    || /(review|phân\s+tích|đánh\s+giá)\s+kênh\s+(của\s+)?(mình|tôi|tao|tui)/i.test(ql)
  ) {
    return { intentType: "own_channel", isFree: false, confidence: "medium" };
  }

  // ── Phase C — TIMING ───────────────────────────────────────────────────────
  if (
    /đăng giờ nào|giờ nào tốt|thứ mấy tốt|best time to post|when to post|posting time|khung giờ vàng|lịch đăng/i.test(ql)
  ) {
    return { intentType: "timing", isFree: false, confidence: "medium" };
  }

  // ── Phase C — FATIGUE (declining patterns) ─────────────────────────────────
  if (
    /pattern.*hết trend|hết trend|pattern đang chết|đang chết dần|dead trend|declining format/i.test(ql)
  ) {
    return { intentType: "fatigue", isFree: false, confidence: "medium" };
  }

  // ── Phase C — FORMAT / LIFECYCLE ───────────────────────────────────────────
  if (/30s vs 60|60s vs 30|carousel vs video|ảnh vs video|short vs long|độ dài video/i.test(ql)) {
    return { intentType: "format_lifecycle_optimize", isFree: false, confidence: "medium" };
  }

  // ── Phase C — HOOK VARIANTS ────────────────────────────────────────────────
  if (
    /biến thể.*hook|hook variants|5 cách viết hook|cách viết hook này|viết lại hook/i.test(ql)
  ) {
    return { intentType: "hook_variants", isFree: false, confidence: "medium" };
  }

  // ── Phase C — CONTENT CALENDAR ─────────────────────────────────────────────
  if (/tuần này post gì|lịch content tuần|content calendar|khi nào post gì/i.test(ql)) {
    return { intentType: "content_calendar", isFree: false, confidence: "medium" };
  }

  // ── Phase C — SUBNICHE BREAKDOWN ──────────────────────────────────────────
  if (/ngách con|subniche|sub-niche|phân ngách/i.test(ql)) {
    return { intentType: "subniche_breakdown", isFree: false, confidence: "medium" };
  }

  // ── Phase C — BRIEF / IDEAS ───────────────────────────────────────────────
  if (/viết brief|brief tuần|5 ý tưởng video|ý tưởng video tuần|production brief/i.test(ql)) {
    return { intentType: "brief_generation", isFree: false, confidence: "medium" };
  }

  // ── 6. CONTENT_DIRECTIONS + TREND disambiguation ──────────────────────────
  const isTrend = /đang viral|video viral|viral rồi|xu hướng|đang lên|bùng nổ|đang nổ|gì đang chạy|trend|tuần này|7 ngày|gần đây|đang trending|mới nổi/i.test(ql)
    || /\b(trending|viral)\b/i.test(ql);

  const isContent = /nên quay gì|quay gì|làm gì|video gì|format nào|hook nào|kiểu video|đang chạy tốt|đang work|đang hiệu quả|hướng content|content direction|hướng nội dung|nên làm gì|nên làm video|ý tưởng video|gì đang hot|gợi ý nội dung|loại video/i.test(ql);

  if (isTrend) return { intentType: "trend_spike", isFree: true, confidence: "medium" };
  if (isContent) return { intentType: "content_directions", isFree: false, confidence: "medium" };

  // ── 7. DEFAULT (must match `INTENT_DESTINATIONS.follow_up_unclassifiable`) ─
  return {
    intentType: "follow_up_unclassifiable",
    isFree: true,
    confidence: priorAssistant ? "medium" : "low",
  };
}

/** POST `/answer/sessions` `format` — must match `AnswerSessionCreateBody` + DB check. */
export type AnswerSessionFormat = "pattern" | "ideas" | "timing" | "generic";

/**
 * Studio → `/app/answer` entry: map `detectIntent` to either a non-answer redirect
 * (video / channel / kol / script) or `{ format, intent_type }` for answer sessions.
 */
export type AnswerEntryPlan =
  | { kind: "redirect"; to: string }
  | { kind: "session"; format: AnswerSessionFormat; intent_type: string };

export function planAnswerEntry(query: string, priorAssistant: boolean): AnswerEntryPlan {
  const trimmed = query.trim();
  if (!trimmed) {
    return { kind: "session", format: "generic", intent_type: "follow_up_unclassifiable" };
  }
  const { intentType } = detectIntent(trimmed, priorAssistant);

  if (!(intentType in INTENT_DESTINATIONS)) {
    return { kind: "session", format: "generic", intent_type: intentType };
  }

  const dest = INTENT_DESTINATIONS[intentType as FixedIntentId];

  if (dest === "video") {
    const urlMatch = trimmed.match(/https?:\/\/[^\s]*tiktok\.com[^\s]*/i);
    const to = urlMatch
      ? `/app/video?url=${encodeURIComponent(urlMatch[0])}`
      : "/app/video";
    return { kind: "redirect", to };
  }
  if (dest === "channel") {
    const handleMatch = trimmed.match(/@([\w.]+)/);
    const to = handleMatch
      ? `/app/channel?handle=${encodeURIComponent(handleMatch[1])}`
      : "/app/channel";
    return { kind: "redirect", to };
  }
  if (dest === "kol") {
    return { kind: "redirect", to: "/app/kol" };
  }
  if (dest === "script") {
    return { kind: "redirect", to: "/app/script" };
  }

  const format: AnswerSessionFormat =
    dest === "answer:pattern"
      ? "pattern"
      : dest === "answer:ideas"
        ? "ideas"
        : dest === "answer:timing"
          ? "timing"
          : "generic";

  return { kind: "session", format, intent_type: intentType };
}

/**
 * Maps follow-up text to `POST /answer/sessions/:id/turns` `kind` (credit + audit).
 * Session `format` still drives which report builder runs on the server.
 */
export function appendTurnKindForQuery(
  query: string,
  priorAssistant: boolean,
): "timing" | "creators" | "script" | "generic" {
  const { intentType } = detectIntent(query.trim(), priorAssistant);
  if (intentType === "timing") return "timing";
  if (intentType === "creator_search" || intentType === "comparison") return "creators";
  if (intentType === "shot_list") return "script";
  return "generic";
}
