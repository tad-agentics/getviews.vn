-- 2026-06-03 — D1 — Kho Douyin · niche taxonomy seed.
--
-- Mirrors ``niche_taxonomy`` (the Vietnamese TikTok corpus' niche table)
-- with Chinese-context fields for the Kho Douyin surface
-- (``screens/douyin.jsx`` § II — kho video lẻ + § I pattern signals).
--
-- Why a separate table:
--   - Douyin niches are CN-context (different cultural buckets) — e.g.
--     "穿搭" (穿搭/OOTD) is a single category in CN; in VN we split fashion +
--     accessories. Sharing taxonomy with VN TikTok would force compromises
--     on both sides.
--   - The ingest pipeline (``cloud-run/getviews_pipeline/douyin_ingest.py``,
--     lands in D2) needs CN signal hashtags (``signal_hashtags_zh``) to
--     drive EnsembleData ``/douyin/hashtag/posts`` queries — Vietnamese
--     hashtags wouldn't match Douyin's tagging conventions.
--   - The downstream FE filter chips (``DOUYIN_NICHES`` in
--     ``screens/douyin.jsx``) read the VN-display label, not the CN one.
--
-- Schema:
--   id              SERIAL PK
--   slug            TEXT UNIQUE — stable string id for FE filter chips
--                   (mirrors design's ``DOUYIN_NICHES[].id``: wellness, tech,
--                   beauty, food, fashion, finance, lifestyle, travel,
--                   home, parenting). Used over numeric id on the wire so
--                   chips stay stable across reseed.
--   name_vn         TEXT NOT NULL — Vietnamese display label
--   name_zh         TEXT NOT NULL — Chinese label (debug + admin tooling)
--   name_en         TEXT NOT NULL — English label (logs + i18n later)
--   signal_hashtags_zh TEXT[] NOT NULL — Chinese hashtags ED ``/douyin/hashtag/posts``
--                   queries against. Seeded with ~5 popular tags per
--                   niche; ``corpus_ingest``'s niche-yield ranker can
--                   prune low-yield ones over time.
--   active          BOOLEAN NOT NULL DEFAULT TRUE — soft-disable flag so
--                   we can pause a niche from the daily cron without
--                   deleting the row (kept for downstream FK validity).
--
-- RLS: read-only for authenticated (mirrors niche_taxonomy). Service-role
-- writes happen via the batch ingest only.

CREATE TABLE IF NOT EXISTS douyin_niche_taxonomy (
  id SERIAL PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name_vn TEXT NOT NULL,
  name_zh TEXT NOT NULL,
  name_en TEXT NOT NULL,
  signal_hashtags_zh TEXT[] NOT NULL DEFAULT '{}',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE douyin_niche_taxonomy ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read douyin_niche_taxonomy"
  ON douyin_niche_taxonomy FOR SELECT
  TO authenticated
  USING (true);

-- Starter set — 10 niches per the user's spec for D1.
-- Order chosen to match design's chip flow (popular wellness/beauty/tech
-- first, then lifestyle/travel/food, then long-tail fashion/home/finance/
-- parenting). signal_hashtags_zh values are popular Douyin tags that
-- consistently surface in keyword/hashtag search; they're STARTING points,
-- not exhaustive — the niche-yield ranker in D2 will prune + grow.
INSERT INTO douyin_niche_taxonomy (id, slug, name_vn, name_zh, name_en, signal_hashtags_zh) VALUES
  (1,  'wellness',  'Sức khoẻ · Wellness',         '养生 · 健康生活',     'Wellness',
       ARRAY['#养生', '#健康生活', '#瑜伽', '#冥想', '#早晨routine']),
  (2,  'beauty',    'Beauty · Skincare',            '美妆 · 护肤',         'Beauty',
       ARRAY['#美妆', '#护肤', '#彩妆', '#口红', '#美容']),
  (3,  'lifestyle', 'Đời sống · Slow-life',         '生活方式 · 慢生活',  'Lifestyle',
       ARRAY['#生活方式', '#vlog', '#慢生活', '#日常', '#一个人生活']),
  (4,  'travel',    'Du lịch',                       '旅游',                'Travel',
       ARRAY['#旅游', '#自驾游', '#旅拍', '#风景', '#vlog']),
  (5,  'food',      'Ẩm thực · F&B',                 '美食',                'Food',
       ARRAY['#美食', '#探店', '#家常菜', '#早餐', '#烘焙']),
  (6,  'tech',      'Tech · Setup',                  '科技 · 数码',         'Tech',
       ARRAY['#科技', '#数码', '#开箱', '#评测', '#手机']),
  (7,  'fashion',   'Thời trang · Phụ kiện',        '穿搭 · 时尚',         'Fashion & accessories',
       ARRAY['#穿搭', '#ootd', '#时尚', '#包包', '#配饰']),
  (8,  'home',      'Nhà cửa · Nội thất',           '家居 · 装修',         'Home & interior',
       ARRAY['#家居', '#装修', '#收纳', '#软装', '#ins风']),
  (9,  'finance',   'Tài chính cá nhân',             '理财',                'Personal finance',
       ARRAY['#理财', '#存钱', '#副业', '#投资', '#月薪']),
  (10, 'parenting', 'Nuôi con · Gia đình',          '育儿 · 亲子',         'Parenting',
       ARRAY['#育儿', '#亲子', '#妈妈', '#宝宝', '#成长记录'])
ON CONFLICT (id) DO NOTHING;

SELECT setval(
  'douyin_niche_taxonomy_id_seq',
  GREATEST(10, (SELECT COALESCE(MAX(id), 1) FROM douyin_niche_taxonomy))
);

COMMENT ON TABLE douyin_niche_taxonomy IS
  'D1 (2026-06-03) — niche reference for Kho Douyin surface. Mirrors niche_taxonomy with CN-context fields (signal_hashtags_zh drives EnsembleData /douyin/hashtag/posts queries in the ingest pipeline). Service-role writes only; FE reads via /douyin/niches.';

COMMENT ON COLUMN douyin_niche_taxonomy.slug IS
  'Stable string id used over numeric id on the wire (FE filter chips, route params). Mirrors screens/douyin.jsx DOUYIN_NICHES[].id.';

COMMENT ON COLUMN douyin_niche_taxonomy.signal_hashtags_zh IS
  'Chinese hashtags the daily Douyin ingest queries against (EnsembleData /douyin/hashtag/posts). Seeded with ~5 high-yield tags per niche; niche-yield ranker in D2 prunes/grows over time.';

COMMENT ON COLUMN douyin_niche_taxonomy.active IS
  'Soft-disable flag — pauses the niche from daily cron without deleting the row (keeps FK targets valid for already-ingested douyin_video_corpus rows).';
