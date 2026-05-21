# Hashtag class map v2

**Status:** Schema deployed (Phase 0b); learn/prune wired Phase 3.  
**Table:** `hashtag_class_map` (migration `20260820000001_hashtag_class_map.sql`)

## Schema

| Column | Type | Notes |
|--------|------|-------|
| `hashtag` | TEXT | Lowercase, no `#` |
| `content_class_id` | INT | FK → `content_classifications` |
| `confidence` | FLOAT | Learn strength (default 0.5) |
| `yield_14d` | FLOAT | From `corpus_hashtag_yields_14d` when available |
| `last_seen_at` | TIMESTAMPTZ | Last corpus observation |
| `source` | TEXT | `batch_learn` \| `ed_trending` \| `manual_seed` |
| `occurrences` | INT | Upsert counter |

Primary key: `(hashtag, content_class_id)`.

## Learn loop (automated)

1. **Batch learn** — after each `video_corpus` upsert, `hashtag_class_map.learn_from_corpus_row()` upserts caption hashtags for stored `content_class_id`.
2. **Cold-start (ACQE nights 1–3)** — learn from rows with `niche_resolution_confidence >= 0.6`.
3. **Validated subset (night 4+)** — prefer `class_assignment_tier = validated` and `class_assignment_disagreement < 0.3`.
4. **Prune** — `run_hashtag_map_maintenance_sync()` nightly: refresh `yield_14d` from `corpus_hashtag_yields_14d`, delete stale low-yield rows.
5. **Expand** — Thin/Dormant targets seed from signal hashtags + top corpus tags (`expand_trending_seeds_sync`).
6. **Pool pick** — `_resolve_pool_hashtags()` reads class map before legacy niche map; Thin/Dormant auto-relax (25 tags + lower pre-pool floor) without manual env when ACQE tier says so.

## Discovery relax

When ACQE sets class **Thin/Dormant**, batch ingest auto-relax (no env flip required):

- `acqe_run_state.discovery_relax_active` + per-target `_viability_tier`
- Optional override: `CORPUS_DISCOVERY_RELAX=true` on batch pod

- Lower pre-pool view floor (~2k)
- Widen hashtag fetch (`ADAPTIVE_HASHTAG_MIN_FETCH`)

Trade purity VPN for pool depth — logged per niche/class target.

## Code

| Module | Path |
|--------|------|
| Class map | `cloud-run/getviews_pipeline/hashtag_class_map.py` |
| Ingest wire | `cloud-run/getviews_pipeline/corpus_ingest.py` |

## Deploy gate

Dual-write legacy `hashtag_niche_map` for 14d shadow, then deprecate niche-only writes (Phase 3).
