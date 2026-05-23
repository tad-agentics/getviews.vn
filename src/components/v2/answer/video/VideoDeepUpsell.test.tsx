import React from "react";
import { describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach } from "vitest";

import { VideoDeepUpsell } from "./VideoDeepUpsell";

afterEach(cleanup);

describe("VideoDeepUpsell", () => {
  it("renders locked section teasers only (no upgrade button)", () => {
    render(
      <VideoDeepUpsell
        lockedSections={[
          { section_id: "sound", title_vi: "Âm thanh và nhịp điệu" },
          { section_id: "editing", title_vi: "Màu sắc và chữ trên hình" },
        ]}
      />,
    );

    expect(screen.getByText("Âm thanh và nhịp điệu")).toBeTruthy();
    expect(screen.getByText("Màu sắc và chữ trên hình")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Phân tích chuyên sâu (2 credit)" })).toBeNull();
  });

  it("renders nothing when locked list is empty", () => {
    const { container } = render(<VideoDeepUpsell lockedSections={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
