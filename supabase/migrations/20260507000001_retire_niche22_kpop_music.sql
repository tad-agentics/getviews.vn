-- Retire niche 22: K-pop / Âm nhạc.
--
-- Niche 22 was created on 2026-04-25 by splitting music-content out of
-- the (then-active) niche 6 Chị đẹp bucket — see
-- ``20260425000002_add_niche22_kpop_music.sql``. Niche 6 was retired
-- the same day for being a media-feed (showbiz aggregators) rather
-- than a creator niche; the K-pop / music split inherited similar
-- problems: dominant traffic comes from MV / dance-cover repost
-- accounts and fan-edits, not from individual creators making
-- shoot-able content. The getviews.vn ICP doesn't live here.
--
-- Retirement strategy mirrors ``20260425000007_retire_niche6_chidep``:
--   1. Rebadge any user with primary_niche=22 → niche 13 (Hài / Giải
--      trí), the closest creator-niche fit for entertainment-leaning
--      content. Same for chat_sessions (read-only legacy transcripts).
--   2. Delete niche-22 rows from NO-ACTION FK tables (or re-point to
--      niche 13). CASCADE tables (scene_intelligence, starter_creators,
--      cross_creator_patterns, trending_sounds, trending_cards,
--      channel_formulas) auto-clear when the niche row drops.
--   3. Delete niche 22 from niche_taxonomy.
--
-- Storage caveat: video_corpus DELETE cascades to video_shots and
-- video_diagnostics. The R2 storage objects (video files, thumbnails,
-- scene frames) are NOT cleaned up by this migration — that's a
-- separate cleanup task (folded into the same R2 janitor follow-up
-- noted on the niche-6 retirement migration).
--
-- Companion code change in same PR:
--   cloud-run/getviews_pipeline/corpus_ingest.py — classify_format
--   highlight-bucket gate ``niche_id in (14, 16, 17, 21, 22)`` →
--   ``(14, 16, 17, 21)``. Niche 22 was added to that gate during the
--   2026-04-25 taxonomy expansion; the assumption that K-pop / music
--   short clips fit the creator-highlight bucket no longer applies.
--
-- This migration is destructive (DELETEs cascading across 8+ tables).
-- Not idempotent — rerunning is a no-op once niche 22 is gone, but
-- cannot be reverted via the schema.

BEGIN;

-- ── 1. Re-route profiles + chat sessions to niche 13 (Hài / Giải trí) ──
UPDATE profiles      SET primary_niche = 13 WHERE primary_niche = 22;
UPDATE chat_sessions SET niche_id      = 13 WHERE niche_id      = 22;
UPDATE answer_sessions SET niche_id = 13 WHERE niche_id = 22;

-- ── 2. Clear NO-ACTION FK references for niche 22 ─────────────────
DELETE FROM niche_insights WHERE niche_id = 22;
UPDATE niche_candidates SET assigned_niche_id = 13 WHERE assigned_niche_id = 22;
UPDATE competitor_tracking SET niche_id = 13 WHERE niche_id = 22;
UPDATE creator_pattern SET niche_id = 13 WHERE niche_id = 22;
DELETE FROM niche_daily_sounds WHERE niche_id = 22;
DELETE FROM niche_weekly_digest WHERE niche_id = 22;
UPDATE draft_scripts SET niche_id = 13 WHERE niche_id = 22;

-- ── 2b. Corpus + analytics tables (same as niche-6 retirement) ────
-- video_corpus DELETE cascades to video_shots and video_diagnostics
-- via the video_id FK.
DELETE FROM video_corpus       WHERE niche_id = 22;
DELETE FROM hashtag_niche_map  WHERE niche_id = 22;
DELETE FROM signal_grades      WHERE niche_id = 22;
DELETE FROM creator_velocity   WHERE niche_id = 22;
DELETE FROM hook_effectiveness WHERE niche_id = 22;
DELETE FROM daily_ritual       WHERE niche_id = 22;

-- ── 3. Drop niche 22 from taxonomy ────────────────────────────────
-- Cascades to: scene_intelligence, starter_creators,
-- cross_creator_patterns, trending_sounds, trending_cards,
-- channel_formulas — all auto-clear via FK CASCADE rules.
DELETE FROM niche_taxonomy WHERE id = 22;

COMMIT;
