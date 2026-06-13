import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import {
  evidenceRangeLabel,
  FindingEvidenceClip,
  type AnalyzedClipContext,
} from "./FindingEvidenceClip";

// The modal lazy-imports motion + a <video> element; stub it so the test asserts
// the deep-link contract (open + startSec) without dragging in playback.
vi.mock("@/components/explore/VideoPlayerModal", () => ({
  VideoPlayerModal: ({ startSec, onClose }: { startSec?: number; onClose: () => void }) => (
    <div data-testid="player" data-start-sec={startSec}>
      <button type="button" onClick={onClose}>
        close
      </button>
    </div>
  ),
}));

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

  it("labels the button with the range and the moment", () => {
    render(
      <FindingEvidenceClip
        evidenceRef={{ start_sec: 0, end_sec: 3, label_vi: "mặt vào khung" }}
        clip={clip}
      />,
    );
    expect(
      screen.getByRole("button", { name: /Xem 0–3s trong clip · mặt vào khung/ }),
    ).toBeTruthy();
  });

  it("opens the player seeked to the resolved start on click", async () => {
    render(
      <FindingEvidenceClip evidenceRef={{ start_sec: 4, end_sec: 9 }} clip={clip} />,
    );
    expect(screen.queryByTestId("player")).toBeNull();
    fireEvent.click(screen.getByRole("button"));
    const player = await screen.findByTestId("player");
    expect(player.getAttribute("data-start-sec")).toBe("4");
  });

  it("derives a start two seconds before end when only end_sec is present", async () => {
    render(<FindingEvidenceClip evidenceRef={{ end_sec: 9 }} clip={clip} />);
    fireEvent.click(screen.getByRole("button"));
    const player = await screen.findByTestId("player");
    expect(player.getAttribute("data-start-sec")).toBe("7");
  });
});
