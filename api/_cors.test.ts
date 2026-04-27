import { describe, expect, it } from "vitest";
import { buildCorsHeaders, isAllowedOrigin } from "./_cors";

describe("isAllowedOrigin", () => {
  it("accepts production hosts", () => {
    expect(isAllowedOrigin("https://getviews.vn")).toBe(true);
    expect(isAllowedOrigin("https://www.getviews.vn")).toBe(true);
  });

  it("accepts Vercel preview deploys", () => {
    expect(isAllowedOrigin("https://feature-branch-getviews.vercel.app")).toBe(true);
    expect(isAllowedOrigin("https://getviews-vn-pr-123.vercel.app")).toBe(true);
  });

  it("accepts local dev ports", () => {
    expect(isAllowedOrigin("http://localhost:5173")).toBe(true);
    expect(isAllowedOrigin("http://127.0.0.1:5173")).toBe(true);
    expect(isAllowedOrigin("http://localhost:3000")).toBe(true);
  });

  it("rejects everything else", () => {
    expect(isAllowedOrigin(null)).toBe(false);
    expect(isAllowedOrigin("")).toBe(false);
    expect(isAllowedOrigin("https://evil.example.com")).toBe(false);
    expect(isAllowedOrigin("http://getviews.vn")).toBe(false); // http, not https
    expect(isAllowedOrigin("https://getviews.vn.evil.com")).toBe(false);
    expect(isAllowedOrigin("https://fake.vercel.app.evil.com")).toBe(false);
  });
});

describe("buildCorsHeaders", () => {
  it("echoes the origin when allowed", () => {
    const req = new Request("https://api.example.com/x", {
      headers: { Origin: "https://getviews.vn" },
    });
    const headers = buildCorsHeaders(req);
    expect(headers["Access-Control-Allow-Origin"]).toBe("https://getviews.vn");
    expect(headers.Vary).toBe("Origin");
  });

  it("omits Allow-Origin when origin is not on the list", () => {
    const req = new Request("https://api.example.com/x", {
      headers: { Origin: "https://evil.example.com" },
    });
    const headers = buildCorsHeaders(req);
    expect(headers["Access-Control-Allow-Origin"]).toBeUndefined();
    expect(headers.Vary).toBe("Origin");
  });

  it("omits Allow-Origin when no Origin header is sent", () => {
    const req = new Request("https://api.example.com/x");
    const headers = buildCorsHeaders(req);
    expect(headers["Access-Control-Allow-Origin"]).toBeUndefined();
  });
});
