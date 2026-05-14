/**
 * VideoThumbnail — failure beacon behaviour tests.
 *
 * Verifies that:
 * - The beacon fires once when an image fails to load.
 * - The beacon does NOT fire again for the same video_id (session dedup).
 * - A missing videoId still fires (no crash), just not de-duplicated.
 * - No beacon fires when thumbnailUrl is null / empty (placeholder, no img).
 */

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { VideoThumbnail } from "./VideoThumbnail";

// ── Mocks ──────────────────────────────────────────────────────────────────

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "anon-key",
  },
}));

const mockSendBeacon = vi.fn().mockReturnValue(true);

// ── Setup / Teardown ───────────────────────────────────────────────────────

beforeEach(() => {
  // Re-isolate the module-level _reported Set between tests by resetting modules.
  vi.resetModules();
  vi.stubGlobal("navigator", { sendBeacon: mockSendBeacon });
  mockSendBeacon.mockClear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// ── Helpers ────────────────────────────────────────────────────────────────

async function importComponent() {
  const mod = await import("./VideoThumbnail");
  return mod.VideoThumbnail;
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe("VideoThumbnail — thumbnail failure beacon", () => {
  it("fires sendBeacon once when image fails to load", async () => {
    const VT = await importComponent();
    const { container } = render(
      <VT thumbnailUrl="https://r2.test/thumb.png" videoId="vid-1" />
    );
    const img = container.querySelector("img")!;
    fireEvent.error(img);
    expect(mockSendBeacon).toHaveBeenCalledTimes(1);
    const [url, blob] = mockSendBeacon.mock.calls[0];
    expect(url).toContain("track-thumbnail-failure");
    expect(blob).toBeInstanceOf(Blob);
  });

  it("does NOT fire beacon a second time for the same video_id on re-render", async () => {
    const VT = await importComponent();
    const { container } = render(
      <VT thumbnailUrl="https://r2.test/thumb.png" videoId="vid-2" />
    );
    const img = container.querySelector("img")!;
    fireEvent.error(img);
    expect(mockSendBeacon).toHaveBeenCalledTimes(1);

    // Reset call count; re-mount fresh component with same video_id.
    // The module-level _reported Set is NOT reset between renders (only between
    // vi.resetModules() calls in beforeEach). Within the same test, the Set persists.
    mockSendBeacon.mockClear();
    cleanup();
    const { container: c2 } = render(
      <VT thumbnailUrl="https://r2.test/thumb3.png" videoId="vid-2" />
    );
    const img2 = c2.querySelector("img")!;
    fireEvent.error(img2);
    expect(mockSendBeacon).toHaveBeenCalledTimes(0);
  });

  it("fires beacon even when videoId is not provided (no crash)", async () => {
    const VT = await importComponent();
    const { container } = render(<VT thumbnailUrl="https://r2.test/thumb.png" />);
    const img = container.querySelector("img")!;
    fireEvent.error(img);
    expect(mockSendBeacon).toHaveBeenCalledTimes(1);
  });

  it("renders placeholder and does NOT fire beacon when thumbnailUrl is null", async () => {
    const VT = await importComponent();
    render(<VT thumbnailUrl={null} videoId="vid-null" />);
    expect(screen.queryByRole("img")).toBeNull();
    expect(mockSendBeacon).toHaveBeenCalledTimes(0);
  });

  it("renders placeholder and does NOT fire beacon when thumbnailUrl is empty string", async () => {
    const VT = await importComponent();
    render(<VT thumbnailUrl="" videoId="vid-empty" />);
    expect(screen.queryByRole("img")).toBeNull();
    expect(mockSendBeacon).toHaveBeenCalledTimes(0);
  });
});
