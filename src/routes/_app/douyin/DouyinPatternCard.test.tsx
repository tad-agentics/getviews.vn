/**
 * D5e (2026-06-05) — DouyinPatternCard render tests.
 */

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import type { DouyinPattern } from "@/lib/api-types";

import { DouyinPatternCard } from "./DouyinPatternCard";


afterEach(() => cleanup());


function _pattern(overrides: Partial<DouyinPattern> = {}): DouyinPattern {
  return {
    id: "pat-1",
    niche_id: 1,
    week_of: "2026-06-01",
    rank: 1,
    name_vn: "Routine 3 bước trước khi ngủ",
    name_zh: "睡前仪式",
    hook_template_vi: "3 việc trước khi ___ — 1 tháng sau bạn sẽ khác",
    format_signal_vi:
      "Quay POV cận cảnh, transition cắt nhanh sau mỗi 1.5s, voiceover thì thầm.",
    sample_video_ids: ["v1", "v2", "v3"],
    cn_rise_pct_avg: 35.0,
    computed_at: "2026-06-01T21:00:00+00:00",
    ...overrides,
  };
}


describe("DouyinPatternCard", () => {
  it("renders rank badge + name + hook template + format signal + sample count + ZH name", () => {
    render(<DouyinPatternCard pattern={_pattern()} />);
    expect(screen.getByLabelText(/Pattern hạng 1/)).toBeTruthy();
    expect(screen.getByText("Routine 3 bước trước khi ngủ")).toBeTruthy();
    expect(screen.getByText(/3 việc trước khi ___/)).toBeTruthy();
    expect(screen.getByText(/Quay POV cận cảnh/)).toBeTruthy();
    expect(screen.getByText(/3 video mẫu/)).toBeTruthy();
    expect(screen.getByText("睡前仪式")).toBeTruthy();
  });

  it("renders the rise pct chip when cn_rise_pct_avg is positive", () => {
    render(<DouyinPatternCard pattern={_pattern({ cn_rise_pct_avg: 42.7 })} />);
    expect(screen.getByLabelText(/Tăng trung bình \+43%/)).toBeTruthy();
    expect(screen.getByText("+43%")).toBeTruthy();
  });

  it("hides the rise chip when cn_rise_pct_avg is null / zero / negative", () => {
    const variants: (number | null)[] = [null, 0, -5];
    for (const v of variants) {
      cleanup();
      render(<DouyinPatternCard pattern={_pattern({ cn_rise_pct_avg: v })} />);
      expect(screen.queryByText(/Tăng trung bình/)).toBeNull();
    }
  });

  it("hides the ZH name when name_zh is null (format-only pattern)", () => {
    render(<DouyinPatternCard pattern={_pattern({ name_zh: null })} />);
    expect(screen.queryByText("睡前仪式")).toBeNull();
  });

  it("exposes data-rank + data-niche-id for stable selection in screen tests", () => {
    const { container } = render(
      <DouyinPatternCard pattern={_pattern({ rank: 2, niche_id: 9 })} />,
    );
    const article = container.querySelector("article")!;
    expect(article.getAttribute("data-rank")).toBe("2");
    expect(article.getAttribute("data-niche-id")).toBe("9");
  });
});
