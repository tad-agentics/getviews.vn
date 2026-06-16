-- 2026-06-16 — Kho Douyin · richer ingest signals per niche.
--
-- Why this exists
-- ───────────────
-- The daily Douyin ingest (``cloud-run/getviews_pipeline/douyin_ingest.py``)
-- builds each niche's candidate pool from two sources seeded here:
--   • ``signal_hashtags_zh`` — drives ``fetch_douyin_hashtag_posts``.
--   • ``signal_keywords_zh`` — (NEW) drives extra ``fetch_douyin_keyword_search``
--     calls beyond the single ``name_zh`` head term.
--
-- The 2026-06-16 manual backfill run surfaced two thin niches —
-- ``tech`` and ``fashion`` ingested 0 videos (all candidates failed the
-- popularity / engagement gate) because their seeded tags were too
-- generic to surface viral clips. This migration:
--   1. Adds the ``signal_keywords_zh`` column (multi-keyword search).
--   2. Widens + sharpens ``signal_hashtags_zh`` for every niche.
--   3. Seeds ``signal_keywords_zh`` for every niche (tech/fashion fixed).
--
-- These are STARTING points — the D2 niche-yield ranker prunes/grows
-- over time. Service-role writes only; FE never writes this table.

ALTER TABLE douyin_niche_taxonomy
  ADD COLUMN IF NOT EXISTS signal_keywords_zh TEXT[] NOT NULL DEFAULT '{}';

COMMENT ON COLUMN douyin_niche_taxonomy.signal_keywords_zh IS
  'Chinese keywords the daily Douyin ingest feeds into fetch_douyin_keyword_search (TikHub /douyin/search/fetch_video_search_v2), in addition to the name_zh head term. Seeded with ~3 high-yield terms per niche; capped at ingest time by batch_douyin_keyword_fetch_limit.';

-- ── Widen + sharpen hashtags, seed keywords (idempotent UPSERT-by-id) ──
UPDATE douyin_niche_taxonomy SET
  signal_hashtags_zh = ARRAY['#养生','#健康生活','#瑜伽','#冥想','#健身','#中医养生','#养生日常','#健康'],
  signal_keywords_zh = ARRAY['养生','健康','瑜伽']
WHERE slug = 'wellness';

UPDATE douyin_niche_taxonomy SET
  signal_hashtags_zh = ARRAY['#美妆','#护肤','#彩妆','#口红','#美容','#化妆教程','#护肤心得','#美妆教程'],
  signal_keywords_zh = ARRAY['美妆','护肤','化妆教程']
WHERE slug = 'beauty';

UPDATE douyin_niche_taxonomy SET
  signal_hashtags_zh = ARRAY['#生活方式','#vlog','#慢生活','#日常','#一个人生活','#生活记录','#治愈系','#生活日常'],
  signal_keywords_zh = ARRAY['生活方式','vlog','日常']
WHERE slug = 'lifestyle';

UPDATE douyin_niche_taxonomy SET
  signal_hashtags_zh = ARRAY['#旅游','#自驾游','#旅拍','#风景','#旅行','#旅行vlog','#国内旅游','#旅游攻略'],
  signal_keywords_zh = ARRAY['旅游','旅行','风景']
WHERE slug = 'travel';

UPDATE douyin_niche_taxonomy SET
  signal_hashtags_zh = ARRAY['#美食','#探店','#家常菜','#早餐','#烘焙','#美食教程','#美食分享','#做饭'],
  signal_keywords_zh = ARRAY['美食','美食教程','探店']
WHERE slug = 'food';

-- tech — was 0 videos: generic ``#科技 #数码`` surfaced low-engagement clips.
UPDATE douyin_niche_taxonomy SET
  signal_hashtags_zh = ARRAY['#科技','#数码','#开箱','#评测','#手机','#数码测评','#科技数码','#手机摄影','#黑科技','#智能家居'],
  signal_keywords_zh = ARRAY['科技','数码','手机评测']
WHERE slug = 'tech';

-- fashion — was 0 videos: ``#穿搭 #ootd`` alone too broad.
UPDATE douyin_niche_taxonomy SET
  signal_hashtags_zh = ARRAY['#穿搭','#ootd','#时尚','#穿搭分享','#穿搭教程','#日常穿搭','#秋冬穿搭','#时尚穿搭','#包包','#配饰'],
  signal_keywords_zh = ARRAY['穿搭','时尚','ootd']
WHERE slug = 'fashion';

UPDATE douyin_niche_taxonomy SET
  signal_hashtags_zh = ARRAY['#家居','#装修','#收纳','#软装','#ins风','#家居好物','#家装','#收纳整理'],
  signal_keywords_zh = ARRAY['家居','装修','收纳']
WHERE slug = 'home';

UPDATE douyin_niche_taxonomy SET
  signal_hashtags_zh = ARRAY['#理财','#存钱','#副业','#投资','#理财知识','#个人理财','#搞钱','#财商'],
  signal_keywords_zh = ARRAY['理财','存钱','副业']
WHERE slug = 'finance';

UPDATE douyin_niche_taxonomy SET
  signal_hashtags_zh = ARRAY['#育儿','#亲子','#育儿经验','#宝宝','#带娃日常','#亲子互动','#育儿知识','#成长记录'],
  signal_keywords_zh = ARRAY['育儿','亲子','带娃']
WHERE slug = 'parenting';
