/** Persist intended in-app destination across OAuth (callback loses query string). */

const STORAGE_KEY = "gv:post_login_next";

/** Only same-origin app paths — blocks open redirects. */
export function sanitizePostLoginPath(raw: string | null | undefined): string {
  if (!raw) return "/app";
  let path = raw.trim();
  try {
    if (path.includes("%")) path = decodeURIComponent(path);
  } catch {
    return "/app";
  }
  // Reject protocol-relative ("//evil") and backslash variants ("/\evil",
  // which some browsers normalise to "//evil") before the /app allowlist.
  if (!path.startsWith("/") || path.startsWith("//")) return "/app";
  if (/^\/[\\/]/.test(path)) return "/app";
  if (!path.startsWith("/app")) return "/app";
  return path;
}

export function buildLoginPath(nextPath?: string): string {
  const next = sanitizePostLoginPath(nextPath ?? "/app");
  if (next === "/app") return "/login";
  return `/login?next=${encodeURIComponent(next)}`;
}

export function persistPostLoginNextFromSearch(searchParams: URLSearchParams): void {
  const raw = searchParams.get("next");
  if (!raw) {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      /* private mode */
    }
    return;
  }
  try {
    sessionStorage.setItem(STORAGE_KEY, sanitizePostLoginPath(raw));
  } catch {
    /* private mode */
  }
}

export function consumePostLoginNext(): string {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    sessionStorage.removeItem(STORAGE_KEY);
    return sanitizePostLoginPath(stored);
  } catch {
    return "/app";
  }
}

export function postLoginPathFromSearch(searchParams: URLSearchParams): string {
  const raw = searchParams.get("next");
  if (!raw) return "/app";
  return sanitizePostLoginPath(raw);
}
