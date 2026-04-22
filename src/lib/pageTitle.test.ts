import { describe, expect, it } from "vitest";

import { pageMeta, pageTitle } from "./pageTitle";

describe("pageTitle", () => {
  it("appends the suffix to the GetViews base", () => {
    expect(pageTitle("Xu hướng")).toBe("Xu hướng — GetViews");
  });

  it("returns the bare base when no suffix is provided", () => {
    expect(pageTitle()).toBe("GetViews");
    expect(pageTitle(null)).toBe("GetViews");
    expect(pageTitle("")).toBe("GetViews");
    expect(pageTitle("   ")).toBe("GetViews");
  });
});

describe("pageMeta", () => {
  it("returns a one-entry array React Router's meta loader expects", () => {
    expect(pageMeta("Kênh tham chiếu")).toEqual([
      { title: "Kênh tham chiếu — GetViews" },
    ]);
  });
});
