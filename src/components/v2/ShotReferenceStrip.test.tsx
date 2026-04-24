import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ShotReference } from "@/lib/api-types";
import { ShotReferenceStrip } from "./ShotReferenceStrip";

afterEach(() => {
  cleanup();
});

function makeRef(overrides: Partial<ShotReference> = {}): ShotReference {
  return {
    video_id: "v1",
    scene_index: 0,
    start_s: 5,
    end_s: 12,
    frame_url: "https://cdn.test/v1/0.jpg",
    thumbnail_url: "https://cdn.test/thumb.jpg",
    tiktok_url: "https://tiktok.com/@creator/video/v1",
    creator_handle: "@creator",
    description: "Cận mặt creator nói hook.",
    score: 55,
    match_signals: ["niche", "hook", "framing"],
    match_label: "Cùng ngách, hook, khung hình",
    ...overrides,
  };
}

describe("ShotReferenceStrip", () => {
  it("renders nothing when refs empty", () => {
    const { container } = render(<ShotReferenceStrip refs={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when refs undefined", () => {
    const { container } = render(<ShotReferenceStrip refs={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows the count in the kicker", () => {
    render(<ShotReferenceStrip refs={[makeRef(), makeRef({ video_id: "v2" })]} />);
    expect(screen.getByText(/CLIP THAM KHẢO · 2/)).toBeTruthy();
  });

  it("renders match_label as VN chip", () => {
    render(<ShotReferenceStrip refs={[makeRef()]} />);
    expect(
      screen.getByText(/Cùng ngách, hook, khung hình/),
    ).toBeTruthy();
  });

  it("shows the creator handle without a double @", () => {
    render(<ShotReferenceStrip refs={[makeRef({ creator_handle: "@creator" })]} />);
    const el = screen.getByText("@creator");
    // Not "@@creator"
    expect(el.textContent).toBe("@creator");
  });

  it("renders the tiktok_url as an external link with noopener noreferrer", () => {
    render(<ShotReferenceStrip refs={[makeRef()]} />);
    const link = screen.getByRole("link");
    expect(link.getAttribute("href")).toBe("https://tiktok.com/@creator/video/v1");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(link.getAttribute("rel")).toContain("noreferrer");
  });

  it("falls back to a static div when no tiktok_url", () => {
    render(
      <ShotReferenceStrip
        refs={[makeRef({ tiktok_url: null })]}
      />,
    );
    expect(screen.queryByRole("link")).toBeNull();
    // Still shows the match chip so the card isn't empty.
    expect(
      screen.getByText(/Cùng ngách, hook, khung hình/),
    ).toBeTruthy();
  });

  it("renders timecode when start_s + end_s present", () => {
    render(<ShotReferenceStrip refs={[makeRef({ start_s: 5, end_s: 12 })]} />);
    expect(screen.getByText("5–12s")).toBeTruthy();
  });

  it("renders start-only timecode when end_s missing", () => {
    render(<ShotReferenceStrip refs={[makeRef({ start_s: 3, end_s: null })]} />);
    expect(screen.getByText("3s")).toBeTruthy();
  });

  it("omits timecode when start_s missing", () => {
    render(<ShotReferenceStrip refs={[makeRef({ start_s: null, end_s: null })]} />);
    // No timecode badge — just the match chip is present.
    expect(screen.queryByText(/s$/)).toBeFalsy();
  });

  it("prefers frame_url background when both frame_url and thumbnail_url set", () => {
    const { container } = render(<ShotReferenceStrip refs={[makeRef()]} />);
    const media = container.querySelector("[style*='background-image']");
    expect(media).toBeTruthy();
    const style = media?.getAttribute("style") ?? "";
    expect(style).toContain("v1/0.jpg");
    expect(style).not.toContain("thumb.jpg");
  });

  it("falls back to thumbnail_url when frame_url missing", () => {
    const { container } = render(
      <ShotReferenceStrip refs={[makeRef({ frame_url: null })]} />,
    );
    const media = container.querySelector("[style*='background-image']");
    expect(media?.getAttribute("style") ?? "").toContain("thumb.jpg");
  });

  it("renders gradient tile when both media urls missing", () => {
    const { container } = render(
      <ShotReferenceStrip
        refs={[makeRef({ frame_url: null, thumbnail_url: null })]}
      />,
    );
    // No background-image style — the fallback class carries the color.
    const media = container.querySelector("[style*='background-image']");
    expect(media).toBeNull();
  });

  it("supports density=block for shoot mode", () => {
    const { container } = render(
      <ShotReferenceStrip refs={[makeRef()]} density="block" />,
    );
    // block mode uses w-24 / min-[700px]:w-28 instead of w-20.
    const link = container.querySelector("a");
    expect(link?.className).toContain("w-24");
  });
});
