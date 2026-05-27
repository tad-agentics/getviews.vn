import { describe, expect, it } from "vitest";

import {
  CONTENT_FORMAT_FILTER_OPTIONS,
  contentFormatLabelVi,
} from "./contentFormatLabels";

describe("contentFormatLabelVi", () => {
  it("maps common corpus slugs to Vietnamese", () => {
    expect(contentFormatLabelVi("tutorial")).toBe("Hướng dẫn");
    expect(contentFormatLabelVi("talking_head")).toBe("Nói thẳng camera");
    expect(contentFormatLabelVi("review")).toBe("Đánh giá");
  });

  it("exposes Vietnamese labels on Explore format filters", () => {
    const labels = CONTENT_FORMAT_FILTER_OPTIONS.map((o) => o.label);
    expect(labels).not.toContain("Tutorial");
    expect(labels).toContain("Hướng dẫn");
  });
});
