import { describe, expect, it } from "vitest";

import {
  boostAttributionLabel,
  shouldShowBoostAttributionBlock,
} from "./boostAttributionLabels";

describe("boostAttributionLabels", () => {
  it("labels suspect_medium in Vietnamese", () => {
    expect(boostAttributionLabel("suspect_medium")).toMatch(/ads\/seeding/i);
  });

  it("shows block for suspect attribution or ineligible refs", () => {
    expect(shouldShowBoostAttributionBlock("organic_confident", true)).toBe(false);
    expect(shouldShowBoostAttributionBlock("suspect_low", true)).toBe(true);
    expect(shouldShowBoostAttributionBlock("organic_confident", false)).toBe(true);
  });
});
