import { describe, expect, it } from "vitest";
import { isV5Report } from "./v5-compat";

// ── isV5Report ──────────────────────────────────────────────────────────────

describe("isV5Report", () => {
  // 1. Definitive marker
  it("returns true when _schema_version is 'v5'", () => {
    expect(isV5Report({ _schema_version: "v5" })).toBe(true);
  });

  it("returns false when _schema_version is absent", () => {
    expect(isV5Report({})).toBe(false);
  });

  it("returns false when _schema_version is 'v4'", () => {
    expect(isV5Report({ _schema_version: "v4" })).toBe(false);
  });

  // 2. Structural: per_format_views
  it("returns true when channel_context.per_format_views is present", () => {
    expect(
      isV5Report({ channel_context: { per_format_views: { "Storytime": { avg: 1000 } } } }),
    ).toBe(true);
  });

  it("returns false when channel_context is present but per_format_views is falsy", () => {
    expect(isV5Report({ channel_context: { per_format_views: null } })).toBe(false);
    expect(isV5Report({ channel_context: {} })).toBe(false);
  });

  // 3. Structural: format_match
  it("returns true when creator_comparison.format_match is present", () => {
    expect(
      isV5Report({ creator_comparison: { format_match: { format_matches: true } } }),
    ).toBe(true);
  });

  it("returns false when creator_comparison exists but format_match is absent", () => {
    expect(isV5Report({ creator_comparison: { avg_views: 5000 } })).toBe(false);
  });

  // 4. Sentence-count + length fallback
  it("returns true for genuine 3-sentence v5 van_de_chinh (long, ≥2 clusters)", () => {
    // Realistic v5 lead: channel-first, metrics-backed, always > 100 chars
    const text =
      "Kênh @abc với 45 videos format Storytime trung bình đạt 180K views mỗi clip. " +
      "Video này dừng phân phối ở giây thứ 4 vì hook mở bằng câu hỏi thay vì tuyên bố. " +
      "Format Storytime của kênh chưa tối ưu ở đoạn dẫn nhập này.";
    expect(text.length).toBeGreaterThanOrEqual(100);
    expect(isV5Report({ narrative_vi: { van_de_chinh: text } })).toBe(true);
  });

  it("returns true for 3-sentence van_de_chinh with ellipsis (old === 3 false negative case)", () => {
    // Pre-fix: "..." grouped as 1 cluster → total = 2 ≠ 3 → false negative
    // Post-fix: 2 clusters + length ≥ 100 → true
    const text =
      "Kênh bạn có 2M views trên các video Storytime... tuy nhiên video này chỉ đạt 10K views. " +
      "Hook mất 3 giây đầu vì không có tuyên bố rõ ràng.";
    expect(text.length).toBeGreaterThanOrEqual(100);
    expect(isV5Report({ narrative_vi: { van_de_chinh: text } })).toBe(true);
  });

  it("returns false for v4 one-liner (short, < 100 chars)", () => {
    const text = "Video này có hook tốt.";
    expect(text.length).toBeLessThan(100);
    expect(isV5Report({ narrative_vi: { van_de_chinh: text } })).toBe(false);
  });

  it("returns false for short exclamatory string with 2 punctuation clusters (false positive fix)", () => {
    // "Tuyệt vời!!! Video rất tốt...." — the specific case the user reported.
    // 2 clusters (!!!, ....) satisfy ≥2 but length < 100 → correctly rejected.
    const text = "Tuyệt vời!!!  Video rất tốt....";
    expect(text.length).toBeLessThan(100);
    expect(isV5Report({ narrative_vi: { van_de_chinh: text } })).toBe(false);
  });

  it("returns false for single-sentence text with ellipsis (< 100 chars)", () => {
    // "Kênh có 2M views... tuy nhiên." — 2 clusters (... and .) but short → rejected.
    const text = "Kênh có 2M views... tuy nhiên.";
    expect(text.length).toBeLessThan(100);
    expect(isV5Report({ narrative_vi: { van_de_chinh: text } })).toBe(false);
  });

  it("returns false for empty van_de_chinh", () => {
    expect(isV5Report({ narrative_vi: { van_de_chinh: "" } })).toBe(false);
    expect(isV5Report({ narrative_vi: { van_de_chinh: null } })).toBe(false);
  });

  it("returns false when narrative_vi is absent", () => {
    expect(isV5Report({ narrative_vi: null })).toBe(false);
  });

  // 5. Priority: _schema_version wins before checking structural fields
  it("returns true via _schema_version even when structural fields are absent", () => {
    expect(isV5Report({ _schema_version: "v5", channel_context: null })).toBe(true);
  });
});
