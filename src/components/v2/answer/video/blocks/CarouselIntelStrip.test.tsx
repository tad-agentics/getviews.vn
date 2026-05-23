import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CarouselIntelStrip } from "./CarouselIntelStrip";

describe("CarouselIntelStrip", () => {
  it("renders slide rows and carousel meta", () => {
    render(
      <CarouselIntelStrip
        intel={{
          content_arc: "list",
          swipe_trigger_type: "list_momentum",
          slides: [
            {
              index: 0,
              text_preview: "7 mẹo skincare",
              swipe_anchor: "numbered_progression",
              word_count: 4,
            },
            { index: 1, text_preview: "Bước 1", swipe_anchor: "incomplete_text" },
          ],
        }}
      />,
    );
    expect(screen.getByText(/Logic lướt · 2 slide/)).toBeTruthy();
    expect(screen.getByText(/7 mẹo skincare/)).toBeTruthy();
    expect(screen.getByText(/Danh sách/)).toBeTruthy();
  });
});
