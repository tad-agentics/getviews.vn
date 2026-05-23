import React from "react";
import { describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach } from "vitest";

import { VideoDeepUpsell } from "./VideoDeepUpsell";

afterEach(cleanup);

describe("VideoDeepUpsell", () => {
  it("renders locked teasers and sticky CTA", () => {
    const onRequest = vi.fn();
    render(
      <VideoDeepUpsell
        lockedSections={[
          { section_id: "sound", title_vi: "Âm thanh và nhịp điệu" },
          { section_id: "editing", title_vi: "Màu sắc và chữ trên hình" },
        ]}
        onRequestDeepAnalysis={onRequest}
      />,
    );

    expect(screen.getByText("Âm thanh và nhịp điệu")).toBeTruthy();
    expect(screen.getByText("Màu sắc và chữ trên hình")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Phân tích chuyên sâu (2 credit)" }));
    expect(onRequest).toHaveBeenCalledOnce();
  });

  it("renders CTA without teasers when locked list is empty", () => {
    render(
      <VideoDeepUpsell lockedSections={[]} onRequestDeepAnalysis={() => undefined} />,
    );
    expect(screen.queryByText("Còn thêm trong bản chuyên sâu")).toBeNull();
    expect(screen.getByRole("button", { name: "Phân tích chuyên sâu (2 credit)" })).toBeTruthy();
  });
});
