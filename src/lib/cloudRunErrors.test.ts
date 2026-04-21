import { describe, expect, it } from "vitest";
import { readErrorDetail } from "./cloudRunErrors";

function mockResponse(status: number, body: string): Response {
  return new Response(body, { status });
}

describe("readErrorDetail", () => {
  it("extracts FastAPI `detail` field", async () => {
    const res = mockResponse(400, JSON.stringify({ detail: "niche_id phải trùng ngách chính" }));
    expect(await readErrorDetail(res)).toBe("niche_id phải trùng ngách chính");
  });

  it("extracts our own `error` field when `detail` is absent", async () => {
    const res = mockResponse(402, JSON.stringify({ error: "insufficient_credits" }));
    expect(await readErrorDetail(res)).toBe("insufficient_credits");
  });

  it("falls through to the raw body when JSON has neither field", async () => {
    const res = mockResponse(500, JSON.stringify({ stack: "…" }));
    expect(await readErrorDetail(res)).toContain("stack");
  });

  it("falls through to the raw body when body is not JSON", async () => {
    const res = mockResponse(502, "Bad Gateway");
    expect(await readErrorDetail(res)).toBe("Bad Gateway");
  });

  it("returns HTTP <status> when body is empty", async () => {
    const res = mockResponse(503, "");
    expect(await readErrorDetail(res)).toBe("HTTP 503");
  });

  it("ignores non-string detail/error values", async () => {
    const res = mockResponse(400, JSON.stringify({ detail: 42 }));
    // Falls through to raw body since detail isn't a string.
    expect(await readErrorDetail(res)).toContain("42");
  });
});
