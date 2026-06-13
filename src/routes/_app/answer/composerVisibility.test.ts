import { describe, expect, it } from "vitest";

import {
  computeComposerVisibility,
  type ComposerVisibilityInput,
} from "./composerVisibility";

const base: ComposerVisibilityInput = {
  streamStatus: "idle",
  turnCount: 0,
  bootstrapLoading: false,
  hasSessionId: false,
  detailLoading: false,
  hasDetailData: false,
};

describe("computeComposerVisibility", () => {
  it("shows the start composer on a fresh idle screen with no turns", () => {
    const v = computeComposerVisibility(base);
    expect(v.streamInFlight).toBe(false);
    expect(v.loading).toBe(false);
    expect(v.showStartComposer).toBe(true);
  });

  it("hides the composer while the SSE stream is streaming", () => {
    const v = computeComposerVisibility({ ...base, streamStatus: "streaming" });
    expect(v.streamInFlight).toBe(true);
    expect(v.showStartComposer).toBe(false);
  });

  it("treats done-with-zero-turns as still in flight (turn not yet persisted)", () => {
    // The report streamed but the detail query hasn't refetched the saved turn —
    // showing the composer here would flash the empty state over a real answer.
    const v = computeComposerVisibility({ ...base, streamStatus: "done", turnCount: 0 });
    expect(v.streamInFlight).toBe(true);
    expect(v.loading).toBe(true);
    expect(v.showStartComposer).toBe(false);
  });

  it("does NOT treat done-with-turns as in flight (persisted answer is visible)", () => {
    const v = computeComposerVisibility({ ...base, streamStatus: "done", turnCount: 1 });
    expect(v.streamInFlight).toBe(false);
    expect(v.loading).toBe(false);
    // turnCount > 0 → follow-up surface owns the composer, not the start composer.
    expect(v.showStartComposer).toBe(false);
  });

  it("hides the composer during bootstrap loading", () => {
    const v = computeComposerVisibility({ ...base, bootstrapLoading: true });
    expect(v.loading).toBe(true);
    expect(v.showStartComposer).toBe(false);
  });

  it("counts an unresolved session detail query as loading only with a session id", () => {
    const withSession = computeComposerVisibility({
      ...base,
      hasSessionId: true,
      detailLoading: true,
      hasDetailData: false,
    });
    expect(withSession.loading).toBe(true);
    expect(withSession.showStartComposer).toBe(false);

    // No session id → a pending detail query must not block the empty-state composer.
    const noSession = computeComposerVisibility({
      ...base,
      hasSessionId: false,
      detailLoading: true,
      hasDetailData: false,
    });
    expect(noSession.loading).toBe(false);
    expect(noSession.showStartComposer).toBe(true);
  });

  it("stops treating the detail query as loading once data has arrived", () => {
    const v = computeComposerVisibility({
      ...base,
      hasSessionId: true,
      detailLoading: true,
      hasDetailData: true,
    });
    expect(v.loading).toBe(false);
  });

  it("keeps the composer hidden on stream error with no persisted turn", () => {
    // Error state is not "in flight", so the composer can return — the error
    // banner + retry live alongside it. turnCount 0 → start composer eligible.
    const v = computeComposerVisibility({ ...base, streamStatus: "error", turnCount: 0 });
    expect(v.streamInFlight).toBe(false);
    expect(v.showStartComposer).toBe(true);
  });
});
