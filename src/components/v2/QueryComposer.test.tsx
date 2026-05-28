import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryComposer } from "./QueryComposer";

function renderComposer(ui: ReactElement) {
  return render(ui, {
    wrapper: ({ children }) => (
      <TooltipProvider delayDuration={0}>{children}</TooltipProvider>
    ),
  });
}

describe("QueryComposer (C.1.0)", () => {
  afterEach(cleanup);
  it("calls onSubmit when Enter is pressed with non-empty text", () => {
    const onSubmit = vi.fn();
    const onChange = vi.fn();
    renderComposer(
      <QueryComposer
        value="hello"
        onChange={onChange}
        onSubmit={onSubmit}
      />,
    );
    const ta = screen.getByPlaceholderText(/Hỏi về hook/);
    fireEvent.keyDown(ta, { key: "Enter", shiftKey: false });
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onChange).not.toHaveBeenCalled();
  });

  it("does not submit on Enter when text is empty (allows newline)", () => {
    const onSubmit = vi.fn();
    renderComposer(
      <QueryComposer value="" onChange={vi.fn()} onSubmit={onSubmit} />,
    );
    const ta = screen.getByPlaceholderText(/Hỏi về hook/);
    fireEvent.keyDown(ta, { key: "Enter", shiftKey: false });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("does not submit on Shift+Enter", () => {
    const onSubmit = vi.fn();
    renderComposer(
      <QueryComposer
        value="line"
        onChange={vi.fn()}
        onSubmit={onSubmit}
      />,
    );
    const ta = screen.getByPlaceholderText(/Hỏi về hook/);
    fireEvent.keyDown(ta, { key: "Enter", shiftKey: true });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows URL chip when showUrlChip is true", () => {
    renderComposer(
      <QueryComposer
        value="x"
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        showUrlChip
      />,
    );
    expect(screen.getByText("Đã nhận link TikTok ✓")).toBeTruthy();
  });

  it("disables Gửi and blocks submit when disabled", () => {
    const onSubmit = vi.fn();
    renderComposer(
      <QueryComposer
        value="hi"
        onChange={vi.fn()}
        onSubmit={onSubmit}
        disabled
      />,
    );
    const send = screen.getByRole("button", { name: /Gửi/i }) as HTMLButtonElement;
    expect(send.disabled).toBe(true);
    fireEvent.click(send);
    expect(onSubmit).not.toHaveBeenCalled();
    const ta = screen.getByPlaceholderText(/Hỏi về hook/);
    fireEvent.keyDown(ta, { key: "Enter", shiftKey: false });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("does not submit empty text via Gửi click", () => {
    const onSubmit = vi.fn();
    renderComposer(
      <QueryComposer value="   " onChange={vi.fn()} onSubmit={onSubmit} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Gửi/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("renders Cơ bản / Chuyên sâu depth pills by default", () => {
    renderComposer(
      <QueryComposer value="" onChange={vi.fn()} onSubmit={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: "Cơ bản" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Chuyên sâu" })).toBeTruthy();
  });

  it("wraps depth pills in Radix tooltip triggers", () => {
    renderComposer(
      <QueryComposer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        studioPill="video_flop"
        onStudioPillChange={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Cơ bản" }).getAttribute("data-slot"),
    ).toBe("tooltip-trigger");
    expect(
      screen.getByRole("button", { name: "Chuyên sâu" }).getAttribute("data-slot"),
    ).toBe("tooltip-trigger");
  });

  it("calls onAnalysisDepthChange when depth pill clicked", () => {
    const onDepth = vi.fn();
    renderComposer(
      <QueryComposer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        analysisDepth="basic"
        onAnalysisDepthChange={onDepth}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Chuyên sâu" }));
    expect(onDepth).toHaveBeenCalledWith("deep");
  });

  it("hides depth pills when studio pill is Tạo kịch bản", () => {
    renderComposer(
      <QueryComposer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        studioPill="script"
        onStudioPillChange={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: "Cơ bản" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Chuyên sâu" })).toBeNull();
  });

  it("hides depth pills when showDepthPicker is false", () => {
    renderComposer(
      <QueryComposer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        showDepthPicker={false}
      />,
    );
    expect(screen.queryByRole("button", { name: "Cơ bản" })).toBeNull();
  });

  it("updates placeholder when studioPill prop changes", () => {
    const { rerender } = renderComposer(
      <QueryComposer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        studioPill="video_flop"
        onStudioPillChange={vi.fn()}
        placeholder="Dán link video bị flop…"
      />,
    );
    expect(screen.getByPlaceholderText(/flop/)).toBeTruthy();
    rerender(
      <QueryComposer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        studioPill="channel"
        onStudioPillChange={vi.fn()}
        placeholder="Nhập @username hoặc dán link kênh TikTok…"
      />,
    );
    expect(screen.getByPlaceholderText(/kênh TikTok/)).toBeTruthy();
    expect(screen.queryByPlaceholderText(/flop/)).toBeNull();
  });

  it("renders studio intent pills when studioPill props provided", () => {
    renderComposer(
      <QueryComposer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        studioPill="channel"
        onStudioPillChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "Soi kênh đối thủ" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Phân tích video" })).toBeTruthy();
  });

  it("does not disable Chuyên sâu on Khám Kênh while credits are unknown", () => {
    renderComposer(
      <QueryComposer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        studioPill="channel"
        onStudioPillChange={vi.fn()}
      />,
    );
    const deep = screen.getByRole("button", { name: "Chuyên sâu" }) as HTMLButtonElement;
    expect(deep.disabled).toBe(false);
  });

  it("disables Chuyên sâu on Khám Kênh when credits are below channel cost", () => {
    renderComposer(
      <QueryComposer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        studioPill="channel"
        onStudioPillChange={vi.fn()}
        creditsRemaining={2}
        channelDeepCreditCost={3}
      />,
    );
    const deep = screen.getByRole("button", { name: "Chuyên sâu" }) as HTMLButtonElement;
    expect(deep.disabled).toBe(true);
  });
});
