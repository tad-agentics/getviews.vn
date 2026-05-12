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

/** Post–C.7: every query lands on a concrete screen (no "chat").
 *
 * ``compare`` added Wave 4 PR #2 (2026-05-12) for the Compare flow —
 * two TikTok URLs → side-by-side diagnosis. Top-level (no ``answer:``
 * prefix) because the destination's URL-bearing nature mirrors
 * ``video`` (single-URL diagnosis), not the niche-scoped
 * ``answer:diagnostic`` shelf. PR #1 shipped this temporarily as
 * ``answer:compare``; the rename happens here before any FE component
 * shipped against the wrong slot. Canonical source — the BE side
 * had a mirror ``Destination`` Literal until L1.5 audit follow-up
 * (purged with the destination-resolution helpers it served). */
export type Destination =
  | "channel"
  | "compare"
  | "answer:pattern"
  | "answer:ideas"
  | "answer:timing"
  | "answer:lifecycle"
  | "answer:diagnostic"
  | "answer:generic"
  | "answer:video"
  | "answer:script";

/** Intents with a fixed row in `INTENT_DESTINATIONS` (excludes dynamic follow_up_classifiable).
 *
 * Historical drops:
 *   - 2026-04-22 — ``series_audit`` (multi-URL corpus comparison; no template)
 *     and ``comparison`` (head-to-head creator comparison; replaced by using
 *     ``competitor_profile`` twice or COMPARE_VIDEOS for two URLs).
 *   - L1.5 (2026-05-06) — server-side enum cleanup removed
 *     ``find_creators`` (alias for ``creator_search``), ``followup``
 *     (chat-era catch-all), and the ``comparison`` enum value (FE never
 *     listed it). Historical session intent_type strings normalise at
 *     the server router edge.
 */
export type FixedIntentId =
  | "video_diagnosis"
  | "competitor_profile"
  | "own_channel"
  | "creator_search"
  | "shot_list"
  | "trend_spike"
  | "content_directions"
  | "subniche_breakdown"
  | "format_lifecycle_optimize"
  | "fatigue"
  | "brief_generation"
  | "hook_variants"
  | "timing"
  | "content_calendar"
  | "own_flop_no_url"
  // Wave 4 PR #1 — two TikTok URLs in one message fires this intent.
  // Server-side mirror: ``QueryIntent.COMPARE_VIDEOS``.
  | "compare_videos"
  | "follow_up_unclassifiable";

export const INTENT_DESTINATIONS: Record<FixedIntentId, Destination> = {
  // ``video_diagnosis`` was the dedicated /app/video screen until the
  // template-migration. PR-3 (this commit) folds it into /app/answer
  // as just another session format alongside Pattern, Ideas, Timing,
  // Lifecycle, Diagnostic — same dispatcher, same chrome, follow-ups
  // stay in the same thread. /app/video is deleted entirely (zero
  // pre-launch traffic, no shim needed).
  video_diagnosis: "answer:video",
  competitor_profile: "channel",
  own_channel: "channel",
  // Creator-only pivot (PR #176, branch claude/remove-kol-creator-only):
  // /app/kol was deleted because finding KOLs is a seller use case. The
  // intent type stays in the system (server still classifies, answer
  // session still renders a "creators" turn block) but it now lands on
  // the generic answer surface instead of a dedicated screen.
  creator_search: "answer:generic",
  shot_list: "answer:script",
  trend_spike: "answer:pattern",
  content_directions: "answer:pattern",
  // Lifecycle template (2026-04-22) — stage pill + reach delta + health
  // score. See `artifacts/docs/report-template-prd-lifecycle.md`.
  // 2026-05-08 — `subniche_breakdown` + `fatigue` rerouted to `pattern`
  // (they rode lifecycle's fixture-with-disclaimer path because the
  // upstream hook-timeseries + subniche-taxonomy signal doesn't exist
  // yet). Pattern's niche leaderboard answers both questions more
  // honestly. The BE no longer has a mirror routing matrix (purged
  // L1.5 audit follow-up — server-side dispatch happens via
  // ``answer_session.select_builder_for_turn``); this map is the
  // single source of truth. Historical sessions still render via
  // lifecycle for stored ``mode="hook_fatigue" | "subniche"``.
  subniche_breakdown: "answer:pattern",
  format_lifecycle_optimize: "answer:lifecycle",
  fatigue: "answer:pattern",
  brief_generation: "answer:ideas",
  hook_variants: "answer:ideas",
  timing: "answer:timing",
  // Updated 2026-04-22: content_calendar routes to timing (not pattern)
  // so the expanded TimingPayload.calendar_slots renders instead of a
  // force-fit pattern report.
  content_calendar: "answer:timing",
  // Diagnostic template (2026-04-22) — URL-less flop diagnosis with a
  // 4-level verdict enum. See `artifacts/docs/report-template-prd-diagnostic.md`.
  own_flop_no_url: "answer:diagnostic",
  // Compare flow (Wave 4 PR #2, 2026-05-12) — two TikTok URLs → side-by-
  // side diagnosis. Top-level destination (mirrors ``video``); render
  // target /app/compare lands in PR #3 with the CompareBody component.
  compare_videos: "compare",
  follow_up_unclassifiable: "answer:generic",
};

/** Subjects the Gemini classifier may emit alongside `follow_up_classifiable`.
 * Canonical source — the BE had a mirror ``FollowUpSubject`` Literal
 * until L1.5 audit follow-up (purged with the destination helpers it
 * served). The Gemini classifier prompt enumerates these subjects;
 * server-side normalisation accepts whatever Gemini returns and the
 * answer-session dispatcher reads ``session.intent_type`` directly.
 * Extended 2026-05-07 with `lifecycle` + `diagnostic` so follow-ups that
 * belong on those shelves are routed there instead of being downgraded to
 * `answer:generic` just because the classifier vocabulary was narrower. */
export type FollowUpSubject =
  | "pattern"
  | "ideas"
  | "timing"
  | "lifecycle"
  | "diagnostic";

export type ClassifiedIntent =
  | { id: FixedIntentId }
  | { id: "follow_up_classifiable"; subject: FollowUpSubject };

export function resolveDestination(intent: ClassifiedIntent): Destination {
  if (intent.id === "follow_up_classifiable") {
    return `answer:${intent.subject}` as const;
  }
  return INTENT_DESTINATIONS[intent.id];
}

// TikTok URL regex shared across every URL branch below. Matches
// www.tiktok.com, tiktok.com, and the short-link subdomains
// (vm/vt/m.tiktok.com). MUST stay in sync with the BE canonical pattern
// at ``cloud-run/getviews_pipeline/url_patterns.py:TIKTOK_URL_RE``.
// When TikTok publishes a new short-link subdomain, update both files
// together — drift here causes silent classify-vs-extract dead-ends.
const TIKTOK_URL_GLOBAL_RE = /https?:\/\/(?:(?:www\.)?tiktok\.com|(?:vm|vt|m)\.tiktok\.com)\/\S+/gi;

export function detectIntent(
  query: string,
  priorAssistant: boolean,
): IntentDecision {
  const q = query.trim();
  const ql = q.toLowerCase();

  // ── COMPARE VIDEOS (two-or-more TikTok URLs) ─────────────────────────────
  // Wave 4 PR #1 (2026-05-11). Must land BEFORE the single-URL branch
  // (which treats the first URL as video_diagnosis) and BEFORE the
  // flop-keyword own_flop branch (the URL gate there already skips
  // URL-bearing messages, but explicit ordering prevents a future
  // refactor from routing a two-URL "tại sao video A vs B flop" query
  // somewhere unexpected). Mirror of the server-side ≥2-URL branch in
  // ``classify_intent``.
  const tiktokUrlMatches = q.match(TIKTOK_URL_GLOBAL_RE) ?? [];
  if (tiktokUrlMatches.length >= 2) {
    return { intentType: "compare_videos", isFree: false, confidence: "high" };
  }

  // ``series_audit`` (multi-URL corpus-comparison) was dropped 2026-04-
  // 22. The Wave 4 PR #1 ``compare_videos`` branch above covers the
  // two-URL case with a real template; single-URL queries fall through
  // to the ``video_diagnosis`` branch below unchanged.

  // ── OWN CHANNEL / VIDEO FLOP (no TikTok URL) ─────────────────────────────
  // 2026-05-07: the flop-keyword branch widened with colloquial
  // Vietnamese expressions. The BE deterministic mirror in
  // ``cloud-run/getviews_pipeline/intents.py`` was purged L1.5 audit;
  // this regex is now the single source of truth — ``/stream``'s
  // null-intent fallback uses Gemini classification, not a regex.
  if (
    !/https?:\/\/[^\s]*tiktok\.com/i.test(q)
    && (
      /\b(video|kênh|channel)\s+(của\s+)?(mình|tôi|tao|tui)\b/i.test(ql)
      || /\b(kênh|channel)\s+(mình|tôi)\b/i.test(ql)
      || /\b(my|kênh mình)\s+(video|channel)\b/i.test(ql)
    )
    && /\b(flop|ít view|kém view|không lên|không có view|không ai xem|low view|dead|underperform|chết|bết|ra gì đâu)\b/i.test(ql)
  ) {
    return { intentType: "own_flop_no_url", isFree: false, confidence: "medium" };
  }

  // ── 0. BARE AWEME-ID (structural — EvidenceThumbs tile navigation) ─────────
  // IdeaBlock passes the raw aweme_id (15-20 digits) via prefillUrl; no URL
  // is present. build_video_report accepts bare ids and routes them through
  // the corpus video_id lookup. Must precede the URL branch.
  if (/^\d{15,20}$/.test(q)) {
    return { intentType: "video_diagnosis", isFree: false, confidence: "high" };
  }

  // ── 1. URL DETECTION (highest confidence — structural) ────────────────────
  // L1.5 audit — METADATA_ONLY removed. Pre-migration it routed to a
  // dedicated /app/video corpus-row preview that genuinely skipped Gemini;
  // post-migration it fell through to the generic-fallback path which DOES
  // call Gemini, so the no-cost framing was broken silently. Stats-only
  // queries with a profile URL now route through competitor_profile (a
  // Gemini-backed channel report) — same effective cost, honest labelling.
  if (/https?:\/\/[^\s]*tiktok\.com/i.test(q)) {
    const hasTiktokProfileUrl = /tiktok\.com\/@[^\s/]+(?:\/(?!video|photo)[^\s]*)?(?:\s|$)/i.test(q)
      && !/\/video\//i.test(q)
      && !/\/photo\//i.test(q);
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
    // ``comparison`` (multi-handle head-to-head) was dropped 2026-04-22.
    // Two @-handles with "so sánh" keywords now classify as a
    // competitor_profile on the first handle; users can open the second
    // via the Channel screen separately.
    return ownChannelHandle
      ? { intentType: "own_channel", isFree: false, confidence: "high" }
      : { intentType: "competitor_profile", isFree: false, confidence: "high" };
  }

  // ── 3. SHOT LIST / SCRIPT WRITING ─────────────────────────────────────────
  // Covers both "what to shoot" (classic shot-list) and "write content" queries
  // ('viết hook', 'viết script', 'ý tưởng nội dung') — all map to the script
  // turn kind on the backend so follow-ups get script-style output.
  if (/shot list|kịch bản|cách quay|hướng dẫn quay|quay như nào|quay thế nào|quay video|lên ý tưởng quay|plan quay|danh sách cảnh|cảnh quay|viết hook|viết script|tạo script|ý tưởng nội dung/i.test(ql)) {
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
  // Match "đăng giờ nào" even when filler words ("TikTok", "video", niche names)
  // sit between the verb and the temporal question, and the reversed form. Keeps
  // the standalone phrases ("khung giờ vàng", "best time to post") so pure-timing
  // queries without a "post" verb still classify correctly.
  //
  // Also match "thời điểm đăng nào tốt…" / "đăng nào tốt nhất…" — common follow-ups
  // after a pattern report; older patterns required the substring "giờ nào", which
  // these phrasings omit, so they fell through to generic / follow_up_unclassifiable.
  if (
    /(đăng|post).{0,40}giờ nào/i.test(ql)
    || /giờ nào.{0,40}(đăng|post)/i.test(ql)
    || /thời điểm.{0,40}(đăng|post)/i.test(ql)
    || /(đăng|post)\s+nào tốt/i.test(ql)
    || /giờ nào tốt|thứ mấy tốt|best time to post|when to post|posting time|khung giờ vàng|lịch đăng/i.test(ql)
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

  // ── 6. KIỂU QUAY / FORMAT (before broad isTrend — "đang lên" alone trends) ─
  // Studio Home chip: "Kiểu quay (POV…) nào đang lên view…" must hit
  // content_directions (30d ER + direction synthesis), not trend_spike.
  if (/kiểu quay|dòng format|format quay/i.test(ql)) {
    return { intentType: "content_directions", isFree: false, confidence: "medium" };
  }

  // ── 7. CONTENT_DIRECTIONS + TREND disambiguation ──────────────────────────
  const isTrend = /đang viral|video viral|viral rồi|xu hướng|đang lên|bùng nổ|đang nổ|gì đang chạy|trend|tuần này|7 ngày|gần đây|đang trending|mới nổi/i.test(ql)
    || /\b(trending|viral)\b/i.test(ql);

  const isContent = /nên quay gì|quay gì|làm gì|video gì|format nào|hook nào|kiểu video|đang chạy tốt|đang work|đang hiệu quả|hướng content|content direction|hướng nội dung|nên làm gì|nên làm video|ý tưởng video|gì đang hot|gợi ý nội dung|loại video/i.test(ql);

  if (isTrend) return { intentType: "trend_spike", isFree: true, confidence: "medium" };
  if (isContent) return { intentType: "content_directions", isFree: false, confidence: "medium" };

  // ── 8. DEFAULT (must match `INTENT_DESTINATIONS.follow_up_unclassifiable`) ─
  return {
    intentType: "follow_up_unclassifiable",
    isFree: true,
    confidence: priorAssistant ? "medium" : "low",
  };
}

/** POST `/answer/sessions` `format` — must match `AnswerSessionCreateBody` + DB check.
 *
 * ``lifecycle`` added 2026-04-22 (migration ``20260505000000_answer_sessions_
 * lifecycle_format.sql``). ``diagnostic`` added 2026-04-22 (migration
 * ``20260506000000_answer_sessions_diagnostic_format.sql``). */
export type AnswerSessionFormat =
  | "pattern"
  | "ideas"
  | "timing"
  | "generic"
  | "lifecycle"
  | "diagnostic"
  | "video"
  | "script";

/**
 * Studio → `/app/answer` entry: map `detectIntent` to either a non-answer redirect
 * (video / channel / script / compare) or `{ format, intent_type }` for answer sessions.
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

  if (dest === "compare") {
    // Wave 4 PR #2 — pull the first two TikTok URLs (mirror of the
    // server-side ≥2-URL classification) and pass both as query params.
    const matches = trimmed.match(TIKTOK_URL_GLOBAL_RE) ?? [];
    const a = matches[0];
    const b = matches[1];
    if (a && b) {
      return {
        kind: "redirect",
        to: `/app/compare?url_a=${encodeURIComponent(a)}&url_b=${encodeURIComponent(b)}`,
      };
    }
    // Defensive — should never happen because detectIntent only returns
    // compare_videos when ≥ 2 URLs are present, but if the routing path
    // gets called with just one URL we fall back to the single-URL
    // video diagnosis session rather than a half-baked compare URL.
    return { kind: "session", format: "video", intent_type: "video_diagnosis" };
  }
  if (dest === "channel") {
    const handleMatch = trimmed.match(/@([\w.]+)/);
    const to = handleMatch
      ? `/app/channel?handle=${encodeURIComponent(handleMatch[1])}`
      : "/app/channel";
    return { kind: "redirect", to };
  }
  const format: AnswerSessionFormat =
    dest === "answer:pattern"
      ? "pattern"
      : dest === "answer:ideas"
        ? "ideas"
        : dest === "answer:timing"
          ? "timing"
          : dest === "answer:lifecycle"
            ? "lifecycle"
            : dest === "answer:diagnostic"
              ? "diagnostic"
              : dest === "answer:video"
                ? "video"
                : dest === "answer:script"
                  ? "script"
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
  if (intentType === "creator_search") return "creators";
  if (intentType === "shot_list") return "script";
  return "generic";
}
