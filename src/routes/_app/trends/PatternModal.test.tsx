/**
 * PR-T4 Trends — PatternModal render-test.
 *
 * Reference: design pack ``screens/trends.jsx`` lines 652-946.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TopPattern } from "@/hooks/useTopPatterns";
import { PatternModal } from "./PatternModal";

afterEach(() => {
  cleanup();
});

const samplePattern = (overrides: Partial<TopPattern> = {}): TopPattern => ({
  id: "p1",
  display_name: "Sau ___ tháng dùng",
  weekly_instance_count: 12,
  weekly_instance_count_prev: 4,
  instance_count: 47,
  niche_spread: [4],
  avg_views: 142_000,
  sample_hook: "Mình dùng iPad Pro 6 tháng rồi và…",
  videos: [
    {
      video_id: "v1",
      thumbnail_url: "https://t/1.jpg",
      creator_handle: "an.tech",
      views: 250_000,
      tiktok_url: null,
    },
    {
      video_id: "v2",
      thumbnail_url: null,
      creator_handle: "huy.codes",
      views: 180_000,
      tiktok_url: null,
    },
    {
      video_id: "v3",
      thumbnail_url: "https://t/3.jpg",
      creator_handle: "@chinasecrets",
      views: 90_000,
      tiktok_url: null,
    },
  ],
  structure: null,
  why: null,
  careful: null,
  angles: null,
  ...overrides,
});

function wrap(node: React.ReactNode) {
  return render(<MemoryRouter>{node}</MemoryRouter>);
}

describe("PatternModal — closed state", () => {
  it("renders nothing when open=false", () => {
    const { queryByText } = wrap(
      <PatternModal pattern={samplePattern()} open={false} onOpenChange={() => {}} />,
    );
    expect(queryByText("Sau ___ tháng dùng")).toBeNull();
  });

  it("renders nothing when pattern is null", () => {
    const { queryByText } = wrap(
      <PatternModal pattern={null} open onOpenChange={() => {}} />,
    );
    expect(queryByText("PATTERN ·")).toBeNull();
  });
});

describe("PatternModal — open state", () => {
  it("renders the header kicker, title, and sample-hook description", () => {
    const { getByText, getAllByText } = wrap(
      <PatternModal pattern={samplePattern()} open onOpenChange={() => {}} />,
    );
    expect(getByText(/PATTERN · 47 VIDEO · 142\.0K VIEW TB/)).toBeTruthy();
    expect(getByText("Sau ___ tháng dùng")).toBeTruthy();
    // Sample hook appears in the description AND inside the takeaway —
    // expect ≥ 1.
    expect(getAllByText(/Mình dùng iPad Pro 6 tháng/).length).toBeGreaterThan(0);
  });

  it("renders the takeaway / structure / gap-angles stub blocks", () => {
    const { getByText } = wrap(
      <PatternModal pattern={samplePattern()} open onOpenChange={() => {}} />,
    );
    expect(getByText("Ý CHÍNH")).toBeTruthy();
    expect(getByText("CẤU TRÚC ĐIỂN HÌNH")).toBeTruthy();
    expect(getByText("GÓC CÒN TRỐNG")).toBeTruthy();
    // Stub copy explicitly says these sections are coming.
    expect(getByText(/biên tập đang tổng hợp/)).toBeTruthy();
  });

  it("renders the sample switcher when ≥ 2 videos are available", () => {
    const { getByText, getAllByLabelText } = wrap(
      <PatternModal pattern={samplePattern()} open onOpenChange={() => {}} />,
    );
    expect(getByText(/CHUYỂN VIDEO \(1\/3\)/)).toBeTruthy();
    expect(getAllByLabelText(/Mẫu \d+/).length).toBe(3);
  });

  it("hides the sample switcher when only one video is present", () => {
    const onePattern = samplePattern({
      videos: [samplePattern().videos[0]],
    });
    const { queryByText } = wrap(
      <PatternModal pattern={onePattern} open onOpenChange={() => {}} />,
    );
    expect(queryByText(/CHUYỂN VIDEO/)).toBeNull();
  });

  it("clicking a sample thumbnail switches the active video", () => {
    const { getByLabelText, getAllByText } = wrap(
      <PatternModal pattern={samplePattern()} open onOpenChange={() => {}} />,
    );
    const initialHandles = getAllByText(/^@an\.tech$/);
    expect(initialHandles.length).toBeGreaterThan(0);
    fireEvent.click(getByLabelText("Mẫu 2"));
    // After switch, the phone tile shows huy.codes.
    expect(getAllByText(/^@huy\.codes$/).length).toBeGreaterThan(0);
  });

  it("close button calls onOpenChange(false)", () => {
    const onChange = vi.fn();
    const { getByLabelText } = wrap(
      <PatternModal pattern={samplePattern()} open onOpenChange={onChange} />,
    );
    fireEvent.click(getByLabelText("Đóng"));
    expect(onChange).toHaveBeenCalledWith(false);
  });

  it("embeds TikTok player in-modal when video_id is a numeric aweme id", () => {
    const p = samplePattern({
      videos: [
        {
          video_id: "7349098765432101123",
          thumbnail_url: "https://t/1.jpg",
          creator_handle: "an.tech",
          views: 250_000,
          tiktok_url: null,
        },
        ...samplePattern().videos.slice(1),
      ],
    });
    wrap(<PatternModal pattern={p} open onOpenChange={() => {}} />);
    const iframe = document.body.querySelector(
      'iframe[src*="tiktok.com/embed/v2/7349098765432101123"]',
    );
    expect(iframe).toBeTruthy();
  });

  it("renders a 'no video' fallback when pattern has zero videos", () => {
    const empty = samplePattern({ videos: [] });
    const { getByText } = wrap(
      <PatternModal pattern={empty} open onOpenChange={() => {}} />,
    );
    expect(getByText(/Chưa có video mẫu/)).toBeTruthy();
  });

  it("normalises bare creator handles with leading @ in the phone tile", () => {
    const { getByText } = wrap(
      <PatternModal pattern={samplePattern()} open onOpenChange={() => {}} />,
    );
    // First video has bare "an.tech" — renders with @ prefix.
    expect(getByText("@an.tech")).toBeTruthy();
  });
});

describe("PatternModal — deck content (post-synth)", () => {
  it("renders the real why + careful in Ý CHÍNH when both are set", () => {
    const decked = samplePattern({
      why: "Format thử-thách-thời-gian tạo curiosity sâu — audience muốn biết kết quả cuối.",
      careful: "Nếu chưa thực sự dùng X tháng, đừng giả — comment sẽ phát hiện.",
    });
    const { getByText, queryByText } = wrap(
      <PatternModal pattern={decked} open onOpenChange={() => {}} />,
    );
    expect(getByText(/Format thử-thách-thời-gian/)).toBeTruthy();
    expect(getByText(/đừng giả/)).toBeTruthy();
    // Stub fallback line is hidden when deck is populated.
    expect(queryByText(/Cấu trúc chi tiết và góc còn trống đang được biên tập/)).toBeNull();
  });

  it("renders the structure as an ordered list when populated", () => {
    const decked = samplePattern({
      structure: [
        "Mở: câu hỏi 'tôi đã dùng X' (0-2s)",
        "Setup: nghi vấn (2-8s)",
        "Body: 3 điểm (8-35s)",
        "Payoff: verdict + CTA (35-50s)",
      ],
    });
    const { getByText } = wrap(
      <PatternModal pattern={decked} open onOpenChange={() => {}} />,
    );
    // Each step renders.
    expect(getByText(/Mở: câu hỏi/)).toBeTruthy();
    expect(getByText(/Payoff: verdict/)).toBeTruthy();
    // Radix Dialog renders into a portal so query at the document
    // level. Structural ol with 4 items.
    const ol = document.querySelector("ol");
    expect(ol).toBeTruthy();
    expect(ol?.children.length).toBe(4);
  });

  it("renders only the gap angles in GÓC CÒN TRỐNG with a count badge", () => {
    const decked = samplePattern({
      angles: [
        { angle: "Sản phẩm Apple", filled: 18, gap: false },
        { angle: "Phụ kiện cao cấp", filled: 0, gap: true },
        { angle: "Hệ điều hành", filled: 0, gap: true },
        { angle: "AI tools", filled: 14, gap: false },
      ],
    });
    const { getByText, queryByText } = wrap(
      <PatternModal pattern={decked} open onOpenChange={() => {}} />,
    );
    expect(getByText(/2 cơ hội/)).toBeTruthy();
    expect(getByText("Phụ kiện cao cấp")).toBeTruthy();
    expect(getByText("Hệ điều hành")).toBeTruthy();
    // Filled angles do NOT render in the gap list.
    expect(queryByText("Sản phẩm Apple")).toBeNull();
    expect(queryByText("AI tools")).toBeNull();
  });

  it("renders the 'no gaps' message when angles is populated but gap-free", () => {
    const decked = samplePattern({
      angles: [
        { angle: "Sản phẩm Apple", filled: 18, gap: false },
        { angle: "AI tools", filled: 14, gap: false },
      ],
    });
    const { getByText } = wrap(
      <PatternModal pattern={decked} open onOpenChange={() => {}} />,
    );
    expect(getByText(/đã có creator khai thác/)).toBeTruthy();
  });
});
