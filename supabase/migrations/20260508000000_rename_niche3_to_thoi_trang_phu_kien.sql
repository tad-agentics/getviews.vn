-- Rename niche 3 from "Thời trang / Outfit" → "Thời trang Phụ kiện",
-- expanding the signal_hashtags to cover fashion accessories
-- (handbags, jewelry, watches, eyewear, hats, belts, scarves,
-- shoes, wallets, hair accessories) alongside outfit content.
--
-- Aligns with the Douyin sister taxonomy where the Chinese 穿搭/时尚
-- bucket is glossed as "Thời trang · Phụ kiện" (see
-- ``20260603000000_douyin_niche_taxonomy.sql`` row id 7,
-- slug='fashion'). The accessory market is a meaningful share of
-- TikTok VN fashion content and the existing niche 3 hashtag set
-- only had 5 accessory tags (#phukien #giay #tui #vay #ao #quan),
-- which underweights it for the corpus_ingest format gates.
--
-- Hashtag strategy:
--   - Keep every existing outfit/style tag (no creator gets re-bucketed
--     unexpectedly on the next ``refresh_niche_intelligence``).
--   - Add high-volume Vietnamese accessory hashtags: bags, jewelry,
--     watches, sunglasses, hats, scarves, belts, wallets, hair
--     accessories. Brand-adjacent tags only when niche-defining.
--   - Skip generic e-commerce tags (#shopee, #lazada) per the
--     hashtag_niche_map "1 niche per tag if possible" guideline.
--
-- Companion FE: ``src/lib/profileNiches.ts``
-- ``NICHE_TAXONOMY_NAME_VN_BY_ID`` adds a 3 → "Thời trang Phụ kiện"
-- override so the new label renders before this migration applies on
-- a cold-clone DB (mirrors the existing id=4 override for
-- "Ẩm thực & Ăn uống").
--
-- Idempotent: pure UPDATE — rerunning is a no-op.

UPDATE niche_taxonomy SET
  name_vn = 'Thời trang Phụ kiện',
  name_en = 'fashion_accessories',
  signal_hashtags = ARRAY[
    -- Outfit / style (existing)
    '#thoitrang', '#ootd', '#outfit', '#mixdo',
    '#outfitideas', '#outfitinspo', '#outfitoftheday', '#fashiontiktok',
    '#thoitrangnu', '#thoitrangnam', '#thoitrangvietnam',
    '#phoidohanngay', '#phoidep', '#style', '#streetstyle',
    '#fashionvietnam', '#lookbook',
    '#beachoutfit', '#summerfashion', '#workoutfit',
    '#thoitrangcongso', '#phoidocongso', '#shopfashion',
    '#reviewquanao', '#fashionhaul',
    -- Garment categories (existing — keep)
    '#vay', '#ao', '#quan',
    -- Bags & wallets (expanded)
    '#tui', '#tuixach', '#tuihang', '#tuihieu',
    '#tuicluc', '#tuibao', '#tuixachnu', '#tuithetao',
    '#balo', '#balothoitrang', '#vidu', '#vinu', '#vinam',
    '#cluctay', '#muatui',
    -- Footwear (expanded)
    '#giay', '#giaynu', '#giaynam', '#giaysneaker',
    '#giaycaogot', '#giayboots', '#giaybanglu', '#giaylu',
    '#giaythethao', '#giayhang', '#giayhanquoc', '#muagiay',
    '#reviewgiay',
    -- Jewelry (new)
    '#trangsuc', '#trangsuchanng', '#trangsucdep',
    '#bongtai', '#bongtaihieu', '#daychuyen', '#daychuyenbac',
    '#vongtay', '#vongtaybac', '#nhan', '#nhanbac',
    '#trangsucnu', '#bonghoa', '#tigerbac',
    -- Watches (new)
    '#dongho', '#donghodeo', '#donghonu', '#donghonam',
    '#donghohieu', '#donghocaocap', '#reviewdongho',
    -- Eyewear (new)
    '#kinhmat', '#kinhrambo', '#kinhmatnu', '#kinhmatnam',
    '#kinhmathang', '#muakinhmat',
    -- Hats / headwear (new)
    '#non', '#nonsnapback', '#nonbucket', '#nonhang',
    '#nonbao', '#bandana', '#mukvai',
    -- Belts / scarves / gloves (new)
    '#thatlung', '#thatlungnu', '#thatlungnam',
    '#khanluanca', '#khanchoangco', '#khanvuong',
    '#gangtay',
    -- Hair accessories (new)
    '#catoc', '#buockingong', '#nophutoc',
    -- Aggregate accessory tags (new)
    '#phukien', '#phukienthoitrang', '#phukiennu',
    '#phukienhang', '#phukienhanquoc', '#phukienkorea',
    '#fashionaccessory', '#accessory', '#accessories',
    '#phukienviet'
  ]
WHERE id = 3;

-- Seed hashtag_niche_map for the new niche-defining accessory tags.
-- Only seeds tags NOT already mapped (ON CONFLICT DO NOTHING) — existing
-- generic / cross-niche tags (e.g. #thoitrang, #ootd) keep their
-- prior mapping.
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('tuixach',          3, 100, 1, 'seed', false),
  ('tuihieu',          3, 100, 1, 'seed', false),
  ('tuicluc',          3, 100, 1, 'seed', false),
  ('tuixachnu',        3, 100, 1, 'seed', false),
  ('balothoitrang',    3, 100, 1, 'seed', false),
  ('cluctay',          3, 100, 1, 'seed', false),
  ('muatui',           3, 100, 1, 'seed', false),
  ('giaynu',           3, 100, 1, 'seed', false),
  ('giaynam',          3, 100, 1, 'seed', false),
  ('giaycaogot',       3, 100, 1, 'seed', false),
  ('giaybanglu',       3, 100, 1, 'seed', false),
  ('reviewgiay',       3, 100, 1, 'seed', false),
  ('trangsuc',         3, 100, 1, 'seed', false),
  ('trangsuchanng',    3, 100, 1, 'seed', false),
  ('bongtai',          3, 100, 1, 'seed', false),
  ('daychuyen',        3, 100, 1, 'seed', false),
  ('daychuyenbac',     3, 100, 1, 'seed', false),
  ('vongtaybac',       3, 100, 1, 'seed', false),
  ('nhanbac',          3, 100, 1, 'seed', false),
  ('trangsucnu',       3, 100, 1, 'seed', false),
  ('donghodeo',        3, 100, 1, 'seed', false),
  ('donghonu',         3, 100, 1, 'seed', false),
  ('donghonam',        3, 100, 1, 'seed', false),
  ('reviewdongho',     3, 100, 1, 'seed', false),
  ('kinhrambo',        3, 100, 1, 'seed', false),
  ('kinhmathang',      3, 100, 1, 'seed', false),
  ('muakinhmat',       3, 100, 1, 'seed', false),
  ('nonsnapback',      3, 100, 1, 'seed', false),
  ('nonbucket',        3, 100, 1, 'seed', false),
  ('thatlungnu',       3, 100, 1, 'seed', false),
  ('thatlungnam',      3, 100, 1, 'seed', false),
  ('khanluanca',       3, 100, 1, 'seed', false),
  ('khanchoangco',     3, 100, 1, 'seed', false),
  ('phukienthoitrang', 3, 100, 1, 'seed', false),
  ('phukiennu',        3, 100, 1, 'seed', false),
  ('phukienhang',      3, 100, 1, 'seed', false),
  ('phukienhanquoc',   3, 100, 1, 'seed', false),
  ('fashionaccessory', 3, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;
