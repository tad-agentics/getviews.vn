/**
 * authErrors — pin the `SessionExpired` contract the global listener
 * in AuthProvider depends on. The listener branches on
 * `err.name === "SessionExpired"` to decide whether to sign out; a
 * rename or typo in `throwSessionExpired` would silently break the
 * auto-logout flow and leave users stuck on a 401 banner.
 */
import { describe, expect, it } from "vitest";
import { isSessionExpired, throwSessionExpired } from "./authErrors";

describe("throwSessionExpired", () => {
  it("throws a named SessionExpired error with the given reason as message", () => {
    expect(() => throwSessionExpired("401_from_cloud_run")).toThrow();
    try {
      throwSessionExpired("401_from_cloud_run");
    } catch (e) {
      expect(e).toBeInstanceOf(Error);
      expect((e as Error).name).toBe("SessionExpired");
      expect((e as Error).message).toBe("401_from_cloud_run");
    }
  });

  it("falls back to 'session_expired' message when reason is empty", () => {
    try {
      throwSessionExpired("");
    } catch (e) {
      expect((e as Error).message).toBe("session_expired");
    }
  });
});

describe("isSessionExpired", () => {
  it("returns true for errors named SessionExpired", () => {
    const e = new Error("x");
    e.name = "SessionExpired";
    expect(isSessionExpired(e)).toBe(true);
  });

  it("returns false for other errors", () => {
    const e = new Error("x");
    e.name = "InsufficientCredits";
    expect(isSessionExpired(e)).toBe(false);
  });

  it("returns false for non-Error values", () => {
    expect(isSessionExpired("session_expired")).toBe(false);
    expect(isSessionExpired(null)).toBe(false);
    expect(isSessionExpired(undefined)).toBe(false);
  });
});
