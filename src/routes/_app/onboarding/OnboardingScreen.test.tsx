/**
 * OnboardingScreen tests — single-niche refactor (PR3, 2026-05-05).
 *
 * Surface contracts:
 *   1. Renders the niche radio grid with hot count labels.
 *   2. Status label flips from "chưa chọn" → "đã chọn" on first pick.
 *   3. Picking a different niche replaces the previous selection (single
 *      radio semantics, not toggle).
 *   4. Primary CTA is gated on a non-null pick and saves
 *      ``primary_niche`` then navigates to /app on success.
 *   5. "Bỏ qua" navigates back to landing without writing the profile.
 *   6. Already-onboarded profiles are bounced to /app immediately.
 *   7. Taxonomy fetch error shows a retry button.
 */

import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";

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
    data: { primary_niche: null },
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

describe("OnboardingScreen — single niche pick", () => {
  it("renders niche radio grid with video counts", () => {
    render(<OnboardingScreen />);
    expect(screen.getByRole("radio", { name: /Ẩm thực/ })).toBeTruthy();
    expect(screen.getByText("1000 video")).toBeTruthy();
    expect(screen.getByText(/chưa chọn/)).toBeTruthy();
  });

  it("primary CTA stays disabled until a niche is picked", () => {
    render(<OnboardingScreen />);
    const cta = screen.getByRole("button", { name: /Vào Creator Studio/ }) as HTMLButtonElement;
    expect(cta.disabled).toBe(true);

    fireEvent.click(screen.getByRole("radio", { name: /Ẩm thực/ }));
    expect(cta.disabled).toBe(false);
    expect(screen.getByText(/đã chọn/)).toBeTruthy();
  });

  it("selecting a different niche replaces the previous pick", () => {
    render(<OnboardingScreen />);
    fireEvent.click(screen.getByRole("radio", { name: /Ẩm thực/ }));
    fireEvent.click(screen.getByRole("radio", { name: /Beauty/ }));

    const amthuc = screen.getByRole("radio", { name: /Ẩm thực/ });
    const beauty = screen.getByRole("radio", { name: /Beauty/ });
    expect(amthuc.getAttribute("aria-checked")).toBe("false");
    expect(beauty.getAttribute("aria-checked")).toBe("true");
  });

  it("primary CTA writes primary_niche + navigates to /app", async () => {
    render(<OnboardingScreen />);
    fireEvent.click(screen.getByRole("radio", { name: /Tech/ }));
    fireEvent.click(screen.getByRole("button", { name: /Vào Creator Studio/ }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
    expect(mutateAsync).toHaveBeenCalledWith({ primary_niche: 3 });
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
      data: { primary_niche: 1 },
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
});
