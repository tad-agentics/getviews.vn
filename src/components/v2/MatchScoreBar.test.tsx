import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MatchScoreBar } from "./MatchScoreBar";

describe("MatchScoreBar", () => {
  it("clamps above 100", () => {
    const { getByText } = render(<MatchScoreBar match={142} />);
    expect(getByText("100")).toBeTruthy();
  });

  it("clamps below 0", () => {
    const { getByText } = render(<MatchScoreBar match={-5} />);
    expect(getByText("0")).toBeTruthy();
  });

  it("renders whole score", () => {
    const { getByText } = render(<MatchScoreBar match={67.6} />);
    expect(getByText("68")).toBeTruthy();
  });
});
