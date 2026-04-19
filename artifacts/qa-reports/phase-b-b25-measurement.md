# B.2.5 — `/kol` measurement + smoke

**Date:** 2026-04-19  
**Plan:** `artifacts/plans/phase-b-plan.md` §Measurement + Testing strategy.

## `usage_events` (via `logUsage`)

| `action` | When | `metadata` (keys) |
|----------|------|-------------------|
| `kol_screen_load` | Successful browse fetch (`KolScreen`) | `tab`, `niche_id`, `page`, `total`, `sort`, `order_dir`, `followers`, `growth_fast` |
| `kol_pin` | After successful `togglePin.mutateAsync` | `handle`, `tab` |

`kol_to_channel` is reserved for when **Phân tích kênh đầy đủ** routes to `/app/channel` (B.3).

## Shell smoke

- **Script:** `artifacts/qa-reports/smoke-kol.sh` (executable)
- **Requires:** `curl`, `jq`, env `JWT`, `CLOUD_RUN_URL`
- **Checks:** `GET /kol/browse?tab=discover&page=1&page_size=5&sort=match&order_dir=desc` → HTTP 200 and JSON keys `rows`, `total`, `reference_handles`.

## Status

**GREEN** — instrumentation and smoke script shipped.
