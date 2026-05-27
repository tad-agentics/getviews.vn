import { describe, expect, it } from "vitest";

import { humanizeStatsProse } from "./humanizeStatsProse";

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
});
