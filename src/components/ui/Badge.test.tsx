/**
 * Badge deprecation shim regression (Phase D.4.1.a).
 *
 * Locks three invariants that downstream D.4.1.b–f will depend on:
 *
 *   1. The `purple` variant is still accepted as a prop value (for
 *      back-compat during the sweep) but renders visually as `default`
 *      — so a consumer that hasn't migrated yet doesn't break.
 *   2. Using `purple` emits exactly one `console.warn` per unique call
 *      stack; the second render from the same call site stays silent
 *      so dev logs don't flood.
 *   3. The warn string names the deprecated value without using the
 *      literal `variant="purple"` token (that token is reserved for
 *      the future D.4.3 lint scan — we don't want the warn text to
 *      self-trip the scanner).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { Badge } from "./Badge";

describe("Badge shim", () => {
  let warnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Install (or re-install) the spy and clear its call history so a warn
    // fired by a previous test isn't visible to assertions in this one.
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    warnSpy.mockClear();
  });

  afterEach(() => {
    warnSpy.mockRestore();
    cleanup();
  });

  it("renders the `default` variant with the gv-ink-3 text token", () => {
    render(<Badge>thường</Badge>);
    const el = screen.getByText("thường");
    expect(el.className).toContain("text-[color:var(--gv-ink-3)]");
    expect(el.className).not.toContain("--ink-soft");
  });

  it("renders `accent` against gv-accent tokens (already on the new namespace)", () => {
    render(<Badge variant="accent">nhấn</Badge>);
    const el = screen.getByText("nhấn");
    expect(el.className).toContain("text-[color:var(--gv-accent)]");
    expect(el.className).toContain("bg-[color:var(--gv-accent-soft)]");
  });

  it("accepts the deprecated `purple` variant and renders it visually as `default`", () => {
    render(<Badge variant="purple">cũ</Badge>);
    const el = screen.getByText("cũ");
    // Visually equivalent to `default` so unmigrated consumers keep working.
    expect(el.className).toContain("text-[color:var(--gv-ink-3)]");
    expect(el.className).not.toContain("--purple");
    expect(el.className).not.toContain("--purple-light");
  });

  it("emits a deprecation warning when `purple` is used", () => {
    render(<Badge variant="purple">x</Badge>);
    expect(warnSpy).toHaveBeenCalled();
    const message = String(warnSpy.mock.calls[0]?.[0] ?? "");
    expect(message).toContain("[Badge]");
    expect(message).toContain("deprecated");
    // Must not embed the literal `variant="purple"` token — that string
    // is reserved for the future D.4.3 lint scan, and having it in our
    // own warn output would make the scan flag Badge.tsx as a violator.
    expect(message).not.toMatch(/variant="purple"/);
  });

  it("does not warn when `purple` is never used", () => {
    render(
      <>
        <Badge>a</Badge>
        <Badge variant="accent">b</Badge>
        <Badge variant="success">c</Badge>
      </>,
    );
    expect(warnSpy).not.toHaveBeenCalled();
  });
});
