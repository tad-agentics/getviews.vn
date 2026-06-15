import { describe, expect, it } from "vitest";

import { humanizeStatsProse, splitVerdictProse } from "./humanizeStatsProse";

describe("humanizeStatsProse", () => {
  it("replaces median and p75 in win diagnosis copy with creator language", () => {
    const raw =
      "Video của bạn là một cú hit thực sự với 3.460.332 view, gấp hơn 688 lần so với median 5.028 view của kênh. " +
      "Tỷ lệ tương tác 3,5% là con số rất ấn tượng, vượt ngưỡng 1,6% của p75 trong ngách thời trang nam.";
    const out = humanizeStatsProse(raw);
    expect(out).toContain("mức view thường trên kênh (khoảng 5.028 lượt xem)");
    expect(out).not.toMatch(/\bmedian\b/i);
    expect(out).not.toMatch(/trung vị/i);
    expect(out).toContain("mức cao trong ngách (top 25%)");
    expect(out).not.toMatch(/\bp75\b/i);
  });

  it("compacts raw view counts in prose", () => {
    expect(humanizeStatsProse("Video @a đạt 27.461 view trong tuần.")).toContain("27.5K view");
  });

  it("replaces signal jargon and raw enum codes in diagnosis copy", () => {
    const raw =
      "Thiếu neo giá trị (price anchor) khiến hook curiosity_gap yếu. " +
      "Persona thiếu negative markers trong transcript.";
    const out = humanizeStatsProse(raw);
    expect(out.toLowerCase()).not.toContain("price anchor");
    expect(out.toLowerCase()).not.toContain("negative markers");
    expect(out.toLowerCase()).not.toContain("curiosity_gap");
    expect(out.toLowerCase()).not.toContain("transcript");
    expect(out.toLowerCase()).toContain("neo giá");
    expect(out.toLowerCase()).toContain("dấu hiệu tiêu cực");
    expect(out.toLowerCase()).toContain("tạo khoảng trống tò mò");
    expect(out.toLowerCase()).toContain("lời thoại");
  });

  it("replaces completion rate and collapses duplicate ngắt nhịp", () => {
    const out = humanizeStatsProse(
      "Thiếu ngắt nhịp (pattern interrupt) ở giây 5 — completion rate thấp hơn chuẩn.",
    );
    expect(out.toLowerCase()).not.toContain("completion rate");
    expect(out.toLowerCase()).not.toContain("pattern interrupt");
    expect(out.toLowerCase()).toContain("tỷ lệ xem hết");
    expect(out).toBe("Thiếu ngắt nhịp ở giây 5 — tỷ lệ xem hết thấp hơn chuẩn.");
  });

  it("collapses duplicated góc nhìn POV label from cached BE prose", () => {
    const out = humanizeStatsProse(
      "Hook góc nhìn góc nhìn POV hiện tại tạo cảm giác chân thật.",
    );
    expect(out).toBe("Hook góc nhìn POV hiện tại tạo cảm giác chân thật.");
  });
});

describe("splitVerdictProse", () => {
  it("puts unformatted single-paragraph text in support so UI can render prose", () => {
    const body = "Hook yếu nên retention tụt sau 3 giây.";
    expect(splitVerdictProse(body)).toEqual({
      verdict: "",
      support: body,
    });
  });

  it("splits bold verdict from trailing support", () => {
    const body = "**Hook chưa neo.** Retention tụt 40% ở giây 3.";
    expect(splitVerdictProse(body)).toEqual({
      verdict: "Hook chưa neo.",
      support: "Retention tụt 40% ở giây 3.",
    });
  });

  it("uses first paragraph as verdict when body has blank-line breaks", () => {
    const body = "Kết luận ngắn.\n\nChi tiết thêm một câu.";
    expect(splitVerdictProse(body)).toEqual({
      verdict: "Kết luận ngắn.",
      support: "Chi tiết thêm một câu.",
    });
  });
});

describe("humanizeStatsProse gap titles", () => {
  it("preserves **bold** gap titles when humanizing dead air jargon inside markers", () => {
    const raw = "Với **Dead air giữa clip**:\n\nClip @struct — tránh dead air.";
    const out = humanizeStatsProse(raw);
    expect(out).toContain("**khoảng lặng giữa clip**");
    expect(out).not.toContain("****");
  });
});
