import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DiagnosisReferenceVideoCards } from "./DiagnosisReferenceVideoCards";

const modalSpy = vi.hoisted(() =>
  vi.fn((_props: { startSec?: number }) => null),
);

vi.mock("@/components/explore/VideoPlayerModal", () => ({
  VideoPlayerModal: (props: { startSec?: number }) => {
    modalSpy(props);
    return null;
  },
}));

afterEach(() => {
  cleanup();
  modalSpy.mockClear();
});

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

  it("passes peer_hook_start_sec to VideoPlayerModal when playing inline", async () => {
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
            narrative_vi: "Peer hook contrast.",
            author_handle: "peer",
            playback_url: "https://cdn/videos/1.mp4",
            peer_hook_start_sec: 0.4,
          },
        ]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Video tham chiếu @peer/i }));
    await waitFor(() => expect(modalSpy).toHaveBeenCalled());
    const lastCall = modalSpy.mock.calls.at(-1)?.[0];
    expect(lastCall?.startSec).toBe(0.4);
  });

  it("keeps thumbnail visible when hover preview play fails", async () => {
    const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockRejectedValue(
      new Error("autoplay blocked"),
    );

    const { container } = render(
      <DiagnosisReferenceVideoCards
        tiles={[
          {
            aweme_id: "7644540069277125909",
            video_url: "https://tiktok.com/@peer/video/7644540069277125909",
            thumbnail_url: "https://pub.r2.dev/thumbnails/7644540069277125909.webp",
            views: 120_000,
            caption_snippet: "",
            posted_at: "",
            narrative_vi: "",
            author_handle: "peer",
            playback_url: "https://pub.r2.dev/videos/7644540069277125909.mp4",
          },
        ]}
        inlineInFinding
      />,
    );

    const tile = container.querySelector("[style*='aspect-ratio']");
    expect(tile).toBeTruthy();
    fireEvent.mouseEnter(tile!);
    await waitFor(() => expect(play).toHaveBeenCalled());

    const img = container.querySelector("img");
    expect(img?.className).toContain("opacity-100");
    expect(img?.className).not.toContain("opacity-0");

    play.mockRestore();
  });

  it("shows CN badge on Douyin reference tiles", () => {
    render(
      <DiagnosisReferenceVideoCards
        tiles={[
          {
            aweme_id: "dy1",
            video_url: "https://www.douyin.com/video/dy1",
            thumbnail_url: "https://thumb/dy1.jpg",
            views: 120_000,
            caption_snippet: "Xu hướng Douyin",
            posted_at: "",
            source: "douyin",
            author_handle: "cn_creator",
            playback_url: "https://pub.r2.dev/videos/dy1.mp4",
          },
        ]}
      />,
    );
    expect(screen.getByLabelText("Xu hướng Douyin Trung Quốc")).toBeTruthy();
    expect(screen.getByText("CN")).toBeTruthy();
  });
});
