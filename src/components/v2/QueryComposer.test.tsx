import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { QueryComposer } from "./QueryComposer";

describe("QueryComposer (C.1.0)", () => {
  afterEach(cleanup);
  it("calls onSubmit when Enter is pressed with non-empty text", () => {
    const onSubmit = vi.fn();
    const onChange = vi.fn();
    render(
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
    render(
      <QueryComposer value="" onChange={vi.fn()} onSubmit={onSubmit} />,
    );
    const ta = screen.getByPlaceholderText(/Hỏi về hook/);
    fireEvent.keyDown(ta, { key: "Enter", shiftKey: false });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("does not submit on Shift+Enter", () => {
    const onSubmit = vi.fn();
    render(
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
    render(
      <QueryComposer
        value="x"
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        showUrlChip
      />,
    );
    expect(screen.getByText("URL detected")).toBeTruthy();
  });

  it("disables Gửi and blocks submit when disabled", () => {
    const onSubmit = vi.fn();
    render(
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
    render(
      <QueryComposer value="   " onChange={vi.fn()} onSubmit={onSubmit} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Gửi/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("renders Cơ bản / Chuyên sâu depth pills by default", () => {
    render(
      <QueryComposer value="" onChange={vi.fn()} onSubmit={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: "Cơ bản" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Chuyên sâu" })).toBeTruthy();
  });

  it("calls onAnalysisDepthChange when depth pill clicked", () => {
    const onDepth = vi.fn();
    render(
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

  it("hides depth pills when showDepthPicker is false", () => {
    render(
      <QueryComposer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        showDepthPicker={false}
      />,
    );
    expect(screen.queryByRole("button", { name: "Cơ bản" })).toBeNull();
  });

  it("renders studio intent pills when studioPill props provided", () => {
    render(
      <QueryComposer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        studioPill="channel"
        onStudioPillChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "Khám Kênh" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Khám Video flop" })).toBeTruthy();
  });

  it("disables Chuyên sâu on Khám Kênh when credits are below channel cost", () => {
    render(
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
