/**
 * OnboardingScreen tests — single-step niche pick (post-design-pack collapse).
 *
 * Surface contracts:
 *   1. Renders the niche grid with hot count labels.
 *   2. Section header counter advances and turns accent-deep at the cap.
 *   3. Picker hard-caps at ONBOARDING_NICHE_PICK_CAP (3); 4th unselected
 *      tile becomes disabled.
 *   4. Primary CTA is gated on MIN_CREATOR_NICHES (3) and triggers
 *      useUpdateProfile + navigates to /app on success.
 *   5. "Bỏ qua" navigates back to landing without writing the profile.
 *   6. Already-onboarded profiles are bounced to /app immediately.
 */

import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within, fireEvent, waitFor } from "@testing-library/react";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
    VITE_R2_PUBLIC_URL: undefined,
  },
}));

const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockUseProfile = vi.fn();
const mockUseUpdateProfile = vi.fn();
const mockUseNicheTaxonomy = vi.fn();
const mockUseTopNiches = vi.fn();

vi.mock("@/hooks/useProfile", () => ({ useProfile: () => mockUseProfile() }));
vi.mock("@/hooks/useUpdateProfile", () => ({
  useUpdateProfile: () => mockUseUpdateProfile(),
}));
vi.mock("@/hooks/useNicheTaxonomy", () => ({
  useNicheTaxonomy: () => mockUseNicheTaxonomy(),
}));
vi.mock("@/hooks/useTopNiches", () => ({
  useTopNiches: () => mockUseTopNiches(),
}));

const OnboardingScreen = (await import("./OnboardingScreen")).default;

const TAXONOMY = [
  { id: 1, name: "Ẩm thực" },
  { id: 2, name: "Beauty" },
  { id: 3, name: "Tech" },
  { id: 4, name: "Du lịch" },
  { id: 5, name: "Tài chính" },
];

const TOP_NICHES = TAXONOMY.map((t, i) => ({
  id: t.id,
  name: t.name,
  hot: 1000 - i * 100,
}));

const mutateAsync = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  mockNavigate.mockReset();
  mutateAsync.mockClear();
  mockUseProfile.mockReturnValue({
    data: { primary_niche: null, niche_ids: [] },
    isPending: false,
  });
  mockUseUpdateProfile.mockReturnValue({ mutateAsync, isPending: false });
  mockUseNicheTaxonomy.mockReturnValue({
    data: TAXONOMY,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  });
  mockUseTopNiches.mockReturnValue({ data: TOP_NICHES });
});

afterEach(() => {
  cleanup();
});

describe("OnboardingScreen — single-step", () => {
  it("renders niche grid with video counts", () => {
    render(<OnboardingScreen />);
    expect(screen.getByRole("button", { name: /Ẩm thực/ })).toBeTruthy();
    expect(screen.getByText("1000 video")).toBeTruthy();
    expect(screen.getByText(/0\/3 đã chọn/)).toBeTruthy();
  });

  it("counter advances and the primary CTA stays disabled until 3 picks", () => {
    render(<OnboardingScreen />);
    const cta = screen.getByRole("button", { name: /Vào Creator Studio/ }) as HTMLButtonElement;
    expect(cta.disabled).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: /Ẩm thực/ }));
    fireEvent.click(screen.getByRole("button", { name: /Beauty/ }));
    expect(cta.disabled).toBe(true);
    expect(screen.getByText(/2\/3 đã chọn/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Tech/ }));
    expect(screen.getByText(/3\/3 đã chọn/)).toBeTruthy();
    expect(cta.disabled).toBe(false);
  });

  it("hard-caps the picker at 3 — extra unselected tiles are disabled", () => {
    render(<OnboardingScreen />);
    fireEvent.click(screen.getByRole("button", { name: /Ẩm thực/ }));
    fireEvent.click(screen.getByRole("button", { name: /Beauty/ }));
    fireEvent.click(screen.getByRole("button", { name: /Tech/ }));

    const dulich = screen.getByRole("button", { name: /Du lịch/ }) as HTMLButtonElement;
    const taichinh = screen.getByRole("button", { name: /Tài chính/ }) as HTMLButtonElement;
    expect(dulich.disabled).toBe(true);
    expect(taichinh.disabled).toBe(true);
  });

  it("primary CTA writes profile + navigates to /app", async () => {
    render(<OnboardingScreen />);
    fireEvent.click(screen.getByRole("button", { name: /Ẩm thực/ }));
    fireEvent.click(screen.getByRole("button", { name: /Beauty/ }));
    fireEvent.click(screen.getByRole("button", { name: /Tech/ }));
    fireEvent.click(screen.getByRole("button", { name: /Vào Creator Studio/ }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
    expect(mutateAsync).toHaveBeenCalledWith({
      niche_ids: [1, 2, 3],
      primary_niche: 1,
    });
    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith("/app", { replace: true }),
    );
  });

  it("Bỏ qua skips back to landing without writing the profile", () => {
    render(<OnboardingScreen />);
    fireEvent.click(screen.getByRole("button", { name: /Bỏ qua/ }));
    expect(mutateAsync).not.toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
  });

  it("bounces already-onboarded profiles straight to /app", () => {
    mockUseProfile.mockReturnValue({
      data: { primary_niche: 1, niche_ids: [1, 2, 3] },
      isPending: false,
    });
    render(<OnboardingScreen />);
    expect(mockNavigate).toHaveBeenCalledWith("/app", { replace: true });
  });

  it("shows error state with retry when taxonomy fetch fails", () => {
    const refetch = vi.fn();
    mockUseNicheTaxonomy.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      refetch,
    });
    render(<OnboardingScreen />);
    const retry = screen.getByRole("button", { name: /Thử lại/ });
    fireEvent.click(retry);
    expect(refetch).toHaveBeenCalled();
  });

  // Section-header counter colour: accent-deep when at cap, ink-4 otherwise.
  // We assert by reading the className token rather than a computed colour.
  it("counter switches to accent class when at cap", () => {
    render(<OnboardingScreen />);
    fireEvent.click(screen.getByRole("button", { name: /Ẩm thực/ }));
    fireEvent.click(screen.getByRole("button", { name: /Beauty/ }));
    fireEvent.click(screen.getByRole("button", { name: /Tech/ }));
    const counter = screen.getByText(/3\/3 đã chọn/);
    expect(counter.className).toMatch(/gv-accent-deep/);
  });
});
