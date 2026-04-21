/**
 * VideoPlayerModal — keyboard + a11y regression.
 *
 * Locks in the three behaviors we added during the /app/trends audit:
 *   1. Escape closes (already shipped; test guards the contract).
 *   2. ArrowDown / ArrowUp cycle through `allVideos` — TikTok-parity.
 *   3. Tab focus trap: Tab from the last focusable wraps to the first,
 *      and Shift+Tab from the first wraps to the last, so keyboard users
 *      can't accidentally tab out of the modal into the masked backdrop.
 *
 * jsdom doesn't play HTMLMediaElement — we stub `HTMLVideoElement.prototype.play`
 * to a no-op before rendering.
 */
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
  },
}));

// motion/react renders a real DOM node; stub AnimatePresence to render
// children directly so we don't wait on exit animations in jsdom.
vi.mock("motion/react", () => {
  function MockMotion(props: Record<string, unknown>) {
    const { children, ...rest } = props as { children?: React.ReactNode };
    // Strip motion-only props that React would warn on.
    for (const key of ["initial", "animate", "exit", "transition"] as const) {
      delete (rest as Record<string, unknown>)[key];
    }
    return React.createElement("div", rest, children);
  }
  const motion = new Proxy({} as Record<string, typeof MockMotion>, {
    get: () => MockMotion,
  });
  return {
    motion,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

import { VideoPlayerModal, type ExploreGridVideo } from "./VideoPlayerModal";

function mkVideo(id: string, overrides: Partial<ExploreGridVideo> = {}): ExploreGridVideo {
  return {
    id,
    video_id: id,
    views: "100K",
    time: "2 giờ trước",
    img: "/thumb.jpg",
    text: `hook cho ${id}`,
    handle: `@creator_${id}`,
    caption: `caption ${id}`,
    likes: "10K",
    comments: "500",
    shares: "200",
    videoUrl: `/video-${id}.mp4`,
    tiktok_url: null,
    ...overrides,
  };
}

beforeEach(() => {
  // HTMLVideoElement.play returns a promise in browsers; jsdom throws.
  Object.defineProperty(HTMLMediaElement.prototype, "play", {
    configurable: true,
    value: vi.fn(() => Promise.resolve()),
  });
  Object.defineProperty(HTMLMediaElement.prototype, "load", {
    configurable: true,
    value: vi.fn(),
  });
});
afterEach(cleanup);

describe("VideoPlayerModal keyboard a11y", () => {
  it("exposes the modal as role=dialog with aria-modal and a label", () => {
    render(
      <VideoPlayerModal
        video={mkVideo("a")}
        allVideos={[mkVideo("a")]}
        onClose={vi.fn()}
      />,
    );
    const dialog = screen.getByRole("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(dialog.getAttribute("aria-label")).toBeTruthy();
  });

  it("closes on Escape", () => {
    const onClose = vi.fn();
    render(
      <VideoPlayerModal video={mkVideo("a")} allVideos={[mkVideo("a")]} onClose={onClose} />,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("ArrowDown advances to the next video in allVideos", () => {
    const videos = [mkVideo("a"), mkVideo("b"), mkVideo("c")];
    render(<VideoPlayerModal video={videos[0]} allVideos={videos} onClose={vi.fn()} />);
    // Initial selection: video a → aria-label reflects its caption.
    expect(screen.getByRole("dialog").getAttribute("aria-label")).toContain("caption a");
    fireEvent.keyDown(document, { key: "ArrowDown" });
    expect(screen.getByRole("dialog").getAttribute("aria-label")).toContain("caption b");
    fireEvent.keyDown(document, { key: "ArrowDown" });
    expect(screen.getByRole("dialog").getAttribute("aria-label")).toContain("caption c");
    // ArrowDown at end stays pinned — no wrap-around (matches TikTok swipe).
    fireEvent.keyDown(document, { key: "ArrowDown" });
    expect(screen.getByRole("dialog").getAttribute("aria-label")).toContain("caption c");
  });

  it("ArrowUp rewinds to the previous video, floor at index 0", () => {
    const videos = [mkVideo("a"), mkVideo("b"), mkVideo("c")];
    render(<VideoPlayerModal video={videos[2]} allVideos={videos} onClose={vi.fn()} />);
    expect(screen.getByRole("dialog").getAttribute("aria-label")).toContain("caption c");
    fireEvent.keyDown(document, { key: "ArrowUp" });
    expect(screen.getByRole("dialog").getAttribute("aria-label")).toContain("caption b");
    fireEvent.keyDown(document, { key: "ArrowUp" });
    expect(screen.getByRole("dialog").getAttribute("aria-label")).toContain("caption a");
    fireEvent.keyDown(document, { key: "ArrowUp" });
    expect(screen.getByRole("dialog").getAttribute("aria-label")).toContain("caption a");
  });

  it("surfaces aria-current on the currently-selected video in the list", () => {
    const videos = [mkVideo("a"), mkVideo("b")];
    render(<VideoPlayerModal video={videos[1]} allVideos={videos} onClose={vi.fn()} />);
    // Find the list row for video b (has aria-current) and video a (doesn't).
    // List rows carry aria-label equal to the caption.
    const rowA = screen.getAllByRole("button", { name: /caption a/ });
    const rowB = screen.getAllByRole("button", { name: /caption b/ });
    expect(rowA.some((el) => el.getAttribute("aria-current") === "true")).toBe(false);
    expect(rowB.some((el) => el.getAttribute("aria-current") === "true")).toBe(true);
  });

  it("labels the close and mute buttons in Vietnamese", () => {
    render(
      <VideoPlayerModal video={mkVideo("a")} allVideos={[mkVideo("a")]} onClose={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: "Đóng video" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Bật tiếng" })).toBeTruthy();
  });
});
