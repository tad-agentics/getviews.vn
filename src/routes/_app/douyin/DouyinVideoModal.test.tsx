/**
 * D4d (2026-06-04) — DouyinVideoModal interaction tests.
 *
 * Mocks ``react-router``'s ``useNavigate`` so the "Adapt sang VN →
 * Kịch bản" CTA can be observed without a real router.
 */

import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { DouyinVideo } from "@/lib/api-types";

const navigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>(
    "react-router",
  );
  return {
    ...actual,
    useNavigate: () => navigate,
  };
});

const { DouyinVideoModal } = await import("./DouyinVideoModal");


function _video(overrides: Partial<DouyinVideo> = {}): DouyinVideo {
  return {
    video_id: "v1",
    douyin_url: "https://www.douyin.com/video/v1",
    niche_id: 1,
    creator_handle: "alice",
    creator_name: "Alice",
    thumbnail_url: null,
    video_url: null,
    video_duration: 30,
    views: 1_200_000,
    likes: 80_000,
    saves: 14_000,
    engagement_rate: 12.5,
    posted_at: null,
    title_zh: "睡前3件事",
    title_vi: "3 việc trước khi ngủ",
    sub_vi: "Bí quyết để ngủ ngon",
    hashtags_zh: [],
    adapt_level: "green",
    adapt_reason: "Routine ngủ phù hợp với khán giả VN; chỉ cần đổi nhạc.",
    eta_weeks_min: 2,
    eta_weeks_max: 4,
    cn_rise_pct: 35,
    translator_notes: [
      { tag: "TỪ NGỮ", note: "Thay 'tế bào' bằng 'làn da' cho tự nhiên." },
      { tag: "BỐI CẢNH", note: "Đổi phòng ngủ phong cách bắc Trung sang phòng VN." },
    ],
    synth_computed_at: null,
    indexed_at: "2026-06-01T00:00:00Z",
    ...overrides,
  };
}


function _renderModal(props: {
  video: DouyinVideo | null;
  saved?: boolean;
  open?: boolean;
} = { video: _video() }) {
  const onOpenChange = vi.fn();
  const onToggleSave = vi.fn();
  render(
    <DouyinVideoModal
      video={props.video}
      open={props.open ?? true}
      onOpenChange={onOpenChange}
      saved={props.saved ?? false}
      onToggleSave={onToggleSave}
    />,
  );
  return { onOpenChange, onToggleSave };
}


beforeEach(() => {
  navigate.mockReset();
});

afterEach(() => {
  cleanup();
});


describe("DouyinVideoModal — populated row", () => {
  it("renders title VN, title ZH, the 2x2 stats grid, the adapt strip and 2 translator notes", () => {
    _renderModal({ video: _video() });
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByText("3 việc trước khi ngủ")).toBeTruthy();
    expect(screen.getByText("睡前3件事")).toBeTruthy();
    // D7 — stats grid is now VIEW / SAVE / TĂNG 14N / THỜI LƯỢNG
    // (design pack ``screens/douyin.jsx`` lines 1078-1086).
    // formatViews keeps one decimal: "1.2M" / "14.0K".
    expect(screen.getByText("1.2M")).toBeTruthy(); // views
    expect(screen.getByText("14.0K")).toBeTruthy(); // saves
    expect(screen.getByText("0:30")).toBeTruthy(); // duration (30s → 0:30)
    // Adapt strip
    expect(screen.getByText(/Khả năng adapt sang VN/)).toBeTruthy();
    expect(screen.getByText("Dịch thẳng")).toBeTruthy();
    expect(screen.getByText(/Routine ngủ phù hợp/)).toBeTruthy();
    expect(screen.getByText("2–4 tuần")).toBeTruthy();
    // The +35% rise appears in the stats grid (TĂNG 14N) AND in the
    // adapt strip "Đà ở CN" cell — both source the same cn_rise_pct.
    expect(screen.getAllByText("+35%").length).toBeGreaterThanOrEqual(1);
    // Translator notes — 2 rows + tags
    expect(screen.getByText(/Note văn hoá \(2\)/)).toBeTruthy();
    expect(screen.getByText("TỪ NGỮ")).toBeTruthy();
    expect(screen.getByText("BỐI CẢNH")).toBeTruthy();
  });

  it("navigates to /app/script with prefill on Adapt CTA click", () => {
    const { onOpenChange } = _renderModal();
    fireEvent.click(
      screen.getByRole("button", { name: /Adapt sang VN → Kịch bản/ }),
    );
    expect(navigate).toHaveBeenCalledTimes(1);
    const arg = navigate.mock.calls[0]![0] as string;
    expect(arg.startsWith("/app/script?")).toBe(true);
    const qs = new URLSearchParams(arg.split("?")[1]);
    expect(qs.get("topic")).toBe("3 việc trước khi ngủ");
    expect(qs.get("hook")).toBe("Bí quyết để ngủ ngon");
    expect(qs.get("duration")).toBe("30");
    // Adapt navigates close the modal first.
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("toggles save when the save pill is clicked + flips label saved/unsaved", () => {
    const { onToggleSave } = _renderModal({ video: _video(), saved: false });
    fireEvent.click(screen.getByRole("button", { name: /Lưu vào kho/ }));
    expect(onToggleSave).toHaveBeenCalledWith("v1");
    cleanup();
    _renderModal({ video: _video(), saved: true });
    expect(screen.getByRole("button", { name: /Bỏ lưu/ })).toBeTruthy();
  });

  it("opens the Douyin source in a new tab when 'Mở trên Douyin' is clicked", () => {
    const open = vi.fn();
    vi.stubGlobal("open", open);
    _renderModal();
    fireEvent.click(screen.getByRole("button", { name: /Mở trên Douyin/ }));
    expect(open).toHaveBeenCalledWith(
      "https://www.douyin.com/video/v1",
      "_blank",
      "noopener,noreferrer",
    );
    vi.unstubAllGlobals();
  });

  it("emits onOpenChange(false) when the close X is clicked", () => {
    const { onOpenChange } = _renderModal();
    fireEvent.click(screen.getByRole("button", { name: "Đóng" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});


describe("DouyinVideoModal — pending / sparse rows", () => {
  it("renders the CHỜ chip and suppresses ETA / cn_rise / translator notes when synth hasn't graded the row", () => {
    _renderModal({
      video: _video({
        adapt_level: null,
        adapt_reason: null,
        eta_weeks_min: null,
        eta_weeks_max: null,
        cn_rise_pct: null,
        translator_notes: [],
      }),
    });
    expect(screen.getByText("CHỜ")).toBeTruthy();
    expect(screen.queryByText(/ETA về VN/)).toBeNull();
    expect(screen.queryByText(/Đà ở CN/)).toBeNull();
    expect(screen.queryByText(/Note văn hoá/)).toBeNull();
  });

  it("hides 'Mở trên Douyin' when douyin_url is missing", () => {
    _renderModal({ video: _video({ douyin_url: null }) });
    expect(screen.queryByRole("button", { name: /Mở trên Douyin/ })).toBeNull();
  });

  it("shows '—' for missing duration / cn_rise_pct in the stats grid", () => {
    // D7 — the stats grid uses TĂNG 14N + THỜI LƯỢNG instead of ER%;
    // both fall back to "—" when their column is null.
    _renderModal({
      video: _video({ video_duration: null, cn_rise_pct: null }),
    });
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(2);
  });

  it("falls back to title_zh when title_vi is empty", () => {
    _renderModal({
      video: _video({ title_vi: null, title_zh: "原标题" }),
    });
    // Header H2 carries the ZH title as the visible heading.
    expect(screen.getByText("原标题")).toBeTruthy();
  });

  it("renders nothing inside the dialog when video is null but open=true", () => {
    _renderModal({ video: null, open: true });
    // Modal shell still mounts (Radix portal), but body is empty —
    // none of the populated-row signals appear.
    expect(screen.queryByText(/Note văn hoá/)).toBeNull();
    expect(screen.queryByRole("button", { name: /Adapt sang VN/ })).toBeNull();
  });
});
