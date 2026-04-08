---
name: caching-strategies
description: Cache-aside discipline for RAD — maps TTL tiers, invalidation, fail-open behavior, volatile-field rules, and stampede awareness to TanStack React Query (web + shared hooks), Supabase, Edge Functions, and optional server Redis. Use when tuning staleTime, designing mutations, adding Edge caches, or reviewing data freshness.
---

# Caching strategies — RAD adaptation

## How this complements TanStack Query

**TanStack Query is RAD’s client cache.** `staleTime`, `gcTime`, `queryKey`, `invalidateQueries`, prefetch, and `QueryClient` defaults are specified in **`.cursor/rules/frontend-data.mdc`** with concrete hook patterns.

**This skill does not replace that.** It adds a **cross-layer vocabulary** (TTL tiers ↔ `staleTime`, write invalidation ↔ `onSuccess` query keys, volatile data ↔ short stale + Realtime, thundering herd ↔ in-flight query deduplication) and covers **Edge / optional server cache** so those layers don’t contradict what React Query already holds.

Use **`frontend-data.mdc`** to implement; use **this skill** when reasoning about freshness, invalidation scope, or server-side caching.

---

## Where caching lives in RAD

| Layer | Mechanism | Canonical rules |
| --- | --- | --- |
| **Browser / native client** | TanStack React Query (`staleTime`, `gcTime`, `queryKey`, `invalidateQueries`) | `.cursor/rules/frontend-data.mdc` — hooks in `src/hooks/` and `shared/hooks/` |
| **Database** | Source of truth; `llm_cache` table for idempotent LLM outputs | `.cursor/rules/backend.mdc` |
| **Edge Functions** | Default: **stateless** per fetch; no cross-invocation memory cache unless explicitly designed | `.cursor/skills/architecture/SKILL.md` |
| **Optional server Redis** (Upstash, etc.) | **Not in template** — only if northstar + tech spec add it; if added, use same discipline as below | Tech spec + this skill |

---

## Concept mapping (API cache doc → RAD)

| Pattern (backend cache doc) | RAD equivalent |
| --- | --- |
| **Optional Redis / fail-open** | App works with **no** Redis; Edge paths hit DB or return errors. Client works with **empty** React Query cache → refetch. |
| **TTL tiers (SHORT / MID / LONG)** | **`staleTime`** (and sometimes `gcTime`) per query type — see `frontend-data.mdc` table (profile vs credits vs feature data vs static reference). |
| **Write-through invalidation** (`delete` on mutation) | **`queryClient.invalidateQueries({ queryKey: [...] })`** in `useMutation.onSuccess` for every affected key. |
| **Pattern / bulk invalidation** | Invalidate **parent** keys (e.g. list + detail ) or use a shared prefix convention in `query-keys.ts` and invalidate by predicate if needed. |
| **Do not cache volatile columns** (e.g. balance overlaid on read) | **Short `staleTime`** or **Realtime + invalidate** for credits, counts, inventory — never `staleTime: Infinity` for money or authorization-sensitive aggregates unless spec says so. |
| **Ownership check on cache hit** | **RLS** on every Supabase read — client “cache” is not a security boundary. Never trust cached JSON for auth decisions without a fresh capability check if the spec requires it. |
| **Composite key for expensive graph** | Prefer **normalized schema + one good query** or **materialized path** in Postgres; optional **Edge** cache with explicit invalidation list in tech spec. **React Query** can hold denormalized view briefly with tight invalidation. |
| **Cache warming** | **Prefetch** with `queryClient.prefetchQuery` on navigation or after mutation when UX requires instant paint. |
| **Thundering herd** | **TanStack** deduplicates in-flight identical queries. Server: if you add Redis, document stampede risk on cold start / mass invalidation — see mitigation ladder below. |

---

## TTL discipline (mental model)

Align new hooks with a **volatility** tier (names are conceptual — set real `staleTime` in ms in code):

| Tier | Volatility | Example RAD data | Typical direction |
| --- | --- | --- | --- |
| **Short** | Changes often or must feel fresh | Credits, live counters | Tens of seconds; Realtime invalidation |
| **Mid** | Per-screen entity data | Lists, detail records | ~60s default in `query-client.ts` |
| **Long** | Rarely changes post-publish | Static reference, LLM interpretation for same input | Minutes–`Infinity` only with documented invalidation path |

**Rule:** Every **mutation** must list **all** affected `queryKey`s in `onSuccess`. Over-invalidate when unsure.

---

## Edge Function or server Redis (if introduced)

Only after **tech spec** and **architecture** approval:

1. **Fail-open:** Timeout / Redis down → fall back to DB or return error; never infinite hang.
2. **Key naming:** `domain:id` or `domain:parent:child` — document in `tech-spec.md` + `changelog.md`.
3. **Invalidation:** Every write path that affects cached reads must delete or bump keys (or use TTL-only for truly append-only data).
4. **Volatile / auth-sensitive fields:** Do not embed in long-TTL blobs unless overlaid or revalidated (same idea as “don’t cache credit_balance without overlay”).
5. **Stampede:** For one hot key rebuilt from heavy SQL, consider single-flight lock or accept risk at low scale — document in tech spec.

---

## Anti-patterns (same as backend cache docs, client flavor)

- **Infinite stale** on data that mutates elsewhere without Realtime or invalidation.
- **Different `queryKey`s** for the same entity on two screens → duplicate fetch, inconsistent UI.
- **Caching LLM** on the client with wrong keys — follow `frontend-data.mdc` LLM section (`staleTime: Infinity` only when input hash is stable and Edge uses `llm_cache`).
- **Treating React Query as source of truth** for security — **RLS** is the boundary.

---

## When Tech Lead should read this

- Tuning **multi-screen** freshness (profile, credits, lists).
- Adding **Edge** endpoints that might repeat expensive work.
- Evaluating **Upstash Redis** or Vercel **Runtime Cache** for a feature.
- Debugging “stale UI after save” → invalidation audit.

**Implementation details** stay in **`frontend-data.mdc`** (web) and mirrored patterns in **`shared/hooks/`** (native).
