import { describe, expect, it } from "vitest";

import { resolveLandingHeroSubmit } from "./landingHeroCta";

describe("resolveLandingHeroSubmit", () => {
  it("routes valid TikTok URL to login with answer handoff", () => {
    const url = "https://www.tiktok.com/@creator/video/7615811534962330901";
    const result = resolveLandingHeroSubmit(url);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.loginPath).toContain("/login?next=");
      const next = new URL(result.loginPath, "https://getviews.vn").searchParams.get("next");
      expect(next).toContain("from=landing");
      expect(next).toContain(url);
    }
  });

  it("blocks non-TikTok URL with Vietnamese error", () => {
    const result = resolveLandingHeroSubmit("https://www.youtube.com/watch?v=abc");
    expect(result).toEqual({
      ok: false,
      error: expect.stringMatching(/link TikTok/i),
    });
  });

  it("allows empty paste → login without next", () => {
    const result = resolveLandingHeroSubmit("   ");
    expect(result).toEqual({ ok: true, loginPath: "/login" });
  });
});
