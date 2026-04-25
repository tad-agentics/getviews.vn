-- Merge niche 12 (Shopee Live / Livestream) into niche 5 →
-- rename combined niche to "Kinh doanh online / Bán hàng".
--
-- Wave 5+ Phase 3 niche consolidation. Both source niches were
-- below 200-row reliability floor (niche 5: 14 rows, niche 12: 40
-- rows) and shared format conventions: face-to-camera advice on
-- earning via TikTok / Shopee, screen-recordings of seller
-- dashboards, "kiếm được X triệu/tháng" hooks. Merging gives
-- ~54 rows immediately under a single coherent identity rather
-- than two thin buckets producing unreliable per-niche aggregates.
--
-- Strategy: REUSE niche 5's id (smaller, cleaner migration than
-- creating a third id). Niche 5 gets renamed + signal_hashtags
-- merged. Niche 12 rows are rebadged to niche 5 across all data
-- tables. Aggregate tables (creator_velocity, hook_effectiveness,
-- niche_insights, signal_grades, starter_creators) are cleared
-- for niche 12 — next refresh cron will rebuild them under niche
-- 5 with combined input.
--
-- Post-migration ops (caller responsibility):
--   1. SELECT refresh_niche_intelligence();
--   2. POST /admin/run/reclassify-format (regex catch-up;
--      classify_format gates may route differently now that
--      niche 5 is broader).
--   3. Sunday batch_analytics will rebuild creator_velocity +
--      hook_effectiveness + signal_grades.
--
-- This migration is NOT idempotent on UPDATE — it assumes niche
-- 12 still exists. Rerunning is a no-op (UPDATE ... WHERE id = 12
-- matches 0 rows). The DELETE at the end removes niche 12 from
-- niche_taxonomy permanently.

BEGIN;

-- ── 1. Rename niche 5 + merge signal_hashtags ──────────────────────
-- Combined set: earning / selling / livestream / e-commerce / KOC /
-- affiliate / content marketing — the union of both source niches'
-- niche-defining tags, deduplicated. Generic tags (#contentcreator,
-- #personalbranding) trimmed from the original niche-5 set since
-- they leaked across many niches.
UPDATE niche_taxonomy SET
  name_vn = 'Kinh doanh online / Bán hàng',
  name_en = 'online_business',
  signal_hashtags = ARRAY[
    -- Earning / passive income (from niche 5)
    '#kiemtienonline', '#kiemtien', '#kiemtientiktok',
    '#thunhapthudong', '#makemoneyonline', '#passiveincome',
    '#mmo', '#freelance', '#zerotohero',
    -- Affiliate / KOC / UGC (shared)
    '#tiktokaffiliate', '#affiliatemarketing', '#tiepthilienket',
    '#affiliatekoc', '#kocvietnam', '#koc',
    '#ugccreator', '#ugcvietnam', '#influencer',
    -- E-commerce platforms (from both)
    '#tiktokshop', '#tiktokshopvn', '#tiktokshopping',
    '#tiktokshoplive', '#shopeelive', '#liveshopee',
    '#shopeereviews', '#banchayshopee',
    -- Livestream / live commerce (from niche 12)
    '#livestream', '#livebanhang', '#liveselling',
    '#livestreamchuyennghiep', '#kynanglive', '#tiktoklive',
    '#facebooklive', '#zololive', '#onlive', '#live',
    -- Selling broadly (from both)
    '#banhangonline', '#banhang', '#banhangtructuyen',
    '#banhangmxh', '#banhangfacebook', '#kinhdoanhonline',
    '#kinhdoanhthongminh',
    -- Sales / promotion mechanics
    '#flashsale', '#dealflash', '#muasam', '#voucher',
    '#khuyenmai', '#combokhuyenmai', '#giftvoucher',
    '#sanphamhot', '#sanphamdangmua', '#reviewsanphamlive',
    -- Education / how-to selling
    '#hocbuon', '#hockinhdoanh', '#khoadayhoc', '#onlinecourse',
    '#chiasekinhdoanhbanhang', '#gockhoanbanhang',
    -- Adjacent / digital business
    '#dropshipping', '#print-on-demand', '#printify', '#etsy',
    '#shopifystore', '#thuongmaidientu', '#ecommerce',
    '#digitalmarketing', '#digitalsales', '#contentmarketing',
    '#marketingonline', '#mxhmarketing'
  ]
WHERE id = 5;

-- ── 2. Rebadge data tables (no uniqueness conflicts) ───────────────
UPDATE video_corpus           SET niche_id = 5 WHERE niche_id = 12;
UPDATE video_shots            SET niche_id = 5 WHERE niche_id = 12;
UPDATE profiles               SET primary_niche = 5 WHERE primary_niche = 12;
UPDATE cross_creator_patterns SET niche_id = 5 WHERE niche_id = 12;
UPDATE daily_ritual           SET niche_id = 5 WHERE niche_id = 12;
UPDATE trending_sounds        SET niche_id = 5 WHERE niche_id = 12;

-- ── 3. hashtag_niche_map: dedupe-then-rebadge ──────────────────────
-- For tags mapped to BOTH 5 and 12: drop the niche-12 row, keep
-- niche-5. For tags mapped ONLY to niche 12: rebadge to niche 5.
DELETE FROM hashtag_niche_map
 WHERE niche_id = 12
   AND hashtag IN (SELECT hashtag FROM hashtag_niche_map WHERE niche_id = 5);
UPDATE hashtag_niche_map SET niche_id = 5 WHERE niche_id = 12;

-- ── 4. Aggregate tables — clear niche-12; cron will rebuild ────────
-- These are derived aggregates (creator_velocity, hook_effectiveness,
-- niche_insights, signal_grades, starter_creators). Cron passes
-- recompute them per-niche; merging directly would require summing
-- engagement counters or rerunning the analytics pass inline. Cleaner
-- to drop and let next refresh rebuild under the unified niche 5.
DELETE FROM creator_velocity   WHERE niche_id = 12;
DELETE FROM hook_effectiveness WHERE niche_id = 12;
DELETE FROM niche_insights     WHERE niche_id = 12;
DELETE FROM signal_grades      WHERE niche_id = 12;
DELETE FROM starter_creators   WHERE niche_id = 12;

-- ── 5. Drop niche 12 from taxonomy ─────────────────────────────────
-- All FK references handled above. niche_taxonomy has no FK to
-- itself, so this is a clean DELETE.
DELETE FROM niche_taxonomy WHERE id = 12;

COMMIT;
