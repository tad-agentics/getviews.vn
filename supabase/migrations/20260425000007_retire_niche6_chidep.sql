-- Retire niche 6: Chị đẹp.
--
-- Wave 5+ Phase 3 niche retirement. Discovery during the consolidation
-- audit: the top creator handles in niche 6 are showbiz aggregators
-- (yeah1.giaitri, chandong.showbiz, wetunes.wn, onhaxemshow,
-- sunseeshowbiz, tiintrending, congg_showbiz__) — major Vietnamese
-- entertainment media accounts reposting clips from "Chị Đẹp Đạp Gió
-- Rẽ Sóng" (the VN reality show) and other music/celebrity content.
-- Almost no individual creators surface in the top traffic.
--
-- The hashtag #chidep was culturally hijacked by the show. Original-
-- intent creators (aspirational feminine lifestyle) are drowned out
-- 4-5× by aggregator volume. This is not a creator niche; it's a
-- media-feed niche, and the getviews.vn ICP doesn't live here. A
-- creator who picks "Chị đẹp" in onboarding gets reports built from
-- showbiz aggregator data — actively wrong recommendations.
--
-- Retirement strategy:
--   1. Rebadge the 1 user with primary_niche=6 → niche 3 (Thời trang
--      / Outfit) as the closest creator-niche fit for someone wanting
--      aspirational-feminine content.
--   2. Rebadge the 2 chat_sessions with niche_id=6 → niche 3
--      (preserves session reachability — they're read-only legacy
--      transcripts anyway, see migrations _034/_035/_036).
--   3. Delete all niche-6 rows from NO-ACTION FK tables. The CASCADE
--      tables (scene_intelligence, starter_creators, cross_creator_
--      patterns, trending_sounds, trending_cards, channel_formulas)
--      auto-clear when niche row drops.
--   4. Delete niche 6 from niche_taxonomy.
--
-- Storage caveat: video_corpus DELETE cascades to video_shots and
-- video_diagnostics. The R2 storage objects (video files, thumbnails,
-- scene frames) are NOT cleaned up by this migration — that's a
-- separate cleanup task. Estimated R2 leak: ~1,238 video_shots
-- frames × ~50KB ≈ 60MB, plus 111 video files. Worth a follow-up
-- janitor cron, not a blocker.
--
-- Companion code change in same PR:
--   cloud-run/getviews_pipeline/corpus_ingest.py — classify_format
--   highlight-bucket gate niche IN (6,16,17,21,22,25) → IN
--   (16,17,21,22,25). Niche 6 was added to that gate during the
--   taxonomy expansion under the assumption it was an aspirational-
--   lifestyle niche; that assumption is now invalidated.
--
-- This migration is destructive (DELETEs cascading to ~1,400 rows
-- across 8+ tables). Not idempotent — rerunning is a no-op once
-- niche 6 is gone, but cannot be reverted via the schema.

BEGIN;

-- ── 1. Re-route the 1 user + 2 chat sessions to niche 3 (Outfit) ──
UPDATE profiles      SET primary_niche = 3 WHERE primary_niche = 6;
UPDATE chat_sessions SET niche_id      = 3 WHERE niche_id      = 6;

-- ── 2. Clear NO-ACTION FK references for niche 6 ──────────────────
-- video_corpus DELETE cascades to video_shots (1238 rows) and
-- video_diagnostics via the video_id FK.
DELETE FROM video_corpus       WHERE niche_id = 6;
DELETE FROM hashtag_niche_map  WHERE niche_id = 6;
DELETE FROM signal_grades      WHERE niche_id = 6;
DELETE FROM creator_velocity   WHERE niche_id = 6;
DELETE FROM hook_effectiveness WHERE niche_id = 6;
DELETE FROM daily_ritual       WHERE niche_id = 6;

-- ── 3. Drop niche 6 from taxonomy ──────────────────────────────────
-- Cascades to: scene_intelligence (0), starter_creators (7),
--   cross_creator_patterns (1), trending_sounds (3), trending_cards
--   (0), channel_formulas (0). All auto-clear via FK CASCADE rules.
DELETE FROM niche_taxonomy WHERE id = 6;

COMMIT;
