import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ScriptForecastBar } from "./ScriptForecastBar";

describe("ScriptForecastBar", () => {
  afterEach(cleanup);

  it("disables save when onSaveDraft is omitted", () => {
    render(<ScriptForecastBar durationSec={32} hookDelayMs={1200} />);
    const btn = screen.getByRole("button", { name: /Lưu kịch bản/i });
    expect((btn as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows Đang lưu… when savePending", () => {
    render(
      <ScriptForecastBar
        durationSec={32}
        hookDelayMs={1200}
        onSaveDraft={vi.fn()}
        savePending
      />,
    );
    expect((screen.getByRole("button", { name: /Đang lưu/i }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows Đã lưu when saved and still calls onSaveDraft when clicked", () => {
    const onSave = vi.fn();
    render(
      <ScriptForecastBar
        durationSec={32}
        hookDelayMs={1200}
        onSaveDraft={onSave}
        saved
      />,
    );
    const btn = screen.getByRole("button", { name: /Đã lưu/i });
    expect((btn as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(btn);
    expect(onSave).toHaveBeenCalledTimes(1);
  });
});
