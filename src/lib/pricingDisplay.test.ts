import { describe, expect, it } from "vitest";

import { planPricePresentation } from "./pricingDisplay";

describe("planPricePresentation", () => {
  it("shows monthly list price without strikethrough", () => {
    const p = planPricePresentation("Starter", "monthly");
    expect(p.mainPrice).toBe("249.000đ");
    expect(p.strikePrice).toBeNull();
    expect(p.billingLine).toMatch(/mỗi tháng/);
  });

  it("shows 6-month equivalent, total due, and savings vs monthly", () => {
    const p = planPricePresentation("Starter", "biannual");
    expect(p.mainPrice).toBe("199.000đ");
    expect(p.strikePrice).toBe("249.000đ");
    expect(p.billingLine).toBe("Thanh toán 1.194.000đ mỗi 6 tháng");
    expect(p.savingsLine).toMatch(/300\.000đ/);
  });

  it("differs Pro annual vs biannual per-month", () => {
    const six = planPricePresentation("Pro", "biannual");
    const year = planPricePresentation("Pro", "annual");
    expect(six.mainPrice).toBe("449.000đ");
    expect(year.mainPrice).toBe("399.000đ");
    expect(year.billingLine).toMatch(/4\.788\.000đ/);
  });
});
