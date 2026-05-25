/**
 * VideoThumbnail — R2 fallback + failure telemetry tests.
 */

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { VideoThumbnail } from "./VideoThumbnail";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "anon-key",
    VITE_R2_PUBLIC_URL: "https://media.getviews.vn",
  },
}));

const mockFetch = vi.fn().mockResolvedValue({ ok: true });

beforeEach(() => {
  vi.resetModules();
  vi.stubGlobal("fetch", mockFetch);
  mockFetch.mockClear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function importComponent() {
  const mod = await import("./VideoThumbnail");
  return mod.VideoThumbnail;
}

function exhaustThumbnailErrors(container: HTMLElement): void {
  for (let i = 0; i < 6; i += 1) {
    const img = container.querySelector("img");
    if (!img) break;
    fireEvent.error(img);
  }
}

describe("VideoThumbnail", () => {
  it("prefers R2 webp before DB CDN URL", async () => {
    const VT = await importComponent();
    const { container } = render(
      <VT thumbnailUrl="https://tiktok.cdn/stale.jpg" videoId="1234567890123456" />,
    );
    const img = container.querySelector("img")!;
    expect(img.getAttribute("src")).toBe(
      "https://media.getviews.vn/thumbnails/1234567890123456.webp",
    );
    expect(mockFetch).toHaveBeenCalledTimes(0);
  });

  it("falls back to CDN after webp fails", async () => {
    const VT = await importComponent();
    const { container } = render(
      <VT thumbnailUrl="https://tiktok.cdn/stale.jpg" videoId="1234567890123456" />,
    );
    const img = container.querySelector("img")!;
    fireEvent.error(img);
    expect(container.querySelector("img")?.getAttribute("src")).toBe(
      "https://tiktok.cdn/stale.jpg",
    );
    expect(mockFetch).toHaveBeenCalledTimes(0);
  });

  it("fires fetch once after all candidates fail", async () => {
    const VT = await importComponent();
    const { container } = render(
      <VT thumbnailUrl="https://r2.test/thumb.png" videoId="1234567890123456" />,
    );
    exhaustThumbnailErrors(container);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(String(url)).toContain("track-thumbnail-failure");
    expect(init).toMatchObject({
      method: "POST",
      credentials: "omit",
      keepalive: true,
      mode: "cors",
    });
  });

  it("does NOT fire fetch a second time for the same video_id on re-render", async () => {
    const VT = await importComponent();
    const { container } = render(
      <VT thumbnailUrl="https://r2.test/thumb.png" videoId="2234567890123456" />,
    );
    exhaustThumbnailErrors(container);
    expect(mockFetch).toHaveBeenCalledTimes(1);

    mockFetch.mockClear();
    cleanup();
    const { container: c2 } = render(
      <VT thumbnailUrl="https://r2.test/thumb3.png" videoId="2234567890123456" />,
    );
    exhaustThumbnailErrors(c2);
    expect(mockFetch).toHaveBeenCalledTimes(0);
  });

  it("fires fetch even when videoId is not provided (no crash)", async () => {
    const VT = await importComponent();
    const { container } = render(<VT thumbnailUrl="https://r2.test/thumb.png" />);
    exhaustThumbnailErrors(container);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("uses R2 when thumbnailUrl is null but videoId is set", async () => {
    const VT = await importComponent();
    const { container } = render(<VT thumbnailUrl={null} videoId="3234567890123456" />);
    expect(container.querySelector("img")?.getAttribute("src")).toBe(
      "https://media.getviews.vn/thumbnails/3234567890123456.webp",
    );
    expect(mockFetch).toHaveBeenCalledTimes(0);
  });

  it("renders placeholder when thumbnailUrl and videoId are missing", async () => {
    const VT = await importComponent();
    render(<VT thumbnailUrl={null} />);
    expect(screen.queryByRole("img")).toBeNull();
    expect(mockFetch).toHaveBeenCalledTimes(0);
  });
});
