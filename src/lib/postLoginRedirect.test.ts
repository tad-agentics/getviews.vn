import { describe, expect, it } from "vitest";

import {
  buildLoginPath,
  consumePostLoginNext,
  persistPostLoginNextFromSearch,
  postLoginPathFromSearch,
  sanitizePostLoginPath,
} from "./postLoginRedirect";

describe("postLoginRedirect", () => {
  it("sanitizes internal /app paths only", () => {
    expect(sanitizePostLoginPath("/app/answer?q=x")).toBe("/app/answer?q=x");
    expect(sanitizePostLoginPath("//evil.com")).toBe("/app");
    expect(sanitizePostLoginPath("https://evil.com")).toBe("/app");
    expect(sanitizePostLoginPath("/login")).toBe("/app");
    // Backslash variants browsers may normalise to protocol-relative.
    expect(sanitizePostLoginPath("/\\evil.com")).toBe("/app");
    expect(sanitizePostLoginPath("/%5cevil.com")).toBe("/app");
    expect(sanitizePostLoginPath("/\\/evil.com")).toBe("/app");
  });

  it("buildLoginPath encodes next", () => {
    expect(buildLoginPath("/app/answer?q=hi")).toBe(
      "/login?next=%2Fapp%2Fanswer%3Fq%3Dhi",
    );
    expect(buildLoginPath()).toBe("/login");
  });

  it("persists and consumes sessionStorage next", () => {
    sessionStorage.clear();
    persistPostLoginNextFromSearch(
      new URLSearchParams("next=%2Fapp%2Fanswer%3Fq%3Dx"),
    );
    expect(consumePostLoginNext()).toBe("/app/answer?q=x");
    expect(sessionStorage.getItem("gv:post_login_next")).toBeNull();
  });

  it("reads next from search params", () => {
    expect(
      postLoginPathFromSearch(new URLSearchParams("next=%2Fapp%2Fhome")),
    ).toBe("/app/home");
  });
});
