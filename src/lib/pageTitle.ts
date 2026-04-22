/**
 * Vietnamese page titles for ``/app/*`` routes.
 *
 * Prior state: every /app/* route.tsx omitted ``export const meta``, so
 * ``document.title`` was the empty string set by the prerendered landing
 * page shell. Browser tabs showed "GetViews" or worse — the URL — and the
 * history API had no way to distinguish routes (BUG-18 in QA audit
 * 2026-04-22).
 *
 * Consuming site: each route.tsx calls ``pageMeta(suffix)`` from its
 * ``meta`` export. React Router v7's ``<Meta />`` (rendered in root.tsx)
 * picks up the title at hydration in SPA mode.
 */
export const APP_TITLE_BASE = "GetViews";

export function pageTitle(suffix?: string | null): string {
  const s = (suffix ?? "").trim();
  return s ? `${s} — ${APP_TITLE_BASE}` : APP_TITLE_BASE;
}

/** Meta-array helper: returns a single ``title`` tag. */
export function pageMeta(suffix?: string | null): [{ title: string }] {
  return [{ title: pageTitle(suffix) }];
}
