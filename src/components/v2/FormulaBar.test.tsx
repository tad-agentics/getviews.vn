import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FormulaBar } from "./FormulaBar";

describe("FormulaBar", () => {
  it("renders weighted segments when steps are provided", () => {
    const steps = [
      { step: "Hook", detail: "0–3s: câu hỏi POV", pct: 22 },
      { step: "Setup", detail: "3–8s: vấn đề", pct: 18 },
    ];
    render(<FormulaBar steps={steps} formulaGate={null} />);
    expect(screen.getByText(/Hook · 22%/)).toBeTruthy();
    expect(screen.getByText(/Setup · 18%/)).toBeTruthy();
    expect(screen.getByText("0–3s: câu hỏi POV")).toBeTruthy();
    expect(screen.getByText("3–8s: vấn đề")).toBeTruthy();
  });

  it("shows thin corpus empty copy when formula_gate is thin_corpus and no steps", () => {
    render(<FormulaBar steps={null} formulaGate="thin_corpus" />);
    expect(screen.getByText("Chưa đủ video để dựng công thức")).toBeTruthy();
  });

  it("shows generic empty copy when steps are empty and gate is null", () => {
    render(<FormulaBar steps={[]} formulaGate={null} />);
    expect(screen.getByText("Chưa có công thức")).toBeTruthy();
  });
});
