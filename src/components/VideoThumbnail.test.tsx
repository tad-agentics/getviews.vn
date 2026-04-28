/**
 * ``VideoThumbnail`` is the single shared renderer for video
 * thumbnails. It replaces the ~6 raw ``<img src={thumbnail_url}>``
 * callsites that had no ``onError`` handler — those rendered the
 * browser's default broken-image icon when the URL went stale
 * (TikTok CDN URLs rotate every few weeks, so older corpus rows
 * hit this commonly).
 *
 * Pin the contract: render the image when URL is present,
 * render the placeholder when URL is missing OR when the image
 * load fails (``onError`` fires). Never let the broken-image icon
 * leak through.
 */
import { describe, expect, it } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import { VideoThumbnail } from "./VideoThumbnail";

describe("VideoThumbnail", () => {
  it("renders the image when a non-empty URL is provided", () => {
    const { container } = render(
      <VideoThumbnail thumbnailUrl="https://r2.test/thumbnails/abc.png" />,
    );
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img?.getAttribute("src")).toBe(
      "https://r2.test/thumbnails/abc.png",
    );
    expect(container.querySelector("div[aria-hidden]")).toBeNull();
  });

  it("renders the placeholder when URL is null", () => {
    const { container } = render(<VideoThumbnail thumbnailUrl={null} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("div[aria-hidden]")).not.toBeNull();
  });

  it("renders the placeholder when URL is undefined", () => {
    const { container } = render(<VideoThumbnail thumbnailUrl={undefined} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("div[aria-hidden]")).not.toBeNull();
  });

  it("treats an all-whitespace URL as empty", () => {
    const { container } = render(<VideoThumbnail thumbnailUrl="   " />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("div[aria-hidden]")).not.toBeNull();
  });

  it("swaps to the placeholder after onError fires (no broken-icon)", () => {
    const { container } = render(
      <VideoThumbnail thumbnailUrl="https://broken.test/x.png" />,
    );
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    fireEvent.error(img!);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("div[aria-hidden]")).not.toBeNull();
  });

  it("forwards alt text to the image element", () => {
    const { container } = render(
      <VideoThumbnail thumbnailUrl="https://r2.test/x.png" alt="hero shot" />,
    );
    expect(container.querySelector("img")?.getAttribute("alt")).toBe("hero shot");
  });

  it("default alt is empty string (decorative thumbnail)", () => {
    const { container } = render(
      <VideoThumbnail thumbnailUrl="https://r2.test/x.png" />,
    );
    // Decorative images should have empty alt — assistive tech skips them.
    expect(container.querySelector("img")?.getAttribute("alt")).toBe("");
  });

  it("merges className onto both the img and the placeholder", () => {
    // Image branch.
    const { container: imgContainer, rerender } = render(
      <VideoThumbnail
        thumbnailUrl="https://r2.test/x.png"
        className="h-16 w-12 rounded"
      />,
    );
    expect(imgContainer.querySelector("img")?.className).toMatch(/h-16 w-12 rounded/);

    // Placeholder branch.
    rerender(
      <VideoThumbnail thumbnailUrl={null} className="h-16 w-12 rounded" />,
    );
    expect(
      imgContainer.querySelector("div[aria-hidden]")?.className,
    ).toMatch(/h-16 w-12 rounded/);
  });

  it("respects placeholderClassName when explicitly set", () => {
    const { container } = render(
      <VideoThumbnail
        thumbnailUrl={null}
        placeholderClassName="bg-[var(--gv-accent-soft)]"
      />,
    );
    expect(container.querySelector("div[aria-hidden]")?.className).toMatch(
      /bg-\[var\(--gv-accent-soft\)\]/,
    );
  });

  it("forwards loading + fetchPriority hints", () => {
    const { container } = render(
      <VideoThumbnail
        thumbnailUrl="https://r2.test/x.png"
        loading="eager"
        fetchPriority="high"
      />,
    );
    const img = container.querySelector("img");
    expect(img?.getAttribute("loading")).toBe("eager");
    // React 19 lowercases the attribute on the DOM.
    expect(img?.getAttribute("fetchpriority")).toBe("high");
  });
});
