/**
 * D4b (2026-06-04) — DouyinVideoCard tests.
 *
 * Targets:
 *   • Renders the card body (title VN + title ZH + adapt chip + relative time).
 *   • Save toggle stops propagation + calls onToggleSave.
 *   • Card click calls onOpen when provided; falls back to opening
 *     douyin_url in a new tab when not.
 *   • Adapt chip uses the right tone class per level + falls back to
 *     "ĐANG CHỜ DUYỆT" for null adapt_level.
 *   • Hides duration / sub band / handle / rise when their data is missing.
 */

import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { DouyinVideo } from "@/lib/api-types";
import { DouyinVideoCard } from "./DouyinVideoCard";

afterEach(cleanup);


function _video(overrides: Partial<DouyinVideo> = {}): DouyinVideo {
  return {
    video_id: "v1",
    douyin_url: "https://www.douyin.com/video/v1",
    niche_id: 1,
    creator_handle: "alice",
    creator_name: "Alice",
    thumbnail_url: "https://cdn/thumb.jpg",
    video_url: "https://cdn/v.mp4",
    video_duration: 51,
    views: 4_100_000,
    likes: 412_000,
    saves: 124_000,
    engagement_rate: 14.6,
    posted_at: null,
    title_zh: "睡前3件事",
    title_vi: "Trước khi ngủ làm 3 việc",
    sub_vi: "3 việc trước khi ngủ — 1 tháng sau bạn sẽ khác",
    hashtags_zh: ["#养生"],
    adapt_level: "green",
    adapt_reason: "Wellness universal.",
    eta_weeks_min: 2,
    eta_weeks_max: 4,
    cn_rise_pct: 240,
    translator_notes: [],
    synth_computed_at: null,
    indexed_at: new Date(Date.now() - 3 * 86_400_000).toISOString(),
    ...overrides,
  };
}


describe("DouyinVideoCard", () => {
  it("renders title VN, title ZH italic, sub band, handle, views, rise, duration", () => {
    render(
      <DouyinVideoCard
        video={_video()}
        saved={false}
        onToggleSave={vi.fn()}
      />,
    );
    expect(screen.getByText("Trước khi ngủ làm 3 việc")).toBeTruthy();
    expect(screen.getByText("睡前3件事")).toBeTruthy();
    expect(screen.getByText(/3 việc trước khi ngủ/)).toBeTruthy();
    expect(screen.getByText(/抖音 @alice/)).toBeTruthy();
    expect(screen.getByText(/4\.1M/)).toBeTruthy();
    expect(screen.getByText(/\+240%/)).toBeTruthy();
    expect(screen.getByText("0:51")).toBeTruthy();
  });

  it("hides title ZH italic line when title_vi is missing (renders ZH as primary)", () => {
    const v = _video({ title_vi: null });
    render(
      <DouyinVideoCard
        video={v}
        saved={false}
        onToggleSave={vi.fn()}
      />,
    );
    // ZH appears as the primary title, not the italic secondary.
    const zh = screen.getByText("睡前3件事");
    expect(zh.className).not.toContain("italic");
  });

  it("hides duration when video_duration is null/zero", () => {
    render(
      <DouyinVideoCard
        video={_video({ video_duration: null })}
        saved={false}
        onToggleSave={vi.fn()}
      />,
    );
    expect(screen.queryByText("0:51")).toBeNull();
  });

  it("hides rise % chip when cn_rise_pct is null", () => {
    render(
      <DouyinVideoCard
        video={_video({ cn_rise_pct: null })}
        saved={false}
        onToggleSave={vi.fn()}
      />,
    );
    expect(screen.queryByText(/\+\d+%/)).toBeNull();
  });

  it("renders 'CHỜ' chip when adapt_level is null", () => {
    render(
      <DouyinVideoCard
        video={_video({ adapt_level: null })}
        saved={false}
        onToggleSave={vi.fn()}
      />,
    );
    expect(screen.getByText("CHỜ")).toBeTruthy();
  });

  it("renders 'XANH' chip when adapt_level is green", () => {
    render(
      <DouyinVideoCard
        video={_video({ adapt_level: "green" })}
        saved={false}
        onToggleSave={vi.fn()}
      />,
    );
    expect(screen.getByText("XANH")).toBeTruthy();
  });

  it("renders 'VÀNG' chip when adapt_level is yellow", () => {
    render(
      <DouyinVideoCard
        video={_video({ adapt_level: "yellow" })}
        saved={false}
        onToggleSave={vi.fn()}
      />,
    );
    expect(screen.getByText("VÀNG")).toBeTruthy();
  });

  it("renders 'ĐỎ' chip when adapt_level is red", () => {
    render(
      <DouyinVideoCard
        video={_video({ adapt_level: "red" })}
        saved={false}
        onToggleSave={vi.fn()}
      />,
    );
    expect(screen.getByText("ĐỎ")).toBeTruthy();
  });

  it("save toggle calls onToggleSave with video_id and stops propagation", () => {
    const onToggleSave = vi.fn();
    const onOpen = vi.fn();
    render(
      <DouyinVideoCard
        video={_video()}
        saved={false}
        onToggleSave={onToggleSave}
        onOpen={onOpen}
      />,
    );
    fireEvent.click(screen.getByLabelText(/Lưu vào kho/));
    expect(onToggleSave).toHaveBeenCalledWith("v1");
    // Click did NOT bubble to the card click handler.
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("save button label changes when saved=true", () => {
    render(
      <DouyinVideoCard
        video={_video()}
        saved={true}
        onToggleSave={vi.fn()}
      />,
    );
    expect(screen.getByLabelText(/Đã lưu/)).toBeTruthy();
    expect(screen.queryByLabelText(/Lưu vào kho/)).toBeNull();
  });

  it("card click calls onOpen with the full video object when provided", () => {
    const onOpen = vi.fn();
    const v = _video();
    render(
      <DouyinVideoCard
        video={v}
        saved={false}
        onToggleSave={vi.fn()}
        onOpen={onOpen}
      />,
    );
    // Click anywhere on the card body (not the save button).
    fireEvent.click(screen.getByRole("button", { name: /Trước khi ngủ/ }));
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith(v);
  });

  it("card click opens douyin_url externally when no onOpen handler provided", () => {
    const open = vi.fn();
    const orig = window.open;
    window.open = open as never;
    try {
      render(
        <DouyinVideoCard
          video={_video()}
          saved={false}
          onToggleSave={vi.fn()}
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: /Trước khi ngủ/ }));
      expect(open).toHaveBeenCalledWith(
        "https://www.douyin.com/video/v1",
        "_blank",
        "noopener,noreferrer",
      );
    } finally {
      window.open = orig;
    }
  });

  it("formats relative time", () => {
    render(
      <DouyinVideoCard
        video={_video({
          indexed_at: new Date(Date.now() - 3 * 86_400_000).toISOString(),
        })}
        saved={false}
        onToggleSave={vi.fn()}
      />,
    );
    expect(screen.getByText("3 ngày trước")).toBeTruthy();
  });
});
