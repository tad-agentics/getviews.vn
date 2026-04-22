import { describe, it, expect } from "vitest";
import { appendTurnKindForQuery, detectIntent, planAnswerEntry } from "./intent-router";

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

describe("detectIntent — own_flop_no_url (C.0)", () => {
  // ``series_audit`` dropped 2026-04-22 — multi-URL queries now
  // classify on their first URL (video_diagnosis).
  it("multiple TikTok URLs now classify via the first URL (video_diagnosis)", () => {
    const r = detectIntent(
      "https://www.tiktok.com/@a/video/1 https://www.tiktok.com/@b/video/2 so sánh",
      false,
    );
    expect(r.intentType).toBe("video_diagnosis");
  });

  it("own channel flop without URL → own_flop_no_url", () => {
    const r = detectIntent("Video kênh của mình flop quá không lên view", false);
    expect(r.intentType).toBe("own_flop_no_url");
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

  it("TikTok URL → redirect to /app/video", () => {
    const p = planAnswerEntry("https://www.tiktok.com/@x/video/123", false);
    expect(p.kind).toBe("redirect");
    if (p.kind === "redirect") {
      expect(p.to).toContain("/app/video");
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

  it("fatigue → lifecycle format", () => {
    const p = planAnswerEntry("Pattern này có đang chết dần không", false);
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("lifecycle");
      expect(p.intent_type).toBe("fatigue");
    }
  });

  it("subniche_breakdown → lifecycle format", () => {
    const p = planAnswerEntry("Ngách con nào đang nổi trong skincare", false);
    expect(p.kind).toBe("session");
    if (p.kind === "session") {
      expect(p.format).toBe("lifecycle");
      expect(p.intent_type).toBe("subniche_breakdown");
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

  it("default → generic kind", () => {
    expect(appendTurnKindForQuery("Giải thích thêm giúp mình", true)).toBe("generic");
  });
});
