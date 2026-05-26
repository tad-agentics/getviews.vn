import { describe, expect, it } from "vitest";

import {
  formatRitualHookTitle,
  formatRitualShotLabel,
  formatRitualWhyWorks,
} from "./ritualDisplay";

describe("ritualDisplay", () => {
  it("formatRitualHookTitle strips nested quotes", () => {
    expect(formatRitualHookTitle('"Hôm nay đi mua serum?"')).toBe(
      "Hôm nay đi mua serum?",
    );
    expect(formatRitualHookTitle('""double""')).toBe("double");
  });

  it("formatRitualWhyWorks drops English mechanism slug", () => {
    expect(
      formatRitualWhyWorks(
        "identification — viewer đặt mình vào tình huống thử nghiệm thực tế của creator",
      ),
    ).toBe("viewer đặt mình vào tình huống thử nghiệm thực tế của creator");
  });

  it("formatRitualShotLabel keeps shot lowercase", () => {
    expect(formatRitualShotLabel(4, 20)).toBe("KỊCH BẢN SẴN · 4 cảnh · 20s");
  });
});
