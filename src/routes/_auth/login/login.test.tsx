import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import Login from "./route";
import { useAuth } from "@/lib/auth";

function facebookButton() {
  const list = screen.getAllByRole("button", { name: /Đăng nhập với Facebook/ });
  return list.at(-1)!;
}

function googleButton() {
  const list = screen.getAllByRole("button", { name: /Đăng nhập với Google/ });
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

describe("LoginScreen", () => {
  beforeEach(async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      session: null,
      loading: false,
      signOut: vi.fn(),
    });
    const { supabase } = await import("@/lib/supabase");
    vi.mocked(supabase.auth.signInWithOAuth).mockReset();
    vi.mocked(supabase.auth.signInWithOAuth).mockResolvedValue({ data: { provider: "facebook", url: null }, error: null });
  });

  it("renders Facebook and Google buttons", () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );
    expect(facebookButton()).toBeTruthy();
    expect(googleButton()).toBeTruthy();
  });

  it("shows loading state on Facebook button click", async () => {
    const { supabase } = await import("@/lib/supabase");
    vi.mocked(supabase.auth.signInWithOAuth).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          setTimeout(() => resolve({ data: { provider: "facebook", url: null }, error: null }), 250);
        }),
    );
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );
    fireEvent.click(facebookButton());
    await waitFor(() => {
      expect(screen.getByText(/Đang kết nối Facebook/)).toBeTruthy();
    });
  });

  it("calls signInWithOAuth with Google when Google button clicked", async () => {
    const { supabase } = await import("@/lib/supabase");
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );
    fireEvent.click(googleButton());
    await waitFor(() => {
      expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith(
        expect.objectContaining({ provider: "google" }),
      );
    });
  });

  it("disables both buttons when one is loading", async () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );
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
        __isAuthError: true,
      } as import("@supabase/supabase-js").AuthError,
    });
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );
    fireEvent.click(facebookButton());
    await waitFor(() => {
      expect(screen.getByText(/Đăng nhập không thành công/)).toBeTruthy();
    });
  });
});
