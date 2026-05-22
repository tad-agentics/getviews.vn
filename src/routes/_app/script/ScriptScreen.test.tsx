/**
 * ScriptScreen — Wave 2 redirect-only route tests.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useSearchParams } from "react-router";

const ScriptScreen = (await import("./ScriptScreen")).default;

function AnswerCapture() {
  const [params] = useSearchParams();
  return <div data-testid="q">{params.get("q")}</div>;
}

describe("ScriptScreen redirects", () => {
  it("bare /app/script redirects to /app/answer", () => {
    render(
      <MemoryRouter initialEntries={["/app/script"]}>
        <Routes>
          <Route path="/app/script" element={<ScriptScreen />} />
          <Route path="/app/answer" element={<div data-testid="answer-landing">answer</div>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("answer-landing")).toBeTruthy();
  });

  it("?topic= deeplink redirects to Answer with ?q= prefill", () => {
    render(
      <MemoryRouter initialEntries={["/app/script?topic=Test+topic"]}>
        <Routes>
          <Route path="/app/script" element={<ScriptScreen />} />
          <Route path="/app/answer" element={<AnswerCapture />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("q").textContent).toContain("Test topic");
  });
});
