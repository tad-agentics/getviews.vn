-- Sprint 8.5 — Remove Vietnamese news/aggregator accounts from corpus.
--
-- These handles are media outlets, news aggregators, and platform-owned
-- showbiz/sports channels that repackage other creators' content.
-- They are NOT creators in the GetViews target audience. Their presence
-- in video_corpus pollutes niche signal and produces fake patterns
-- (e.g. an entire "Pattern" surface dominated by repackaged news clips).
--
-- The matching ingest filter ships in
--   ``cloud-run/getviews_pipeline/creator_blocklist.py``
-- via ``is_blocklisted_handle()``. This migration removes the existing
-- rows so users see clean corpus immediately instead of waiting for the
-- 30-day fall-off.
--
-- ── Why hard delete (not soft-mark) ─────────────────────────────────
--
-- 1. ``video_patterns.niche_spread`` / ``weekly_instance_count`` is
--    recomputed from video_corpus by the fingerprint cron — the next
--    cron run cleans up pattern stats automatically.
-- 2. ``daily_ritual.grounded_video_ids`` references video_id but
--    tolerates missing rows (the FE filters out unloadable thumbnails).
-- 3. There are no FK constraints out of video_corpus, so no cascading
--    integrity issues.
-- 4. Soft-marking would require every downstream query to know about
--    a new ``is_blocklisted`` column. Hard delete keeps the schema clean.
--
-- The list MUST stay in sync with
-- ``creator_blocklist.NEWS_AGGREGATOR_HANDLES``. If you update one,
-- update the other in the same PR.

BEGIN;

DELETE FROM video_corpus
WHERE LOWER(REGEXP_REPLACE(creator_handle, '^@', '')) IN (
  -- theanh28 family
  'theanh28gaming','theanh28sport','theanh28trending',
  'theanh28entertainment','hanoinews.theanh28',

  -- vtvcab + vtv
  'vtvcab','vtvcab.khampha.onlive','vtvcab.sports',
  'vtvcab.gaming.onlive','vtvcab.congnghe.onlive',
  'vtvcab.esports.onlive','vtvcab.tintuc','vtvcab.giaitri24h',
  'vtvcab.tieudiem','vtvcab.trending','vtvcab.giaitri',
  'vtvcab.thethao','vtvindex','yeuthoisuvtv',
  'truyenhinhthanhhoa.ttv','truyenhinhnghean',

  -- 24h family
  '24h.sports','24h.tinmoi','bongda24h.vn.official',
  '24h_nhieuchuyen','24hmoney.dautu',

  -- Sports media outlets
  'thethao247.vn','thethaovavanhoa','thethao.net206',
  'thethaovacuocsong21','sportfocusvn','asiasportvn',
  'btsport739taquangbuu','chuyensports',
  'football.century_','football_nvc','minhhuu_football',
  'sinregar_football','ptfootball','ducansport',
  'khangsport00','onlivesports','onsportsplus',
  'oksportvn','chusssport.offici','ilovefootball31299',
  'jogarbolasport','uniscore.football','kin.cng.sports.ty',
  'baseline_sport','mediapickleballvietnam',

  -- Gaming/esports news
  'kiran.aov.news','hung_aovnews','vovgamesport',
  'jettvn','tethan.news','freefireesportsvn',
  'freefireesportswc','tsa.esport_1',

  -- General news / showbiz
  'znewssocial','kenh14official','kenh14disoisaodi',
  'beatvn_official','news360.k37','.vni.media',
  'vnexpress_hanoi','vietnamnet.vn','tayninh.news',
  'sunseeshowbiz','muoivove','vkr_news','k.news_vn',
  'kenh7.news','amgland.news','tintuciran','tram.tintuc',
  'trm.tin.tc.24h','tinshowbiz2026','quayducshowbiz',
  'bhmediacomedy','xemxe24h','congnghe24h.gmv',
  'locoloconews','eva.vnsao',

  -- Auto / legal / biz news
  'autonews.vneconomy','auto5.vn','thuvienphapluat.vn',
  'phapluatchinhsach.vn','aftvmedia','plxh.vn',
  'vietnameconomynews'
);

COMMIT;
