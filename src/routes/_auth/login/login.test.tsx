import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import Login from "./route";
import { useAuth } from "@/lib/auth";
import { supabase } from "@/lib/supabase";

type OAuthResult = Awaited<ReturnType<typeof supabase.auth.signInWithOAuth>>;

function facebookButton() {
  const list = screen.getAllByRole("button", { name: /Tiếp tục với Facebook/ });
  return list.at(-1)!;
}

function googleButton() {
  const list = screen.getAllByRole("button", { name: /Tiếp tục với Google/ });
  return list.at(-1)!;
}

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      signInWithOAuth: vi.fn().mockResolvedValue({ error: null }),
    },
  },
}));

vi.mock("@/lib/auth", () => ({
  useAuth: vi.fn(),
}));

function mockLandingStats(corpus_indexed_count: number | null) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ corpus_indexed_count }),
    }),
  );
}

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );
}

describe("LoginScreen", () => {
  beforeEach(async () => {
    mockLandingStats(null);
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      session: null,
      loading: false,
      signOut: vi.fn(),
    });
    const { supabase } = await import("@/lib/supabase");
    vi.mocked(supabase.auth.signInWithOAuth).mockReset();
    vi.mocked(supabase.auth.signInWithOAuth).mockResolvedValue({
      data: { provider: "facebook", url: "" },
      error: null,
    } as OAuthResult);
  });

  it("renders Facebook and Google buttons", () => {
    renderLogin();
    expect(facebookButton()).toBeTruthy();
    expect(googleButton()).toBeTruthy();
  });

  it("shows corpus count from landing-stats fetch (floored marketing tier)", async () => {
    mockLandingStats(12_847);
    renderLogin();
    await waitFor(() => {
      expect(screen.getAllByText("12.000+").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows loading state on Facebook button click", async () => {
    const { supabase } = await import("@/lib/supabase");
    vi.mocked(supabase.auth.signInWithOAuth).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          setTimeout(
            () =>
              resolve({
                data: { provider: "facebook", url: "" },
                error: null,
              } as OAuthResult),
            250,
          );
        }),
    );
    renderLogin();
    fireEvent.click(facebookButton());
    await waitFor(() => {
      expect(screen.getByText(/Đang kết nối Facebook/)).toBeTruthy();
    });
  });

  it("calls signInWithOAuth with Google when Google button clicked", async () => {
    const { supabase } = await import("@/lib/supabase");
    renderLogin();
    fireEvent.click(googleButton());
    await waitFor(() => {
      expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith(
        expect.objectContaining({ provider: "google" }),
      );
    });
  });

  it("disables both buttons when one is loading", async () => {
    renderLogin();
    fireEvent.click(facebookButton());
    await waitFor(() => {
      const buttons = screen.getAllByRole("button");
      const disabled = buttons.filter((b) => b.hasAttribute("disabled"));
      expect(disabled.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("shows error text on OAuth failure", async () => {
    const { supabase } = await import("@/lib/supabase");
    vi.mocked(supabase.auth.signInWithOAuth).mockResolvedValueOnce({
      data: { provider: "facebook", url: null },
      error: {
        message: "OAuth failed",
        status: 400,
        name: "AuthApiError",
        code: "oauth_error",
      } as unknown as import("@supabase/supabase-js").AuthError,
    } as OAuthResult);
    renderLogin();
    fireEvent.click(facebookButton());
    await waitFor(() => {
      expect(screen.getByText(/Đăng nhập không thành công/)).toBeTruthy();
    });
  });
});
