# Douyin Pipeline Audit v2 (2026-06-16)

Side-by-side comparison of the Douyin pipeline against the current Vietnamese TikTok `video_corpus` ingest architecture, with a prioritized remediation list for playback, reference integration, and parity.

## Executive summary

| Capability | TikTok corpus (current) | Douyin corpus (before this work) | Target (this plan) |
|---|---|---|---|
| Extraction boundary | `async_run_extraction_core` | Same (shared) | Same |
| Synthesis at ingest | Extraction-only (`include_diagnosis=False`) | Same | Same |
| Live diagnosis synthesis | `output_redesign` / `voice_guide` | N/A (separate adapt/pattern synth) | Douyin refs feed diagnosis; adapt synth unchanged |
| Two-axis `content_class_id` | HI-9 + HI-11 at ingest | Missing (flat `niche_id` only) | Phase 2a |
| Reference pool | `fetch_corpus_reference_pool` (class→junction→niche) | Side signal only (`douyin_match`) | Phase 2b |
| Video playback | R2 `videos/{id}.mp4` (~30s clip) + TikTok redirect | External `douyin.com` link only | Phase 1: full standard `play_addr` banked to R2 |
| Ingest volume | Nightly shifts, purity gates | ~50/day (5/niche × 10 niches) | Phase 1c: ~100/day |
| HI-13 Gemini Batch | On corpus when `CORPUS_INGEST_USE_GEMINI_BATCH` | Sync only | Phase 3a (after core) |

## Extraction gap matrix

| Item | TikTok corpus | Douyin | Gap severity |
|---|---|---|---|
| Canonical boundary | `async_run_extraction_core` | Same | None |
| HI-14 vi-VN ASR | Optional on video paths | Not used (CN audio) | Low — CN ASR deferred (Phase 3b) |
| HI-13 Gemini Batch | Optional (`CORPUS_INGEST_USE_GEMINI_BATCH`) | Sync per-video | Medium — Phase 3a |
| Tier-1 signals v2 (`loop_score`, etc.) | `compute_tier1_extraction_signals` | Not persisted | Low — Phase 3b |
| `reference_eligible` / purity gates | Yes | No | Low — Phase 3b |
| `content_class_id` + junction | HI-11 route | Not stored | **High** — Phase 2a |
| R2 hook frames + scene JPGs | Yes | Yes | None |
| R2 full/clip MP4 | 30s clip to `videos/` | **Not banked** | **Critical** — Phase 1 |

## Synthesis gap matrix

| Item | TikTok live diagnosis | Douyin batch |
|---|---|---|
| Per-video narrative | `gemini.synthesize_diagnosis_v2` at query time | `douyin_synth.synth_douyin_adapt` (adapt grade) |
| Weekly patterns | `video_patterns` (TikTok) | `douyin_patterns_synth` (3 cards/niche) |
| Stored in corpus | `analysis_json` only (extraction) | `analysis_json` + adapt fields on row |

Douyin synthesis is **intentionally different** — cultural-distance grading for the Kho Douyin product, not a fork of live diagnosis prompts.

## Reference / evidence gap

- TikTok: `fetch_corpus_reference_pool` → `_build_reference_awemes_from_rows` → `_slim_reference_video` with R2 `playback_url`.
- Douyin: `douyin_match.enrich_analysis_with_douyin_match` adds a single `douyin_origin` peer signal — **not** in the reference video carousel.
- Bridge: `map_creator_niche_to_douyin_niche_id` (HI-9 slug → 10-bucket `douyin_niche_taxonomy.id`) — lossy but exists.
- **Phase 2b** generalizes `fetch_douyin_peer_row` → N rows, prefers `content_class_id`, merges into reference pool behind `GETVIEWS_DOUYIN_REFERENCE_POOL`.

## Playback gap

- TikTok: ephemeral CDN → R2 clip; FE `VideoPlayerModal` when `playback_url` set.
- Douyin: `video_url` = ephemeral `play_addr`; FE opens `douyin.com/video/{id}` — **unusable for VN creators without CN app**.
- **Phase 1**: bank standard `play_addr` (not paid HQ endpoint — watermark OK for hook/structure study), `+faststart` remux, Douyin `Referer` header, `playback_url` column, native `<video>` in `DouyinVideoModal`.

## Legal / attribution (accepted)

Re-hosting full Douyin videos on public R2 for in-app study is accepted for v1, parity with existing TikTok corpus clip banking:

- Keep creator attribution (`creator_handle`, `creator_name`).
- Keep secondary **「Mở trên Douyin」** link (`douyin_url`).
- **Retention:** banked videos kept **indefinitely** (protects diagnosis references + saved videos). Feed surfaces recent trends by `indexed_at` only. R2 janitor deletes **orphans** (object with no corpus row), never by age.

## content_class backfill coverage

Run after migration:

```sql
-- Rows with usable format_axis in analysis_json
SELECT COUNT(*) FROM douyin_video_corpus
WHERE (analysis_json->'niche_classification'->>'format_axis') IS NOT NULL
   OR (analysis_json->'niche_classification'->>'carousel_format_axis') IS NOT NULL;

-- Total rows
SELECT COUNT(*) FROM douyin_video_corpus;
```

Backfill uses `content_class_id_for_creator_niche_format(creator_niche_id, format_axis)`; null `format_axis` rows fall back to `niche_id`-mapped default via `douyin_content_class.resolve_content_class_from_analysis`.

## Prioritized remediation (implementation order)

1. **Phase 0** — This document.
2. **Phase 1** — `playback_url` banking + in-app playback + backfill + janitor + tests.
3. **Phase 1c** — Volume ~100/day (`batch_douyin_videos_per_niche=10`, TikHub request cap ~150).
4. **Phase 2a** — `content_class_id` column + ingest resolve + backfill.
5. **Phase 2b** — Reference pool merge + FE CN reference cards (flag-gated).
6. **Phase 3a** — HI-13 Gemini Batch for Douyin (`DOUYIN_INGEST_USE_GEMINI_BATCH`).
7. **Phase 3b** — Tier-1 signals v2, `reference_eligible`, CN ASR, VN subtitle track (separate approval).
8. **Phase 4** — Flip `KHO_DOUYIN_COMING_SOON` after production verification (human gate).

## TikHub endpoints consumed (verified)

Douyin Web API v1 family (`tikhub_douyin.py`):

| Function | Endpoint |
|---|---|
| `fetch_douyin_post_info` | `GET /api/v1/douyin/web/fetch_one_video_v2` |
| `fetch_douyin_post_multi_info` | `POST /api/v1/douyin/web/fetch_multi_video` |
| `fetch_douyin_keyword_search` | `POST /api/v1/douyin/search/fetch_video_search_v2` |
| `fetch_douyin_hashtag_posts` | `POST /api/v1/douyin/web/fetch_challenge_posts` (+ challenge resolve) |
| `fetch_douyin_user_posts` | `GET /api/v1/douyin/web/fetch_user_post_videos` (+ user resolve) |

Playback banking uses `play_addr` from metadata — **no** paid `app/v3/fetch_video_high_quality_play_url` (study use case; saves ~$0.005/video).

## Phase 3b parity backlog (not in this sprint)

- Tier-1 extraction signals v2 on `douyin_video_corpus`
- `reference_eligible` + boost/purity gates
- CN-language ASR (not vi-VN HI-14)
- Vietnamese transcript/subtitle of spoken CN hook (v1: `sub_vi` gloss overlay only)
