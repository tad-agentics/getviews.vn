/**
 * ReferenceChannelsStep — onboarding step 2 tests (Phase A · A3.1).
 *
 * Covers:
 *   1. 1–3 selection cap enforces (fourth selection disabled)
 *   2. Toggle on/off
 *   3. "Tiếp tục" writes handles via useUpdateProfile then calls onDone
 *   4. "Bỏ qua" writes an empty array then calls onDone
 *   5. Empty creator list → "chưa có danh sách gợi ý" state with onDone wired
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ── Module mocks ────────────────────────────────────────────────────────────

const mockUseStarterCreators = vi.fn();
const mockUseUpdateProfile = vi.fn();

vi.mock("@/hooks/useStarterCreators", () => ({
  useStarterCreators: () => mockUseStarterCreators(),
}));

vi.mock("@/hooks/useUpdateProfile", () => ({
  useUpdateProfile: () => mockUseUpdateProfile(),
}));

// Pull in AFTER mocks so the component picks them up.
const { ReferenceChannelsStep } = await import("./ReferenceChannelsStep");

// ── Fixtures ────────────────────────────────────────────────────────────────

const CREATORS = [
  { handle: "a", display_name: "Alpha", followers: 1_200_000, avg_views: 200_000, video_count: 20, rank: 1 },
  { handle: "b", display_name: "Bravo", followers: 900_000,   avg_views: 150_000, video_count: 18, rank: 2 },
  { handle: "c", display_name: null,    followers: 500_000,   avg_views: 100_000, video_count: 12, rank: 3 },
  { handle: "d", display_name: "Delta", followers: 300_000,   avg_views:  80_000, video_count: 10, rank: 4 },
];

// ── Helpers ─────────────────────────────────────────────────────────────────

function renderStep({ onDone = vi.fn(), onBack }: { onDone?: () => void; onBack?: () => void }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ReferenceChannelsStep onDone={onDone} onBack={onBack} />
    </QueryClientProvider>,
  );
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe("ReferenceChannelsStep", () => {
  beforeEach(() => {
    mockUseStarterCreators.mockReset();
    mockUseUpdateProfile.mockReset();
    mockUseUpdateProfile.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    });
  });

  afterEach(cleanup);

  it("caps selection at 3 creators", () => {
    mockUseStarterCreators.mockReturnValue({ data: CREATORS, isPending: false, error: null });
    renderStep({});

    fireEvent.click(screen.getByRole("button", { name: /Alpha/i }));
    fireEvent.click(screen.getByRole("button", { name: /Bravo/i }));
    fireEvent.click(screen.getByRole("button", { name: /@c/i })); // c has no display_name
    // Fourth attempt should be disabled (the row itself — not the CTA).
    const delta = screen.getByRole("button", { name: /Delta/i }) as HTMLButtonElement;
    expect(delta.disabled).toBe(true);
    expect(screen.getByText("3/3 kênh")).toBeTruthy();
  });

  it("toggles a creator off when re-clicked", () => {
    mockUseStarterCreators.mockReturnValue({ data: CREATORS, isPending: false, error: null });
    renderStep({});

    const alpha = screen.getByRole("button", { name: /Alpha/i });
    fireEvent.click(alpha);
    expect(alpha.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(alpha);
    expect(alpha.getAttribute("aria-pressed")).toBe("false");
    expect(screen.getByText("0/3 kênh")).toBeTruthy();
  });

  it("Tiếp tục commits selected handles and calls onDone", async () => {
    const onDone = vi.fn();
    const mutateAsync = vi.fn().mockResolvedValue({});
    mockUseUpdateProfile.mockReturnValue({ mutateAsync, isPending: false });
    mockUseStarterCreators.mockReturnValue({ data: CREATORS, isPending: false, error: null });
    renderStep({ onDone });

    fireEvent.click(screen.getByRole("button", { name: /Alpha/i }));
    fireEvent.click(screen.getByRole("button", { name: /Bravo/i }));

    fireEvent.click(screen.getByRole("button", { name: /Tiếp tục/i }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
    expect(mutateAsync).toHaveBeenCalledWith({ reference_channel_handles: ["a", "b"] });
    await waitFor(() => expect(onDone).toHaveBeenCalledTimes(1));
  });

  it("Bỏ qua writes an empty array", async () => {
    const onDone = vi.fn();
    const mutateAsync = vi.fn().mockResolvedValue({});
    mockUseUpdateProfile.mockReturnValue({ mutateAsync, isPending: false });
    mockUseStarterCreators.mockReturnValue({ data: CREATORS, isPending: false, error: null });
    renderStep({ onDone });

    fireEvent.click(screen.getByRole("button", { name: /Bỏ qua/i }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ reference_channel_handles: [] }));
    await waitFor(() => expect(onDone).toHaveBeenCalledTimes(1));
  });

  it("shows empty-state copy + Tiếp tục when starter list is empty", async () => {
    const onDone = vi.fn();
    const mutateAsync = vi.fn().mockResolvedValue({});
    mockUseUpdateProfile.mockReturnValue({ mutateAsync, isPending: false });
    mockUseStarterCreators.mockReturnValue({ data: [], isPending: false, error: null });
    renderStep({ onDone });

    expect(screen.getByText(/Chưa có danh sách gợi ý/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Tiếp tục/i }));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ reference_channel_handles: [] }));
    await waitFor(() => expect(onDone).toHaveBeenCalledTimes(1));
  });

  it("falls back to empty-state copy when the query errors", () => {
    mockUseStarterCreators.mockReturnValue({
      data: undefined, isPending: false, error: new Error("boom"),
    });
    renderStep({});
    expect(screen.getByText(/Chưa có danh sách gợi ý/i)).toBeTruthy();
  });
});
