import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import {
  evidenceCaptionLabel,
  evidenceRangeLabel,
  FindingEvidenceClip,
  resolveStartSec,
  type AnalyzedClipContext,
} from "./FindingEvidenceClip";

const clip: AnalyzedClipContext = {
  videoId: "aweme-1",
  clipUrl: "https://r2.example/clip.mp4",
  durationSec: 30,
};

afterEach(cleanup);

describe("evidenceRangeLabel", () => {
  it("shares the trailing unit for a sub-minute range", () => {
    expect(evidenceRangeLabel({ start_sec: 0, end_sec: 3 })).toBe("0–3s");
  });

  it("formats mm:ss when either bound crosses a minute", () => {
    expect(evidenceRangeLabel({ start_sec: 12, end_sec: 78 })).toBe("12s–1:18");
  });

  it("keeps one decimal of sub-second precision", () => {
    expect(evidenceRangeLabel({ start_sec: 3.2, end_sec: 7 })).toBe("3.2–7s");
  });

  it("falls back to a single point when there is no usable range", () => {
    expect(evidenceRangeLabel({ start_sec: 5 })).toBe("5s");
    expect(evidenceRangeLabel({})).toBe("");
  });
});

describe("evidenceCaptionLabel", () => {
  it("joins range and moment with a middle dot", () => {
    expect(
      evidenceCaptionLabel({ start_sec: 0, end_sec: 3, label_vi: "mặt vào khung" }),
    ).toBe("0–3s · mặt vào khung");
  });
});

describe("resolveStartSec", () => {
  it("derives a start two seconds before end when only end_sec is present", () => {
    expect(resolveStartSec({ end_sec: 9 })).toBe(7);
  });
});

describe("FindingEvidenceClip", () => {
  it("renders nothing without a clip URL", () => {
    const { container } = render(
      <FindingEvidenceClip
        evidenceRef={{ start_sec: 2, end_sec: 5 }}
        clip={{ ...clip, clipUrl: null }}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when the ref has no usable timestamp", () => {
    const { container } = render(
      <FindingEvidenceClip evidenceRef={{ label_vi: "mặt vào khung" }} clip={clip} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when evidenceRef is absent", () => {
    const { container } = render(<FindingEvidenceClip evidenceRef={null} clip={clip} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders an inline video with caption for range + moment", () => {
    const { container } = render(
      <FindingEvidenceClip
        evidenceRef={{ start_sec: 0, end_sec: 3, label_vi: "mặt vào khung" }}
        clip={clip}
      />,
    );
    const video = container.querySelector("video");
    expect(video).toBeTruthy();
    expect(video?.getAttribute("src")).toBe(clip.clipUrl);
    expect(video?.getAttribute("data-start-sec")).toBe("0");
    expect(screen.getByText("0–3s · mặt vào khung")).toBeTruthy();
  });

  it("seeks to the resolved start when only end_sec is present", () => {
    const { container } = render(
      <FindingEvidenceClip evidenceRef={{ end_sec: 9 }} clip={clip} />,
    );
    const video = container.querySelector("video");
    expect(video?.getAttribute("data-start-sec")).toBe("7");
  });
});
