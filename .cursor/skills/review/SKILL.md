---
name: review
description: Pre-handoff production safety audit — two-pass security and quality check before deploying. Invoked by the QA Agent during pre-handoff mode.
disable-model-invocation: true
---

# Review — Pre-Handoff Production Safety Audit

First, run the automated pre-handoff checks:

```bash
bash .cursor/skills/review/scripts/pre-handoff-check.sh
```

Resolve all BLOCKING findings from the script before continuing to the manual passes below.

Then run two passes against the complete codebase:

## Pass 1 — Critical (fix before handoff)

- N+1 queries: any list or feed screen fetching related data in a loop instead of a single query with joins/selects?
- Race conditions: any write operation (form submit, toggle, delete) that can be double-triggered?
- Trust boundaries: any user-provided input used in a query, LLM prompt, or file path without validation?
- RLS gaps: any table where a user could read or write another user's rows by manipulating IDs? Run `SELECT tablename FROM pg_tables WHERE schemaname = 'public'` and verify every table has RLS enabled.
- Orphaned records: any write that can fail mid-operation and leave dangling data with no cleanup?
- LLM output trust: any LLM response written to the database without type-checking or schema validation?
- Secrets in bundle: check `dist/` build output — no `SUPABASE_SERVICE_ROLE_KEY`, payment secrets, or other server-only values present. Only `VITE_` prefixed values should appear.
- Auth guard completeness: every route under `src/routes/_app/` must be a child of the auth-guarded layout. No unauthenticated access to app screens.
- Edge Function validation: every Edge Function uses zod for input validation and returns structured errors — no raw exceptions leaked to caller.
- Paywall gate integrity: any screen with a credit cost in screen spec metadata that can be bypassed (result visible without payment, credit not deducted, negative balance possible)?
- Interaction flow completeness: any branch condition in screen spec metadata (credit check, profile exists) that has no corresponding code path?
- Copy-rules compliance: any visible copy string that uses a forbidden word, forbidden opening, or fails the 5-question quality test from `copy-rules.mdc`?
- SEO infrastructure: are `public/sitemap.xml`, `public/robots.txt`, `public/manifest.json` all present? Does the pre-rendered landing page at `/` contain full HTML with meta tags (view source check)?
- Landing page completeness: does `src/routes/_index/route.tsx` render all 8 sections from the screen spec? Does the install prompt fire? Does FAQ JSON-LD render?

## Pass 2 — Informational (log, fix if low-effort)

- Missing indexes on foreign keys used in WHERE clauses
- Error degradation: does any partial failure silently save garbage instead of rolling back?
- Dead code: any component, function, or route not reachable from any screen in the build?
- Dead hooks: any hook in `src/hooks/` not imported by any route or component?
- Enum completeness: any new status/type value that isn't handled in all places sibling values are handled?
- Stale comments or ASCII diagrams in files changed during this build
- Edge Function deployment: do all functions in `supabase/functions/` deploy cleanly with `supabase functions serve`?
- OG image quality: does the OG image render Vietnamese diacritics correctly? Is the font file present?
- PWA manifest completeness: does `public/manifest.json` include `screenshots` with `form_factor: 'narrow'`? Is `start_url` pointing to the authenticated app, not the landing page?
- Offline fallback: does the service worker serve an offline fallback page when network is unavailable?

For each finding: classify as AUTO-FIX (apply directly) or BLOCKING (requires decision before handoff).
