import { describe, expect, it } from "vitest";

import { scriptLineStartSec, sortScriptBulletsByTimestamp } from "./nextVideoScript";

describe("scriptLineStartSec", () => {
  it.each([
    ["• Hook (0-1s): câu mở", 0],
    ["• Beat 2 (4s-8s): demo", 4],
    ["• Beat 1 (1.5–4s): cận sản phẩm", 1.5],
    ["• Beat 1 (2,5-4s): cận sản phẩm", 2.5],
  ])("parses %s → %d", (line, t) => {
    expect(scriptLineStartSec(line)).toBe(t);
  });

  it("returns null without a timestamp range", () => {
    expect(scriptLineStartSec("• CTA: comment 'giá'")).toBeNull();
    expect(scriptLineStartSec("• Hook 0-1s không ngoặc")).toBeNull();
  });
});

describe("sortScriptBulletsByTimestamp", () => {
  it("reorders shuffled timestamped bullets chronologically", () => {
    const text = [
      "• Beat 2 (8-12s): so sánh trước/sau",
      "• Hook (0-1s): câu hỏi đảo",
      "• Beat 1 (1-8s): demo cận",
      "• CTA: comment 'giá'",
    ].join("\n");
    expect(sortScriptBulletsByTimestamp(text).split("\n")).toEqual([
      "• Hook (0-1s): câu hỏi đảo",
      "• Beat 1 (1-8s): demo cận",
      "• Beat 2 (8-12s): so sánh trước/sau",
      "• CTA: comment 'giá'",
    ]);
  });

  it("keeps non-timestamped lines (CTA) in their original slot", () => {
    const text = [
      "Một câu dẫn.",
      "• Beat 1 (3-6s): demo",
      "• Hook (0-3s): mở bằng chuyển động",
      "• CTA: theo dõi kênh",
    ].join("\n");
    const out = sortScriptBulletsByTimestamp(text).split("\n");
    expect(out[0]).toBe("Một câu dẫn.");
    expect(out[1]).toBe("• Hook (0-3s): mở bằng chuyển động");
    expect(out[2]).toBe("• Beat 1 (3-6s): demo");
    expect(out[3]).toBe("• CTA: theo dõi kênh");
  });

  it("returns input unchanged when already ordered", () => {
    const text = "• Hook (0-1s): a\n• Beat 1 (1-4s): b";
    expect(sortScriptBulletsByTimestamp(text)).toBe(text);
  });

  it("returns input unchanged with fewer than 2 timestamped lines", () => {
    const text = "• Hook (0-1s): a\n• CTA: b";
    expect(sortScriptBulletsByTimestamp(text)).toBe(text);
  });
});
