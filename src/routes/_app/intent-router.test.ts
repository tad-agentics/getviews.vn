import { describe, it, expect } from "vitest";
import {
  appendTurnKindForQuery,
  detectIntent,
  planAnswerEntry,
  resolveDestination,
} from "./intent-router";

/**
 * Regression guard for the "Soi kênh đối thủ @handle" routing bug.
 *
 * Old behaviour: the "Soi Kênh Đối Thủ" card produced
 *   "Soi kênh đối thủ @phuong.nga.beauty — phân tích công thức content..."
 * and the `soi kênh` keyword short-circuited to own_channel even though
 * the query clearly names a competitor. Sellers saw "đánh giá kênh của
 * bạn" style output when they wanted competitor teardown.
 *
 * Fix: own_channel requires an explicit self-reference pronoun, AND
 * "đối thủ / competitor" short-circuits to competitor_profile.
 */

describe("detectIntent — handle + 'Soi kênh đối thủ' regression", () => {
  it("competitor_profile when @handle paired with 'đối thủ'", () => {
    const r = detectIntent(
      "Soi kênh đối thủ @phuong.nga.beauty — phân tích công thức content, hook, format của họ",
      false,
    );
    expect(r.intentType).toBe("competitor_profile");
    expect(r.confidence).toBe("high");
  });

  it("competitor_profile when @handle with no self-reference", () => {
    const r = detectIntent("Soi kênh @testuser", false);
    expect(r.intentType).toBe("competitor_profile");
  });

  it("own_channel when @handle paired with 'của mình'", () => {
    const r = detectIntent("Soi kênh của mình @my.handle", false);
    expect(r.intentType).toBe("own_channel");
  });

  it("own_channel when @handle paired with 'của tôi'", () => {
    const r = detectIntent("Xem kênh của tôi @me.handle thế nào", false);
    expect(r.intentType).toBe("own_channel");
  });

  it("competitor_profile when @handle + 'competitor' (English)", () => {
    const r = detectIntent("Analyze competitor @someone", false);
    expect(r.intentType).toBe("competitor_profile");
  });

  it("competitor_profile for bare '@handle' with no kênh keyword", () => {
    const r = detectIntent("@someone.handle", false);
    expect(r.intentType).toBe("competitor_profile");
  });
});

describe("detectIntent — own_channel without a handle requires self-reference", () => {
  it("falls through to follow_up_unclassifiable on bare 'Soi kênh' (ambiguous)", () => {
    const r = detectIntent("Soi kênh", false);
    expect(r.intentType).toBe("follow_up_unclassifiable");
  });

  it("own_channel on 'Soi kênh của mình'", () => {
    const r = detectIntent("Soi kênh của mình đi", false);
    expect(r.intentType).toBe("own_channel");
  });

  it("own_channel on 'Phân tích kênh của tôi'", () => {
    const r = detectIntent("Phân tích kênh của tôi tuần này", false);
    expect(r.intentType).toBe("own_channel");
  });

  it("follow_up_unclassifiable on 'Phân tích kênh' without self-reference", () => {
    const r = detectIntent("Phân tích kênh này xem sao", false);
    expect(r.intentType).toBe("follow_up_unclassifiable");
  });
});

describe("detectIntent — bare aweme_id (EvidenceThumbs tile)", () => {
  it("video_diagnosis on bare 19-digit aweme_id", () => {
    const r = detectIntent("7398542123456789012", false);
    expect(r.intentType).toBe("video_diagnosis");
    expect(r.confidence).toBe("high");
  });

  it("video_diagnosis on 15-digit aweme_id (lower bound)", () => {
    const r = detectIntent("739854212345678", false);
    expect(r.intentType).toBe("video_diagnosis");
  });

  it("does NOT match a short numeric string (not an aweme_id)", () => {
    const r = detectIntent("12345", false);
    expect(r.intentType).not.toBe("video_diagnosis");
  });
});

describe("detectIntent — URL branches unchanged", () => {
  it("video_diagnosis on tiktok video URL", () => {
    const r = detectIntent(
      "Phân tích video này https://www.tiktok.com/@abc/video/123",
      false,
    );
    expect(r.intentType).toBe("video_diagnosis");
  });

  it("competitor_profile on tiktok profile URL", () => {
    const r = detectIntent(
      "Soi kênh https://www.tiktok.com/@someone",
      false,
    );
    expect(r.intentType).toBe("competitor_profile");
  });
});

describe("detectIntent — non-handle branches still work", () => {
  it("shot_list on 'kịch bản'", () => {
    const r = detectIntent("Lên kịch bản cho video review son mới", false);
    expect(r.intentType).toBe("shot_list");
  });

  it("creator_search on 'tìm KOL'", () => {
    const r = detectIntent("Tìm KOL skincare cho da dầu mụn", false);
    expect(r.intentType).toBe("creator_search");
  });

  it("content_directions on 'hướng nội dung'", () => {
    const r = detectIntent("Hướng nội dung skincare đang chạy tốt", false);
    expect(r.intentType).toBe("content_directions");
  });

  it("trend_spike on 'xu hướng tuần này'", () => {
    const r = detectIntent("Xu hướng TikTok đang hot tuần này", false);
    expect(r.intentType).toBe("trend_spike");
  });

  it("content_directions on Studio Home 'kiểu quay … đang lên view' (before trend)", () => {
    const r = detectIntent(
      "Kiểu quay (POV, lồng tiếng, list, storytime…) nào đang lên view nhanh trong Gym?",
      false,
    );
    expect(r.intentType).toBe("content_directions");
  });

  it("trend_spike on 'chủ đề và góc kể … tuần này' chip", () => {
    const r = detectIntent("Chủ đề và góc kể nào đang hot trong Gym tuần này?", false);
    expect(r.intentType).toBe("trend_spike");
  });

  it("follow_up_unclassifiable on open-ended chat with prior context", () => {
    const r = detectIntent("Tại sao vậy nhỉ?", true);
    expect(r.intentType).toBe("follow_up_unclassifiable");
    expect(r.confidence).toBe("medium");
  });

  it("follow_up_unclassifiable low-confidence without prior context", () => {
    const r = detectIntent("Chào bạn", false);
    expect(r.intentType).toBe("follow_up_unclassifiable");
    expect(r.confidence).toBe("low");
  });
});

describe("Studio Home — legacy quick-start prompts (detectIntent for Answer follow-up)", () => {
  const niche = "Gym / Fitness";

  it("trend_spike", () => {
    expect(
      detectIntent(
        `Xu hướng và chủ đề nào đang nổi trong ngách ${niche} tuần này?`,
        false,
      ).intentType,
    ).toBe("trend_spike");
  });

  it("content_directions", () => {
    expect(
      detectIntent(
        `Hướng nội dung và format nào đang chạy tốt nhất trong ngách ${niche}?`,
        false,
      ).intentType,
    ).toBe("content_directions");
  });

  it("subniche_breakdown", () => {
    expect(
      detectIntent(
        `Trong ngách ${niche}, ngách con nào đáng khai thác hoặc mở rộng thêm?`,
        false,
      ).intentType,
    ).toBe("subniche_breakdown");
  });

  it("timing", () => {
    expect(
      detectIntent(
        "Nên đăng TikTok khung giờ nào trong tuần để tối ưu reach?",
        false,
      ).intentType,
    ).toBe("timing");
  });

  it("brief_generation", () => {
    expect(
      detectIntent(`Viết brief sản xuất nội dung tuần này cho ngách ${niche}.`, false)
        .intentType,
    ).toBe("brief_generation");
  });

  it("own_flop_no_url", () => {
    expect(
      detectIntent("Video của mình flop — phân tích nguyên nhân và nên chỉnh gì?", false)
        .intentType,
    ).toBe("own_flop_no_url");
  });

  it("own_channel", () => {
    expect(
      detectIntent(
        "Soi kênh của mình — tổng quan hook, format và gợi ý cải thiện.",
        false,
      ).intentType,
    ).toBe("own_channel");
  });
});

describe("detectIntent — own_flop_no_url (C.0)", () => {
  // ``series_audit`` dropped 2026-04-22 — multi-URL queries now fire
  // ``compare_videos`` instead (Wave 4 PR #1). Full coverage for the
  // two-URL branch lives in its own describe block further down; the
  // pin here just guards against a multi-URL query accidentally
  // falling through to VIDEO_DIAGNOSIS (which would drop the 2nd URL).
  it("multiple TikTok URLs fire compare_videos (Wave 4 PR #1)", () => {
    const r = detectIntent(
      "https://www.tiktok.com/@a/video/1 https://www.tiktok.com/@b/video/2 so sánh",
      false,
    );
    expect(r.intentType).toBe("compare_videos");
  });

  it("own channel flop without URL → own_flop_no_url", () => {
    const r = detectIntent("Video kênh của mình flop quá không lên view", false);
    expect(r.intentType).toBe("own_flop_no_url");
  });

  // 2026-05-07 — widened the colloquial flop-keyword coverage. Each
  // added phrase must fire the own_flop branch when paired with a
  // "my video / channel" keyword. Kept narrow to avoid false positives
  // against niche-level trend complaints.
  it("fires on 'không ai xem'", () => {
    const r = detectIntent("Video kênh của mình không ai xem", false);
    expect(r.intentType).toBe("own_flop_no_url");
  });

  it("fires on 'không có view'", () => {
    const r = detectIntent("Kênh của mình không có view", false);
    expect(r.intentType).toBe("own_flop_no_url");
  });

  it("fires on 'ra gì đâu'", () => {
    const r = detectIntent("Video kênh của mình ra gì đâu", false);
    expect(r.intentType).toBe("own_flop_no_url");
  });

  it("fires on 'bết'", () => {
    const r = detectIntent("Kênh của tôi bết quá", false);
    expect(r.intentType).toBe("own_flop_no_url");
  });

  it("fires on 'kém view'", () => {
    const r = detectIntent("Video của mình kém view", false);
    expect(r.intentType).toBe("own_flop_no_url");
  });

  it("does NOT fire on niche-level complaint without self-reference", () => {
    // The outer "my video / channel" gate is what makes these phrases
    // safe additions. Without it, the same complaint about a niche
    // should stay in the follow-up fallback.
    const r = detectIntent("Ngách này bết quá không ai xem", false);
    expect(r.intentType).not.toBe("own_flop_no_url");
  });
});

describe("planAnswerEntry — /answer session vs redirect", () => {
  it("timing query → session format timing + intent timing", () => {
    const p = planAnswerEntry("Nên đăng TikTok giờ nào trong tuần?", false);
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("timing");
      expect(p.intent_type).toBe("timing");
    }
  });

  it("shot_list → script session (answer composer)", () => {
    const p = planAnswerEntry("Viết kịch bản 30s review son", false);
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("script");
      expect(p.intent_type).toBe("shot_list");
    }
  });

  it("brief_generation → ideas format", () => {
    const p = planAnswerEntry("Viết brief tuần này cho kênh skincare", false);
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("ideas");
      expect(p.intent_type).toBe("brief_generation");
    }
  });

  it("trend_spike → pattern format", () => {
    const p = planAnswerEntry("Xu hướng TikTok đang hot tuần này", false);
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("pattern");
      expect(p.intent_type).toBe("trend_spike");
    }
  });

  it("content_directions → pattern format (kiểu quay chip)", () => {
    const p = planAnswerEntry(
      "Kiểu quay nào đang lên view nhanh trong Gym / Fitness?",
      false,
    );
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("pattern");
      expect(p.intent_type).toBe("content_directions");
    }
  });

  it("TikTok URL → video session (lands on /app/answer with format=video)", () => {
    // PR-3 of the video-as-template migration: composer URL pastes
    // stay on /app/answer instead of redirecting to the deleted
    // /app/video screen. The session's ``initial_q`` carries the URL
    // verbatim; the BE ``build_video_report`` extracts it back out
    // and runs the existing /video/analyze pipeline.
    const p = planAnswerEntry("https://www.tiktok.com/@x/video/123", false);
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("video");
      expect(p.intent_type).toBe("video_diagnosis");
    }
  });

  it("unclassified query → generic session + follow_up_unclassifiable (aligned with INTENT_DESTINATIONS)", () => {
    const p = planAnswerEntry("Chào bạn, cho mình hỏi chút", false);
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("generic");
      expect(p.intent_type).toBe("follow_up_unclassifiable");
    }
  });

  // Lifecycle template — routes the 3 intents previously force-fit into
  // pattern. Migration 20260505000000 extends the DB CHECK constraint.
  it("format_lifecycle_optimize → lifecycle format", () => {
    const p = planAnswerEntry("30s vs 60s video nào hiệu quả hơn", false);
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("lifecycle");
      expect(p.intent_type).toBe("format_lifecycle_optimize");
    }
  });

  // 2026-05-08 — ``fatigue`` + ``subniche_breakdown`` moved off the
  // lifecycle shelf (fixture-with-disclaimer cells were misleading).
  // They now route to Pattern's niche-hook-leaderboard which is a more
  // honest fit for "what's rising/declining in my niche?" until we
  // build a real hook-timeseries + subniche-taxonomy signal.
  it("fatigue → pattern format (redirected off lifecycle fixture)", () => {
    const p = planAnswerEntry("Pattern này có đang chết dần không", false);
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("pattern");
      expect(p.intent_type).toBe("fatigue");
    }
  });

  it("subniche_breakdown → pattern format (redirected off lifecycle fixture)", () => {
    const p = planAnswerEntry("Ngách con nào đang nổi trong skincare", false);
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("pattern");
      expect(p.intent_type).toBe("subniche_breakdown");
    }
  });

  it("own_channel → /app/channel with handle when @ present", () => {
    const p = planAnswerEntry("Soi kênh @myhandle — tổng quan hook.", false);
    expect(p.kind).toBe("redirect");
    if (p.kind === "redirect") {
      expect(p.to).toBe("/app/channel?handle=myhandle");
    }
  });

  it("own_channel with depth=deep → /app/channel?depth=deep", () => {
    const p = planAnswerEntry("Soi kênh @rival — audit brief.", false, "deep");
    expect(p.kind).toBe("redirect");
    if (p.kind === "redirect") {
      expect(p.to).toBe("/app/channel?handle=rival&depth=deep");
    }
  });

  it("own_channel without handle → /app/channel", () => {
    const p = planAnswerEntry(
      "Soi kênh của mình — tổng quan hook, format và gợi ý cải thiện.",
      false,
    );
    expect(p.kind).toBe("redirect");
    if (p.kind === "redirect") {
      expect(p.to).toBe("/app/channel");
    }
  });

  // Diagnostic template — routes own_flop_no_url off of the pattern
  // template so URL-less flop questions get a verdict-based diagnosis
  // rather than a niche hook leaderboard.
  it("own_flop_no_url → diagnostic format", () => {
    const p = planAnswerEntry(
      "Video kênh của mình flop quá không lên view",
      false,
    );
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("diagnostic");
      expect(p.intent_type).toBe("own_flop_no_url");
    }
  });
});

describe("appendTurnKindForQuery", () => {
  it("timing intent → timing kind", () => {
    expect(appendTurnKindForQuery("Khung giờ vàng để post?", true)).toBe("timing");
  });

  it("creator_search → creators kind", () => {
    expect(appendTurnKindForQuery("Tìm KOL làm review son", true)).toBe("creators");
  });

  it("pattern-style timing follow-up → timing kind (thời điểm / đăng nào tốt)", () => {
    expect(
      appendTurnKindForQuery("Thời điểm đăng nào tốt nhất cho các hook này?", true),
    ).toBe("timing");
  });

  it("default → generic kind", () => {
    expect(appendTurnKindForQuery("Giải thích thêm giúp mình", true)).toBe("generic");
  });
});

describe("resolveDestination — follow_up_classifiable subject union", () => {
  // The Gemini classifier can tag a follow-up with a subject family so
  // it lands on the right answer template. The union was historically
  // capped at pattern/ideas/timing; 2026-05-07 extended it with the two
  // new shelves (lifecycle + diagnostic) so follow-ups on those session
  // shapes can be routed back to the same shelf instead of being
  // downgraded to answer:generic.

  it("fixed intent → its INTENT_DESTINATIONS entry", () => {
    expect(resolveDestination({ id: "trend_spike" })).toBe("answer:pattern");
    expect(resolveDestination({ id: "timing" })).toBe("answer:timing");
    expect(resolveDestination({ id: "shot_list" })).toBe("answer:script");
    // ``format_lifecycle_optimize`` is the only intent still on the
    // lifecycle shelf post-2026-05-08 (fatigue + subniche_breakdown
    // moved to pattern). This case is the canary: if anyone re-adds a
    // fixture-cell-backed intent back onto lifecycle, the test would
    // need an explicit update.
    expect(resolveDestination({ id: "format_lifecycle_optimize" })).toBe("answer:lifecycle");
    expect(resolveDestination({ id: "fatigue" })).toBe("answer:pattern");
    expect(resolveDestination({ id: "subniche_breakdown" })).toBe("answer:pattern");
    expect(resolveDestination({ id: "own_flop_no_url" })).toBe("answer:diagnostic");
  });

  it("follow_up_classifiable + each original subject resolves correctly", () => {
    expect(
      resolveDestination({ id: "follow_up_classifiable", subject: "pattern" }),
    ).toBe("answer:pattern");
    expect(
      resolveDestination({ id: "follow_up_classifiable", subject: "ideas" }),
    ).toBe("answer:ideas");
    expect(
      resolveDestination({ id: "follow_up_classifiable", subject: "timing" }),
    ).toBe("answer:timing");
  });

  it("follow_up_classifiable + lifecycle subject routes to answer:lifecycle", () => {
    expect(
      resolveDestination({
        id: "follow_up_classifiable",
        subject: "lifecycle",
      }),
    ).toBe("answer:lifecycle");
  });

  it("follow_up_classifiable + diagnostic subject routes to answer:diagnostic", () => {
    expect(
      resolveDestination({
        id: "follow_up_classifiable",
        subject: "diagnostic",
      }),
    ).toBe("answer:diagnostic");
  });
});

// ── compare_videos routing ───────────────────────────────────────────────
//
// Two TikTok URLs in one message → `compare_videos` intent → top-level
// `compare` destination → a first-class `compare` answer-session (both URLs
// ride in `initial_q`; the Cloud Run turn handler extracts + resolves them).
// Mirrors the server-side classification in `classify_intent` (see
// `test_intent_routing.py`). The two routers must agree on the boundary.

describe("detectIntent — compare_videos (≥ 2 TikTok URLs)", () => {
  const URL_A = "https://www.tiktok.com/@a/video/1";
  const URL_B = "https://www.tiktok.com/@b/video/2";
  const URL_C = "https://www.tiktok.com/@c/video/3";

  it("fires compare_videos when two TikTok URLs are present", () => {
    const r = detectIntent(`${URL_A} ${URL_B}`, false);
    expect(r.intentType).toBe("compare_videos");
    expect(r.confidence).toBe("high");
    expect(r.isFree).toBe(false);
  });

  it("fires compare_videos even with analysis keywords between URLs", () => {
    const r = detectIntent(
      `phân tích ${URL_A} vs ${URL_B} sai ở đâu`, false,
    );
    expect(r.intentType).toBe("compare_videos");
  });

  it("fires compare_videos for 3+ URLs (orchestrator caps; classifier doesn't)", () => {
    const r = detectIntent(`${URL_A} ${URL_B} ${URL_C}`, false);
    expect(r.intentType).toBe("compare_videos");
  });

  it("single URL still routes to video_diagnosis", () => {
    const r = detectIntent(`${URL_A} tại sao flop`, false);
    expect(r.intentType).toBe("video_diagnosis");
  });

  it("matches short-link domain (vm.tiktok.com) for both URLs", () => {
    const r = detectIntent(
      "https://vm.tiktok.com/abc https://vt.tiktok.com/xyz",
      false,
    );
    expect(r.intentType).toBe("compare_videos");
  });

  it("does NOT fire on a single URL + a non-tiktok URL", () => {
    const r = detectIntent(
      `${URL_A} https://example.com/something`, false,
    );
    expect(r.intentType).toBe("video_diagnosis");
  });

  it("resolveDestination maps compare_videos → compare (top-level, not answer:*)", () => {
    expect(resolveDestination({ id: "compare_videos" })).toBe("compare");
  });

  it("planAnswerEntry blocks YouTube URL (no generic hallucination path)", () => {
    const result = planAnswerEntry("https://www.youtube.com/watch?v=abc", false);
    expect(result).toEqual({
      kind: "blocked",
      reason: "non_tiktok_url",
      message: expect.stringMatching(/link TikTok/i),
    });
  });

  it("planAnswerEntry opens a compare answer-session for two URLs", () => {
    const result = planAnswerEntry(`${URL_A} ${URL_B}`, false);
    expect(result.kind).toBe("session");
    if (result.kind !== "session") return;
    expect(result.format).toBe("compare");
    expect(result.intent_type).toBe("compare_videos");
  });

  it("planAnswerEntry falls back to video_diagnosis when only one URL is present", () => {
    const result = planAnswerEntry(`${URL_A} tại sao flop`, false);
    expect(result.kind).toBe("session");
    if (result.kind !== "session") return;
    expect(result.format).toBe("video");
    expect(result.intent_type).toBe("video_diagnosis");
  });
});

// ── AQ-3 — appendTurnKindForQuery keyword coverage ─────────────────────────
//
// Regression + gap-fill suite ensuring timing, script/ideas, and generic
// pass-through buckets each cover the Vietnamese phrasing variants a creator
// is likely to type as a follow-up. Prior gaps:
//   • "viết hook" / "viết script" / "tạo script" fell through to "generic"
//   • "ý tưởng nội dung" fell through to "generic"
//   • "viết lại hook" / "biến thể hook" (hook_variants) stay ``generic``
//     — A/B hook lines, not the 6-shot script template.
//
// Fixes applied in intent-router.ts:
//   1. shot_list regex extended with: viết hook, viết script, tạo script, ý tưởng nội dung
//   2. appendTurnKindForQuery: only shot_list → "script"

describe("appendTurnKindForQuery — timing keyword coverage (regression)", () => {
  it("'đăng giờ nào' → timing", () => {
    expect(appendTurnKindForQuery("nên đăng giờ nào cho TikTok beauty", true)).toBe("timing");
  });

  it("'khung giờ vàng' → timing", () => {
    expect(appendTurnKindForQuery("khung giờ vàng để post video", true)).toBe("timing");
  });

  it("'lịch đăng' → timing", () => {
    expect(appendTurnKindForQuery("lịch đăng tuần này nên như nào", true)).toBe("timing");
  });

  it("'thứ mấy tốt' → timing", () => {
    expect(appendTurnKindForQuery("thứ mấy tốt để post TikTok", true)).toBe("timing");
  });

  it("'best time to post' → timing", () => {
    expect(appendTurnKindForQuery("best time to post trong ngách review", true)).toBe("timing");
  });

  it("'thời điểm đăng' → timing", () => {
    expect(appendTurnKindForQuery("thời điểm đăng video nào tốt nhất", true)).toBe("timing");
  });
});

describe("appendTurnKindForQuery — script/ideas keyword coverage (gap-fill)", () => {
  it("'kịch bản' → script (regression)", () => {
    expect(appendTurnKindForQuery("kịch bản video tutorial trang điểm", true)).toBe("script");
  });

  it("'danh sách cảnh quay' → script (regression)", () => {
    expect(appendTurnKindForQuery("danh sách cảnh quay cho video review", true)).toBe("script");
  });

  it("'viết hook' → script (new coverage)", () => {
    expect(appendTurnKindForQuery("viết hook cho video beauty", true)).toBe("script");
  });

  it("'viết script' → script (new coverage)", () => {
    expect(appendTurnKindForQuery("viết script cho video 30 giây", true)).toBe("script");
  });

  it("'tạo script' → script (new coverage)", () => {
    expect(appendTurnKindForQuery("tạo script cho video unboxing", true)).toBe("script");
  });

  it("'ý tưởng nội dung' → script (new coverage)", () => {
    expect(appendTurnKindForQuery("ý tưởng nội dung cho ngách skincare", true)).toBe("script");
  });

  it("'viết lại hook' → generic (hook_variants — text variants, not 6-shot script)", () => {
    expect(appendTurnKindForQuery("viết lại hook cho video này", true)).toBe("generic");
  });

  it("'biến thể hook' → generic (hook_variants)", () => {
    expect(appendTurnKindForQuery("5 biến thể hook cho video beauty", true)).toBe("generic");
  });
});

describe("appendTurnKindForQuery — generic pass-through (correct non-routing)", () => {
  it("'giải thích thêm' → generic", () => {
    expect(appendTurnKindForQuery("giải thích thêm về pattern này", true)).toBe("generic");
  });

  it("'tại sao' open question → generic", () => {
    expect(appendTurnKindForQuery("tại sao hook này không work nhỉ", true)).toBe("generic");
  });

  it("'so sánh hai kiểu hook' → generic (no URLs, not a compare_videos)", () => {
    expect(appendTurnKindForQuery("so sánh hai kiểu hook này", true)).toBe("generic");
  });

  it("'cho mình biết thêm' → generic", () => {
    expect(appendTurnKindForQuery("cho mình biết thêm", true)).toBe("generic");
  });

  it("'cụ thể hơn' → generic", () => {
    expect(appendTurnKindForQuery("cụ thể hơn về video trên đi", true)).toBe("generic");
  });

  it("'ví dụ cụ thể' → generic", () => {
    expect(appendTurnKindForQuery("ví dụ cụ thể đi", true)).toBe("generic");
  });
});
