-- Merge niche 1 (Review đồ Shopee / Gia dụng) into niche 5 →
-- "Kinh doanh online / Bán hàng" (already the post-merge identity
-- since 20260425000006 absorbed niche 12).
--
-- Both niches center on Shopee-ecosystem creators: niche 1 leaned
-- review-then-buy (#reviewshopee, #unboxingshopee, #shopeeaffiliate)
-- while niche 5 leaned earn-via-selling (#tiktokshop, #shopeelive,
-- #banhangonline). Hashtag overlap was already wide (#shopeeaffiliate
-- spans both); the merge unifies the Shopee corpus under one bucket
-- so per-niche aggregates have a thicker sample for benchmarks.
--
-- Strategy: REUSE niche 5's id (smaller, cleaner migration than
-- creating a third id). Niche 5's signal_hashtags absorb niche 1's
-- review / household / unbox / haul tags. Niche 1 rows are rebadged
-- to niche 5 across all data tables. Aggregate tables are cleared
-- for niche 1 — next refresh cron rebuilds them under niche 5 with
-- combined input.
--
-- Post-migration ops (caller responsibility):
--   1. SELECT refresh_niche_intelligence();
--   2. POST /admin/run/reclassify-format (broader niche 5 may route
--      previously misclassified rows differently).
--   3. Sunday batch_analytics will rebuild creator_velocity +
--      hook_effectiveness + signal_grades.
--
-- This migration is NOT idempotent on UPDATE — it assumes niche 1
-- still exists. Rerunning is a no-op (UPDATE ... WHERE id = 1
-- matches 0 rows). The DELETE at the end removes niche 1 from
-- niche_taxonomy permanently.

BEGIN;

-- ── 1. Extend niche 5's signal_hashtags with niche 1's set ─────────
-- Combined: existing online_business + review-buying + Shopee/haul
-- + household + unboxing tags from niche 1. Deduped.
UPDATE niche_taxonomy SET
  signal_hashtags = ARRAY[
    -- Earning / passive income (existing niche 5)
    '#kiemtienonline', '#kiemtien', '#kiemtientiktok',
    '#thunhapthudong', '#makemoneyonline', '#passiveincome',
    '#mmo', '#freelance', '#zerotohero',
    -- Affiliate / KOC / UGC
    '#tiktokaffiliate', '#affiliatemarketing', '#tiepthilienket',
    '#affiliatekoc', '#kocvietnam', '#koc',
    '#ugccreator', '#ugcvietnam', '#influencer',
    '#shopeeaffiliate',
    -- E-commerce platforms
    '#tiktokshop', '#tiktokshopvn', '#tiktokshopping',
    '#tiktokshoplive', '#shopeelive', '#liveshopee',
    '#shopeereviews', '#banchayshopee',
    -- Livestream / live commerce
    '#livestream', '#livebanhang', '#liveselling',
    '#livestreamchuyennghiep', '#kynanglive', '#tiktoklive',
    '#facebooklive', '#zololive', '#onlive', '#live',
    -- Selling broadly
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
    '#marketingonline', '#mxhmarketing',
    -- Review-then-buy + Shopee household (absorbed from niche 1)
    '#reviewdogiadung', '#dogiadung', '#reviewshopee', '#nhacua',
    '#unboxingshopee', '#muahangshopee', '#shopeehaul', '#haul',
    '#reviewdo', '#donoibat', '#beptop', '#dobeprep',
    '#haulopee', '#reviewdochoian', '#maysay', '#noicook',
    '#reviewdoquan', '#muasamthongminh'
  ]
WHERE id = 5;

-- ── 2. Rebadge data tables (no uniqueness conflicts) ───────────────
UPDATE video_corpus           SET niche_id = 5 WHERE niche_id = 1;
-- video_shots is created in 20260510000003 — skip if this merge runs first (fresh db reset).
DO $$
BEGIN
  IF to_regclass('public.video_shots') IS NOT NULL THEN
    UPDATE video_shots SET niche_id = 5 WHERE niche_id = 1;
  END IF;
END $$;
UPDATE profiles               SET primary_niche = 5 WHERE primary_niche = 1;
UPDATE cross_creator_patterns SET niche_id = 5 WHERE niche_id = 1;
UPDATE daily_ritual           SET niche_id = 5 WHERE niche_id = 1;
UPDATE trending_sounds        SET niche_id = 5 WHERE niche_id = 1;

-- ── 3. hashtag_niche_map: dedupe-then-rebadge ──────────────────────
-- For tags mapped to BOTH 5 and 1: drop the niche-1 row, keep
-- niche-5. For tags mapped ONLY to niche 1: rebadge to niche 5.
DELETE FROM hashtag_niche_map
 WHERE niche_id = 1
   AND hashtag IN (SELECT hashtag FROM hashtag_niche_map WHERE niche_id = 5);
UPDATE hashtag_niche_map SET niche_id = 5 WHERE niche_id = 1;

-- ── 4. Aggregate tables — clear niche-1; cron will rebuild ─────────
-- These are derived aggregates (creator_velocity, hook_effectiveness,
-- niche_insights, signal_grades, starter_creators). Cron passes
-- recompute them per-niche; merging directly would require summing
-- engagement counters or rerunning the analytics pass inline. Cleaner
-- to drop and let next refresh rebuild under the unified niche 5.
DELETE FROM creator_velocity   WHERE niche_id = 1;
DELETE FROM hook_effectiveness WHERE niche_id = 1;
DELETE FROM niche_insights     WHERE niche_id = 1;
DELETE FROM signal_grades      WHERE niche_id = 1;
DELETE FROM starter_creators   WHERE niche_id = 1;

-- ── 5. Drop niche 1 from taxonomy ──────────────────────────────────
-- All FK references handled above. niche_taxonomy has no FK to
-- itself, so this is a clean DELETE.
DELETE FROM niche_taxonomy WHERE id = 1;

COMMIT;
