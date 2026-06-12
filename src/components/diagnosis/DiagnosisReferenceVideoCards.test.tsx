import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DiagnosisReferenceVideoCards } from "./DiagnosisReferenceVideoCards";

afterEach(() => cleanup());

describe("DiagnosisReferenceVideoCards", () => {
  it("renders narrative, views, and handle per card", () => {
    render(
      <DiagnosisReferenceVideoCards
        tiles={[
          {
            aweme_id: "1",
            video_url: "https://tiktok.com/@a/video/1",
            thumbnail_url: "https://thumb/1.jpg",
            views: 34_200,
            caption_snippet: "fallback",
            posted_at: "",
            narrative_vi: "Cùng format listicle — nhịp nhanh hơn median ngách.",
            author_handle: "nahoang5477",
          },
        ]}
      />,
    );
    expect(screen.getByText(/Cùng format listicle/)).toBeTruthy();
    expect(screen.getByText(/34\.2K view/)).toBeTruthy();
    expect(screen.getByText("@nahoang5477")).toBeTruthy();
  });

  it("omits the kicker when showLabel is false (inline in parent section)", () => {
    render(
      <DiagnosisReferenceVideoCards
        tiles={[
          {
            aweme_id: "1",
            video_url: "https://tiktok.com/@a/video/1",
            thumbnail_url: "",
            views: 1000,
            caption_snippet: "",
            posted_at: "",
            narrative_vi: "Được chọn vì cấu trúc format và nhịp dẫn nhất quán suốt clip.",
            author_handle: "creator",
          },
        ]}
        embedded
        showLabel={false}
      />,
    );
    expect(screen.queryByText("Video tham chiếu")).toBeNull();
    expect(screen.getByText(/nhịp dẫn nhất quán/)).toBeTruthy();
  });

  it("wraps each tile in a bordered card shell", () => {
    const { container } = render(
      <DiagnosisReferenceVideoCards
        tiles={[
          {
            aweme_id: "1",
            video_url: "https://tiktok.com/@a/video/1",
            thumbnail_url: "",
            views: 1000,
            caption_snippet: "",
            posted_at: "",
            narrative_vi: "Được chọn vì cấu trúc format và nhịp dẫn nhất quán suốt clip.",
            author_handle: "creator",
          },
        ]}
        embedded
        showLabel={false}
      />,
    );
    const shell = container.querySelector(".rounded-xl.border");
    expect(shell).toBeTruthy();
    expect(shell?.className).toContain("bg-[color:var(--gv-canvas-2)]");
  });
});
