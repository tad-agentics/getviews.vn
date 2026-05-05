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
const mockUseCreatorNiches = vi.fn();

vi.mock("@/hooks/useProfile", () => ({ useProfile: () => mockUseProfile() }));
vi.mock("@/hooks/useUpdateProfile", () => ({
  useUpdateProfile: () => mockUseUpdateProfile(),
}));
vi.mock("@/hooks/useCreatorNiches", () => ({
  useCreatorNiches: () => mockUseCreatorNiches(),
}));

const OnboardingScreen = (await import("./OnboardingScreen")).default;

// Mirrors the seeded creator_niches in
// 20260510000000_two_axis_niche_pr1_schema.sql for the picker.
const CREATOR_NICHES = [
  { id: 1, slug: "beauty", name: "Làm đẹp · Skincare", description: "Skincare routine, makeup, review.", display_order: 10 },
  { id: 3, slug: "food", name: "Ẩm thực · Ăn uống", description: "Review quán, công thức, ăn vặt.", display_order: 30 },
  { id: 8, slug: "tech_gaming", name: "Công nghệ · Gaming", description: "Review gadget, gameplay.", display_order: 80 },
  { id: 11, slug: "travel", name: "Du lịch · Thể thao", description: "Du lịch, marathon, trekking.", display_order: 110 },
  { id: 9, slug: "business", name: "Kinh doanh · Tài chính", description: "Affiliate, đầu tư, BĐS.", display_order: 90 },
];

const mutateAsync = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  mockNavigate.mockReset();
  mutateAsync.mockClear();
  mockUseProfile.mockReturnValue({
    data: { primary_niche: null },
    isPending: false,
  });
  mockUseUpdateProfile.mockReturnValue({ mutateAsync, isPending: false });
  mockUseCreatorNiches.mockReturnValue({
    data: CREATOR_NICHES,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  });
});

afterEach(() => {
  cleanup();
});

describe("OnboardingScreen — single creator-niche pick", () => {
  it("renders creator-niche radio grid with descriptions", () => {
    render(<OnboardingScreen />);
    expect(screen.getByRole("radio", { name: /Ẩm thực · Ăn uống/ })).toBeTruthy();
    expect(screen.getByText(/Skincare routine/)).toBeTruthy();
    expect(screen.getByText(/chưa chọn/)).toBeTruthy();
  });

  it("primary CTA stays disabled until a niche is picked", () => {
    render(<OnboardingScreen />);
    const cta = screen.getByRole("button", { name: /Vào Creator Studio/ }) as HTMLButtonElement;
    expect(cta.disabled).toBe(true);

    fireEvent.click(screen.getByRole("radio", { name: /Ẩm thực · Ăn uống/ }));
    expect(cta.disabled).toBe(false);
    expect(screen.getByText(/đã chọn/)).toBeTruthy();
  });

  it("selecting a different niche replaces the previous pick", () => {
    render(<OnboardingScreen />);
    fireEvent.click(screen.getByRole("radio", { name: /Ẩm thực · Ăn uống/ }));
    fireEvent.click(screen.getByRole("radio", { name: /Làm đẹp · Skincare/ }));

    const food = screen.getByRole("radio", { name: /Ẩm thực · Ăn uống/ });
    const beauty = screen.getByRole("radio", { name: /Làm đẹp · Skincare/ });
    expect(food.getAttribute("aria-checked")).toBe("false");
    expect(beauty.getAttribute("aria-checked")).toBe("true");
  });

  it("primary CTA dual-writes creator_niche_id + legacy primary_niche, then navigates", async () => {
    render(<OnboardingScreen />);
    // creator_niche_id 8 (tech_gaming) → legacy primary_niche 9 (Tech)
    fireEvent.click(screen.getByRole("radio", { name: /Công nghệ · Gaming/ }));
    fireEvent.click(screen.getByRole("button", { name: /Vào Creator Studio/ }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
    expect(mutateAsync).toHaveBeenCalledWith({
      creator_niche_id: 8,
      primary_niche: 9,
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

  it("bounces already-onboarded profiles (creator_niche_id set) straight to /app", () => {
    mockUseProfile.mockReturnValue({
      data: { primary_niche: null, creator_niche_id: 1 },
      isPending: false,
    });
    render(<OnboardingScreen />);
    expect(mockNavigate).toHaveBeenCalledWith("/app", { replace: true });
  });

  it("bounces already-onboarded legacy profiles (primary_niche only) to /app", () => {
    mockUseProfile.mockReturnValue({
      data: { primary_niche: 4, creator_niche_id: null },
      isPending: false,
    });
    render(<OnboardingScreen />);
    expect(mockNavigate).toHaveBeenCalledWith("/app", { replace: true });
  });

  it("shows error state with retry when niches fetch fails", () => {
    const refetch = vi.fn();
    mockUseCreatorNiches.mockReturnValue({
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
