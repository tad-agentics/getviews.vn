import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { IntentCtaRail } from "./IntentCtaRail";

const ctx = {
  format: "video" as const,
  mode: "win" as const,
  videoQuery: "https://www.tiktok.com/@a/video/1",
  scriptDraftId: null,
  evidenceVideoQuery: null,
  sessionInitialQ: "https://www.tiktok.com/@a/video/1",
  creatorHandle: null,
};

describe("IntentCtaRail", () => {
  it("renders Vietnamese CTA pills and fires onCta on tap", () => {
    const onCta = vi.fn();
    render(<IntentCtaRail context={ctx} onCta={onCta} />);
    fireEvent.click(screen.getByRole("button", { name: /Tạo kịch bản/ }));
    expect(onCta).toHaveBeenCalledWith(
      expect.objectContaining({ id: "video_script", intentType: "shot_list" }),
      expect.any(String),
    );
  });

  it("opens compare URL mini prompt", () => {
    render(<IntentCtaRail context={ctx} onCta={vi.fn()} />);
    const compareButtons = screen.getAllByRole("button", { name: /So sánh với video khác/ });
    fireEvent.click(compareButtons[0]!);
    expect(screen.getByPlaceholderText(/tiktok/i)).toBeTruthy();
  });
});
