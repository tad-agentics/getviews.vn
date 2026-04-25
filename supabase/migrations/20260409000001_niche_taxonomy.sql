-- niche_taxonomy — reference niches (read for all, no client writes)

CREATE TABLE niche_taxonomy (
  id SERIAL PRIMARY KEY,
  name_vn TEXT NOT NULL UNIQUE,
  name_en TEXT NOT NULL,
  signal_hashtags TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE niche_taxonomy ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read niche taxonomy"
  ON niche_taxonomy FOR SELECT
  TO anon, authenticated
  USING (true);

-- No INSERT/UPDATE/DELETE for clients (service_role bypasses RLS for batch jobs if needed)

-- Baseline rows (ids 1–17) must exist before later migrations UPDATE/INSERT by id.
-- Previously these lived only in seed.sql, which runs after migrations — breaking `db reset`.
INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags) VALUES
  (1,  'Review đồ Shopee / Gia dụng', 'Shopee affiliate reviews',       ARRAY['#reviewdogiadung','#dogiadung','#reviewshopee','#nhacua']),
  (2,  'Làm đẹp / Skincare',          'Beauty & skincare',               ARRAY['#lamdep','#skincare','#chamsocda','#reviewmypham']),
  (3,  'Thời trang / Outfit',          'Fashion & outfit',                ARRAY['#thoitrang','#ootd','#outfit','#mixdo']),
  (4,  'Review đồ ăn / F&B',          'Food reviews & restaurants',      ARRAY['#reviewdoan','#angi','#foodtiktok','#ancungtiktok']),
  (5,  'Kiếm tiền online / MMO',       'Make money online',               ARRAY['#kiemtienonline','#mmo','#affiliate','#thunhapthudong']),
  (6,  'Chị đẹp',                      'Aspirational feminine lifestyle', ARRAY['#chidep','#songdep','#dailylife','#morningroutine']),
  (7,  'Mẹ bỉm sữa / Parenting',      'Parenting & baby',                ARRAY['#mebimsua','#baby','#nuoiday','#mevaebe']),
  (8,  'Gym / Fitness VN',             'Fitness & gym',                   ARRAY['#gymvietnam','#tapgym','#fitness','#giamcan']),
  (9,  'Công nghệ / Tech',             'Technology & gadgets',            ARRAY['#congnghe','#reviewdienthoai','#tech','#laptop']),
  (10, 'Bất động sản',                 'Real estate',                     ARRAY['#batdongsan','#nhadat','#muanha']),
  (11, 'EduTok VN',                    'Education',                       ARRAY['#edutokvn','#hoctienganh','#giaoduc','#kienthuc']),
  (12, 'Shopee Live / Livestream',     'Live commerce',                   ARRAY['#shopeelive','#livestream','#banhang','#liveshopee']),
  (13, 'Hài / Giải trí',              'Comedy & entertainment',           ARRAY['#hai','#haihuoc','#comedy','#cuoivoibui']),
  (14, 'Ô tô / Xe máy',               'Automobiles & motorcycles',       ARRAY['#oto','#xemay','#reviewxe','#otovietnam']),
  (15, 'Tài chính / Đầu tư',          'Finance & investment',            ARRAY['#taichinh','#chungkhoan','#crypto','#dautu']),
  (16, 'Du lịch / Travel',             'Travel & tourism',                ARRAY['#dulich','#travel','#khampha','#reviewkhachsan']),
  (17, 'Gaming',                       'Gaming & esports',                ARRAY['#game','#lienquan','#freefire','#gamevietnam'])
ON CONFLICT (id) DO NOTHING;

SELECT setval('niche_taxonomy_id_seq', GREATEST(17, (SELECT COALESCE(MAX(id), 1) FROM niche_taxonomy)));
