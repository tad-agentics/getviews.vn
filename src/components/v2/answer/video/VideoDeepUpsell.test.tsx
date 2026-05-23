import React from "react";
import { describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach } from "vitest";

import { VideoDeepUpsell } from "./VideoDeepUpsell";

afterEach(cleanup);

describe("VideoDeepUpsell", () => {
  it("renders locked section teasers with manifest signal counts", () => {
    render(
      <VideoDeepUpsell
        lockedSections={[
          { section_id: "sound", title_vi: "Âm thanh và nhịp điệu", signal_count: 3 },
          { section_id: "editing", title_vi: "Màu sắc và chữ trên hình", signal_count: 1 },
        ]}
      />,
    );

    expect(screen.getByText("Âm thanh và nhịp điệu")).toBeTruthy();
    expect(screen.getByText("+3 nhận định")).toBeTruthy();
    expect(screen.getByText("+1 nhận định")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Phân tích chuyên sâu (2 credit)" })).toBeNull();
  });

  it("renders boost_attribution teaser copy on basic upsell", () => {
    render(
      <VideoDeepUpsell
        lockedSections={[
          {
            section_id: "boost_attribution",
            title_vi: "Có dấu hiệu ads/seeding",
            signal_count: 2,
            teaser_vi: "Kiểm tra phân phối bất thường và benchmark đã lọc outlier",
          },
        ]}
      />,
    );
    expect(screen.getByText(/Kiểm tra phân phối bất thường/)).toBeTruthy();
  });

  it("renders nothing when locked list is empty", () => {
    const { container } = render(<VideoDeepUpsell lockedSections={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
