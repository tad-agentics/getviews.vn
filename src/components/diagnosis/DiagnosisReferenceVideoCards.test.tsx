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
});
