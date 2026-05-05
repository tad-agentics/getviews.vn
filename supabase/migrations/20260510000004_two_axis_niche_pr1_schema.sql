-- Two-axis niche refactor — PR1 of 6.
--
-- Splits the conflated ``niche_taxonomy`` into two separate concerns:
--
--   1. ``creator_niches``        — UX-facing buckets (~13). Drives
--      onboarding, Settings, Trends pills, profile self-identification.
--      Coarse, friendly Vietnamese labels matching how creators refer
--      to themselves ("tôi làm content beauty", "tôi làm content
--      lifestyle"). Cognitive load < 1s for a creator to pick.
--
--   2. ``content_classifications`` — analysis-facing categories (~70).
--      Drives video_corpus tagging, benchmark grouping, pattern thesis
--      sample selection. Sharp boundaries on (topic × format), so
--      benchmarks don't blur food-review with food-recipe-tutorial.
--
-- Each ``content_classification`` belongs to one or more
-- ``creator_niches`` via the junction table. A creator picking
-- "Beauty & Skincare" in onboarding gets recommendations / pattern
-- thesis aggregated across all beauty content_classes (skincare
-- routine + makeup tutorial + product review + haul + …).
--
-- ── Why this exists ──────────────────────────────────────────────────
--
-- The single ``niche_taxonomy`` was being asked to do two opposing
-- jobs at once:
--   - Analysis wants fine granularity (so beauty_skincare_routine and
--     beauty_makeup_tutorial don't blur — they have different hook
--     conventions, retention curves, viewer intent).
--   - UX wants coarse granularity (so a creator picks one thing, fast,
--     without paralysis between 30 sub-niches).
-- Every merge / retire / add migration in 2026-04→05 was a tradeoff
-- between these two pulls. This refactor lets each axis be optimised
-- independently.
--
-- ── PR1 scope (this migration) ───────────────────────────────────────
--
-- Schema + seed data ONLY. Does NOT touch:
--   - ``video_corpus`` (existing ``niche_id`` column unchanged — PR2
--     adds ``content_class_id``)
--   - ``profiles`` (existing ``primary_niche`` unchanged — PR3 adds
--     ``creator_niche_id``)
--   - ``niche_taxonomy`` (kept for compat — PR6 retires it)
-- Old code keeps working against old taxonomy. New code can opt into
-- new tables. Subsequent PRs migrate the data in stages.
--
-- ── Idempotency ──────────────────────────────────────────────────────
--
-- All CREATE TABLE IF NOT EXISTS. INSERT … ON CONFLICT (id) DO NOTHING
-- so re-running on a half-applied DB is a no-op. setval() at the end
-- bumps SERIAL sequences so future inserts pick the next free id.

BEGIN;

-- ── 1. creator_niches ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS creator_niches (
  id           SERIAL PRIMARY KEY,
  slug         TEXT NOT NULL UNIQUE,           -- stable id for FE filter chips
  name_vn      TEXT NOT NULL,                  -- Vietnamese display label
  name_en      TEXT NOT NULL,                  -- English label (logs, i18n)
  description_vn TEXT,                         -- onboarding helper text
  display_order INTEGER NOT NULL DEFAULT 100,  -- sidebar / picker order
  active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE creator_niches ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Anyone can read creator niches" ON creator_niches;
CREATE POLICY "Anyone can read creator niches"
  ON creator_niches FOR SELECT
  TO anon, authenticated
  USING (active = TRUE);

INSERT INTO creator_niches (id, slug, name_vn, name_en, description_vn, display_order) VALUES
  (1,  'beauty',       'Làm đẹp · Skincare',         'Beauty & Skincare',
       'Skincare routine, makeup, review mỹ phẩm, haul đồ làm đẹp.', 10),
  (2,  'fashion',      'Thời trang · Phụ kiện',      'Fashion & Style',
       'Outfit, OOTD, túi xách, giày, trang sức, đồng hồ, kính mắt.', 20),
  (3,  'food',         'Ẩm thực · Ăn uống',          'Food & Drink',
       'Review quán ăn, công thức nấu, ăn vặt, cafe, đồ uống, food challenge.', 30),
  (4,  'lifestyle',    'Đời sống · Tâm sự',          'Lifestyle & Storytelling',
       'Vlog hằng ngày, morning routine, POV đời sống, tâm sự, chuyện công sở.', 40),
  (5,  'comedy',       'Hài · Giải trí',             'Comedy & Entertainment',
       'Hài skits, parody, react, cover hát, dance challenge.', 50),
  (6,  'family',       'Nuôi con · Gia đình',        'Parenting & Family',
       'Mẹ bỉm, bố nuôi con, family vlog, mẹo nuôi dạy.', 60),
  (7,  'education',    'Giáo dục · Sự nghiệp',       'Education & Career',
       'Học thuật, ngoại ngữ, kỹ năng sống, hướng nghiệp, BookTok.', 70),
  (8,  'tech_gaming',  'Công nghệ · Gaming',         'Tech & Gaming',
       'Review gadget, hướng dẫn phần mềm, gameplay, esports, livestream game.', 80),
  (9,  'business',     'Kinh doanh · Tài chính',     'Business & Finance',
       'Affiliate, livestream commerce, MMO, đầu tư, bất động sản, finance personal.', 90),
  (10, 'wellness',     'Sức khoẻ · Wellness',        'Wellness & Health',
       'Mindfulness, sleep, supplement, nutrition phục hồi, holistic lifestyle.', 100),
  (11, 'travel',       'Du lịch · Thể thao',         'Travel & Outdoor Sports',
       'Du lịch trong/ngoài nước, marathon outdoor, trekking, camping, thể thao ngoài trời.', 110),
  (12, 'auto',         'Ô tô · Xe máy',              'Auto & Moto',
       'Review xe, lái thử, mod xe, văn hoá moto, tin tức ngành xe.', 120),
  (13, 'pets_home',    'Thú cưng · Nhà cửa',         'Pets & Home',
       'Thú cưng, mẹo chăm pet, decor nhà cửa, organize, DIY home.', 130),
  (14, 'gym_fitness',  'Gym · Fitness',              'Gym & Fitness',
       'Gym workout, yoga, calisthenics, chạy bộ marathon, body training.', 105)
ON CONFLICT (id) DO NOTHING;

SELECT setval('creator_niches_id_seq', GREATEST(14, (SELECT COALESCE(MAX(id), 1) FROM creator_niches)));

-- ── 2. content_classifications ───────────────────────────────────────
-- Comprehensive (topic × format) categories. Ingest will classify
-- each video into ONE primary content_class; reports group on this
-- column. ``format_axis`` is denormalised so cross-niche format
-- queries ("show me all POV-storytelling content across niches") are
-- cheap without joins.

CREATE TABLE IF NOT EXISTS content_classifications (
  id              SERIAL PRIMARY KEY,
  slug            TEXT NOT NULL UNIQUE,
  name_vn         TEXT NOT NULL,
  name_en         TEXT NOT NULL,
  -- Format primary: cross-niche grouping for "format-pattern" reports.
  -- Enum-like: keep stable; add new values via migration.
  format_axis     TEXT NOT NULL,
  -- Topic primary: for narrowing within a creator_niche.
  topic_axis      TEXT NOT NULL,
  description_vn  TEXT,
  active          BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE content_classifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Anyone can read content classifications" ON content_classifications;
CREATE POLICY "Anyone can read content classifications"
  ON content_classifications FOR SELECT
  TO anon, authenticated
  USING (active = TRUE);

CREATE INDEX IF NOT EXISTS idx_content_classifications_format ON content_classifications(format_axis);
CREATE INDEX IF NOT EXISTS idx_content_classifications_topic  ON content_classifications(topic_axis);

INSERT INTO content_classifications (id, slug, name_vn, name_en, format_axis, topic_axis, description_vn) VALUES
  -- ── Beauty (5)
  (1,  'beauty_skincare_routine',  'Skincare routine',          'Skincare routine tutorial',           'tutorial',         'beauty',     'Tutorial routine sáng/tối, áp dụng sản phẩm theo bước.'),
  (2,  'beauty_makeup_tutorial',   'Makeup tutorial',           'Makeup tutorial',                      'tutorial',         'beauty',     'Hướng dẫn make up theo look, theo dịp.'),
  (3,  'beauty_product_review',    'Review mỹ phẩm',            'Beauty product review',                'review_unboxing',  'beauty',     'Review từng sản phẩm, so sánh A vs B.'),
  (4,  'beauty_haul',              'Haul mỹ phẩm',              'Beauty haul / shopping',               'review_unboxing',  'beauty',     'Mua nhiều, mở hộp lần lượt.'),
  (5,  'beauty_problem_solution',  'Vấn đề da & cách trị',      'Beauty problem-solution POV',          'pov_storytelling', 'beauty',     'POV "da tôi tệ thế nào…" + journey trị mụn / sạm.'),
  -- ── Fashion (5)
  (6,  'fashion_outfit_styling',   'Outfit phối đồ',            'Outfit styling POV',                   'pov_storytelling', 'fashion',    'POV phối đồ theo dịp / mood / weather.'),
  (7,  'fashion_haul_shopping',    'Haul thời trang',           'Fashion haul / shopping',              'review_unboxing',  'fashion',    'Mua nhiều outfit / phụ kiện, thử lần lượt.'),
  (8,  'fashion_accessory_review', 'Phụ kiện review',           'Accessory review',                     'review_unboxing',  'fashion',    'Túi, giày, đồng hồ, trang sức, kính mắt cụ thể.'),
  (9,  'fashion_lookbook_montage', 'Lookbook montage',          'Fashion lookbook montage',             'montage_highlights', 'fashion',  'Series outfit nhanh, chuyển cảnh nhịp nhạc.'),
  (10, 'fashion_thrift_secondhand','Thrift / đồ secondhand',    'Thrift / secondhand vlog',             'vlog_daily',       'fashion',    'Đi chợ thrift, đồ vintage, restyle.'),
  -- ── Food (5)
  (11, 'food_restaurant_review',   'Review quán ăn',            'Restaurant review POV',                'pov_storytelling', 'food',       'POV ăn ở quán, phản ứng, đánh giá địa chỉ.'),
  (12, 'food_street_food_vlog',    'Ăn vặt / street food',      'Street food vlog',                     'vlog_daily',       'food',       'Đi ăn dạo phố, food tour, ẩm thực địa phương.'),
  (13, 'food_recipe_tutorial',     'Công thức nấu ăn',          'Recipe tutorial',                      'tutorial',         'food',       'Hướng dẫn món, top-down camera, voice-over.'),
  (14, 'food_challenge',           'Food challenge',            'Food challenge / mukbang',             'react_commentary', 'food',       'Ăn nhiều / cay / món lạ, reaction-driven.'),
  (15, 'food_drinks_cafe',         'Đồ uống & cafe',            'Drinks & cafe review',                 'review_unboxing',  'food',       'Cafe culture, đồ uống mới, review menu.'),
  -- ── Lifestyle / Storytelling (8)
  (16, 'lifestyle_morning_routine','Morning / night routine',   'Morning / night routine vlog',         'vlog_daily',       'lifestyle',  'Routine mở đầu / kết ngày, slow content aesthetic.'),
  (17, 'lifestyle_daily_vlog',     'Daily vlog',                'Daily vlog',                           'vlog_daily',       'lifestyle',  'Một ngày của tôi, day-in-the-life.'),
  (18, 'lifestyle_minimalism',     'Minimalism / dọn dẹp',      'Minimalism & organize',                'tutorial',         'lifestyle',  'Sống tối giản, dọn dẹp, organize không gian.'),
  (19, 'lifestyle_self_improvement','Self-improvement',         'Self-improvement advice',              'talking_head_advice','lifestyle','Triết học 20s, kỷ luật, mindset.'),
  (20, 'storytelling_relationship','POV tình yêu / quan hệ',    'Relationship storytelling POV',        'pov_storytelling', 'storytelling','Chuyện yêu xa, chia tay, quan hệ gia đình.'),
  (21, 'storytelling_workplace',   'POV công sở',               'Workplace storytelling POV',           'pov_storytelling', 'storytelling','Chuyện công ty, sếp, đồng nghiệp, lương thưởng.'),
  (22, 'storytelling_late_night',  'Tâm sự đêm khuya',          'Late-night reflection',                'pov_storytelling', 'storytelling','Tâm sự, suy nghĩ, reflection slow-paced.'),
  (23, 'lifestyle_aesthetic',      'Lifestyle aesthetic',       'Aspirational aesthetic content',       'montage_highlights','lifestyle', 'Slow-mo lifestyle aesthetic, no narrative.'),
  -- ── Comedy / Music (6)
  (24, 'comedy_skit_scripted',     'Hài skit kịch bản',         'Scripted comedy skit',                 'skit_scripted',    'comedy',     'Tiểu phẩm có kịch bản, role-play.'),
  (25, 'comedy_parody_satire',     'Parody / châm biếm',        'Parody / satire',                      'skit_scripted',    'comedy',     'Nhại lại trend, châm biếm xã hội.'),
  (26, 'comedy_observational',     'Hài quan sát relatable',    'Observational humor',                  'pov_storytelling', 'comedy',     '"Người Việt khi…" relatable observation.'),
  (27, 'comedy_react_response',    'React / response',          'React / response comedy',              'react_commentary', 'comedy',     'Phản ứng video / drama / trends.'),
  (28, 'music_cover_singing',      'Cover hát / âm nhạc',       'Music cover / singing',                'music_performance','music',      'Hát cover, acoustic, livestage.'),
  (29, 'music_dance_choreography', 'Dance / choreography',      'Dance choreography',                   'dance_choreography','music',     'Dance challenge, K-pop dance, choreography.'),
  -- ── Family / Parenting (5)
  (30, 'parenting_baby_milestone', 'Mốc phát triển em bé',      'Baby milestone content',               'vlog_daily',       'family',     'Bé tháng thứ N, hành trình lớn lên.'),
  (31, 'parenting_mom_humor',      'Mẹ bỉm relatable',          'Mom relatable humor',                  'comedy_observational','family',  'Hài relatable đời sống mẹ bỉm.'),
  (32, 'parenting_dad_content',    'Bố nuôi con',               'Dad parenting content',                'vlog_daily',       'family',     'Bố chăm con, dad-and-baby moments.'),
  (33, 'parenting_tips_advice',    'Mẹo nuôi dạy',              'Parenting tips & advice',              'talking_head_advice','family',   'Giáo dục con, dinh dưỡng, kỷ luật.'),
  (34, 'family_vlog_daily',        'Family vlog',               'Family daily vlog',                    'vlog_daily',       'family',     'Sinh hoạt cả gia đình, đa thế hệ.'),
  -- ── Education (5)
  (35, 'edu_academic_explain',     'Giải thích học thuật',      'Academic explainer',                   'talking_head_advice','education','Toán, lý, hoá, lịch sử explain.'),
  (36, 'edu_language_lesson',      'Học ngoại ngữ',             'Language lesson',                      'tutorial',         'education',  'Tiếng Anh, Hàn, Trung, Nhật bài giảng.'),
  (37, 'edu_life_skill',           'Kỹ năng sống',              'Life skill tutorial',                  'tutorial',         'education',  'Giao tiếp, kỹ năng mềm, kỹ năng học tập.'),
  (38, 'edu_career_advice',        'Hướng nghiệp / sự nghiệp',  'Career advice',                        'talking_head_advice','education','Chọn nghề, phỏng vấn, lương, kỹ năng nghề.'),
  (39, 'edu_book_review',          'Review sách / BookTok',     'Book review / BookTok',                'talking_head_advice','education','Review sách, đọc sách, BookTok VN.'),
  -- ── Tech / Gaming (5)
  (40, 'tech_gadget_unboxing',     'Mở hộp gadget',             'Tech gadget unboxing',                 'review_unboxing',  'tech',       'Điện thoại, laptop, smart home, đồ tech.'),
  (41, 'tech_software_tutorial',   'Hướng dẫn phần mềm',        'Software tutorial',                    'tutorial',         'tech',       'Tutorial app, web, AI, productivity.'),
  (42, 'gaming_gameplay',          'Gameplay / highlights',     'Gameplay highlights',                  'montage_highlights','gaming',    'Highlight clips, big plays, funny moments.'),
  (43, 'gaming_review_commentary', 'Review game / commentary',  'Game review / commentary',             'talking_head_advice','gaming',   'Review game mới, commentary live.'),
  (44, 'gaming_esports_news',      'Esports / tin tức game',    'Esports news',                         'talking_head_advice','gaming',   'Tin tức giải đấu, transfer, meta.'),
  -- ── Business / Finance (6)
  (45, 'finance_personal_advice',  'Tài chính cá nhân',         'Personal finance advice',              'talking_head_advice','finance',  'Quản lý chi tiêu, tiết kiệm, lập kế hoạch.'),
  (46, 'finance_investment',       'Đầu tư / chứng khoán',      'Investment explainer',                 'talking_head_advice','finance',  'Chứng khoán, crypto, vàng, vĩ mô.'),
  (47, 'finance_business_story',   'Kinh doanh storytelling',   'Business storytelling',                'pov_storytelling', 'finance',    'POV kinh doanh, founder story, vấp ngã.'),
  (48, 'mmo_affiliate_education',  'MMO / Affiliate education', 'MMO / affiliate course',               'talking_head_advice','business', 'Dạy kiếm tiền online, affiliate, KOC.'),
  (49, 'ecommerce_shopee_review',  'Review Shopee / gia dụng',  'Shopee affiliate review (buyer-side)', 'review_unboxing',  'business',   'Review đồ Shopee, gia dụng, để người mua quyết định.'),
  (50, 'ecommerce_live_commerce',  'Livestream bán hàng',       'Live commerce anchor',                 'live_commerce',    'business',   'Anchor livestream Shopee/TikTok Shop.'),
  (51, 'real_estate_listing',      'Listing bất động sản',      'Real estate listing tour',             'vlog_daily',       'real_estate','Tour căn hộ, dự án, listing thực tế.'),
  -- ── Wellness / Fitness (8)
  (52, 'wellness_mindfulness',     'Mindfulness / thiền',       'Mindfulness / meditation',             'talking_head_advice','wellness', 'Thiền định, mindfulness, hơi thở.'),
  (53, 'wellness_sleep_recovery',  'Giấc ngủ / phục hồi',       'Sleep & recovery',                     'talking_head_advice','wellness', 'Mẹo ngủ ngon, phục hồi mệt mỏi, stress.'),
  (54, 'wellness_nutrition',       'Dinh dưỡng & supplement',   'Nutrition & supplement',               'talking_head_advice','wellness', 'Vitamin, collagen, supplement, ăn lành mạnh.'),
  (55, 'wellness_holistic',        'Lifestyle holistic',        'Holistic lifestyle',                   'vlog_daily',       'wellness',   'Sống xanh, clean living, women health.'),
  (56, 'fitness_gym_tutorial',     'Gym workout tutorial',      'Gym workout tutorial',                 'tutorial',         'fitness',    'Form chuẩn, set/rep, leg day, push-pull.'),
  (57, 'fitness_yoga_pilates',     'Yoga / Pilates',            'Yoga / pilates',                       'tutorial',         'fitness',    'Yoga giảm cân, eo thon, hồi phục sau sinh.'),
  (58, 'fitness_calisthenics',     'Calisthenics / bodyweight', 'Calisthenics / bodyweight',            'tutorial',         'fitness',    'Tập thể hình tự trọng lượng, street workout.'),
  (59, 'fitness_outdoor_running',  'Chạy bộ / marathon',        'Running / marathon',                   'vlog_daily',       'fitness',    'Chạy bộ, runner culture, race vlog.'),
  -- ── Travel / Outdoor / Sports (5)
  (60, 'travel_destination',       'Điểm đến du lịch',          'Travel destination vlog',              'vlog_daily',       'travel',     'Tour địa điểm, hidden gems, review khách sạn.'),
  (61, 'travel_food_tour',         'Du lịch ẩm thực',           'Travel food tour',                     'vlog_daily',       'travel',     'Foodie travel, đặc sản địa phương.'),
  (62, 'travel_tips_planning',     'Mẹo du lịch / lên kế hoạch','Travel tips & planning',               'talking_head_advice','travel',   'Lập kế hoạch, mẹo budget, visa, packing.'),
  (63, 'travel_adventure',         'Phiêu lưu / outdoor',       'Adventure / outdoor',                  'montage_highlights','travel',    'Trekking, leo núi, kayak, surfing.'),
  (64, 'sports_event_highlight',   'Highlight thể thao',        'Sports event highlight',               'montage_highlights','sports',    'Bóng đá, pickleball, badminton, tennis.'),
  -- ── Auto / Moto (4)
  (65, 'auto_car_review',          'Review xe ô tô',            'Car review test drive',                'review_unboxing',  'auto',       'Lái thử, review nội thất, so sánh xe.'),
  (66, 'auto_moto_culture',        'Văn hoá moto',              'Moto culture / ride',                  'vlog_daily',       'auto',       'Phượt moto, văn hoá biker, ride content.'),
  (67, 'auto_modification',        'Mod xe / tuning',           'Modification / tuning',                'tutorial',         'auto',       'Độ xe, tuning, lắp phụ kiện.'),
  (68, 'auto_news_industry',       'Tin tức ngành xe',          'Auto news / industry',                 'talking_head_advice','auto',     'Ra mắt xe mới, giá xe, ngành.'),
  -- ── Pets / Home (6)
  (69, 'pets_cute_compilation',    'Pet cute / funny',          'Pet cute / funny compilation',         'montage_highlights','pets',      'Mèo / chó cute, funny moments, slow-mo.'),
  (70, 'pets_care_tips',           'Mẹo chăm pet',              'Pet care tips',                        'talking_head_advice','pets',     'Chăm sóc, dinh dưỡng, sức khoẻ pet.'),
  (71, 'pets_training',            'Huấn luyện pet',            'Pet training tutorial',                'tutorial',         'pets',       'Train chó / mèo, mẹo nghe lời.'),
  (72, 'pets_owner_storytelling',  'POV chủ pet',               'Pet-owner storytelling',               'pov_storytelling', 'pets',       'POV "có pet là…" relatable storytelling.'),
  (73, 'home_decor_inspiration',   'Decor / nội thất',          'Home decor inspiration',               'montage_highlights','home',      'Inspiration nhà đẹp, room tour aesthetic.'),
  (74, 'home_renovation_diy',      'Cải tạo / DIY',             'Home renovation / DIY',                'tutorial',         'home',       'DIY trang trí, cải tạo phòng, hack tổ chức.')
ON CONFLICT (id) DO NOTHING;

SELECT setval('content_classifications_id_seq', GREATEST(74, (SELECT COALESCE(MAX(id), 1) FROM content_classifications)));

-- ── 3. Junction: creator_niche ↔ content_classifications ─────────────
-- Each content_class belongs to one or more creator_niches. Most are
-- 1:1; some span (e.g. travel_food_tour belongs to both Travel and
-- Food). The junction encodes "if creator picks Beauty, what
-- content_classes do we consider 'theirs' for benchmark queries".

CREATE TABLE IF NOT EXISTS creator_niche_content_classes (
  creator_niche_id      INTEGER NOT NULL REFERENCES creator_niches(id) ON DELETE CASCADE,
  content_class_id      INTEGER NOT NULL REFERENCES content_classifications(id) ON DELETE CASCADE,
  is_primary            BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (creator_niche_id, content_class_id)
);

ALTER TABLE creator_niche_content_classes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Anyone can read creator-niche content-class map" ON creator_niche_content_classes;
CREATE POLICY "Anyone can read creator-niche content-class map"
  ON creator_niche_content_classes FOR SELECT
  TO anon, authenticated
  USING (true);

CREATE INDEX IF NOT EXISTS idx_cncc_creator_niche ON creator_niche_content_classes(creator_niche_id);
CREATE INDEX IF NOT EXISTS idx_cncc_content_class ON creator_niche_content_classes(content_class_id);

-- Mapping rows. Some content_classes appear under multiple creator_niches
-- (e.g. travel_food_tour ∈ {Travel, Food}; storytelling_relationship ∈
-- {Lifestyle, Comedy} for the relatable-humor sub-pattern). is_primary
-- flags which creator_niche is the canonical home for benchmarking;
-- secondary memberships are for cross-niche browse only.

INSERT INTO creator_niche_content_classes (creator_niche_id, content_class_id, is_primary) VALUES
  -- Beauty (1)
  (1, 1, TRUE), (1, 2, TRUE), (1, 3, TRUE), (1, 4, TRUE), (1, 5, TRUE),
  -- Fashion (2)
  (2, 6, TRUE), (2, 7, TRUE), (2, 8, TRUE), (2, 9, TRUE), (2, 10, TRUE),
  -- Food (3)
  (3, 11, TRUE), (3, 12, TRUE), (3, 13, TRUE), (3, 14, TRUE), (3, 15, TRUE),
  (3, 61, FALSE), -- travel_food_tour also lives here for browsing
  -- Lifestyle / Storytelling (4)
  (4, 16, TRUE), (4, 17, TRUE), (4, 18, TRUE), (4, 19, TRUE),
  (4, 20, TRUE), (4, 21, TRUE), (4, 22, TRUE), (4, 23, TRUE),
  (4, 26, FALSE), -- comedy_observational often relatable lifestyle
  -- Comedy / Entertainment (5)
  (5, 24, TRUE), (5, 25, TRUE), (5, 26, TRUE), (5, 27, TRUE),
  (5, 28, TRUE), (5, 29, TRUE),
  -- Family / Parenting (6)
  (6, 30, TRUE), (6, 31, TRUE), (6, 32, TRUE), (6, 33, TRUE), (6, 34, TRUE),
  -- Education / Career (7)
  (7, 35, TRUE), (7, 36, TRUE), (7, 37, TRUE), (7, 38, TRUE), (7, 39, TRUE),
  -- Tech / Gaming (8)
  (8, 40, TRUE), (8, 41, TRUE), (8, 42, TRUE), (8, 43, TRUE), (8, 44, TRUE),
  -- Business / Finance (9)
  (9, 45, TRUE), (9, 46, TRUE), (9, 47, TRUE), (9, 48, TRUE),
  (9, 49, TRUE), (9, 50, TRUE), (9, 51, TRUE),
  -- Wellness / Health (10) — non-fitness only (mindfulness, sleep, nutrition, holistic)
  (10, 52, TRUE), (10, 53, TRUE), (10, 54, TRUE), (10, 55, TRUE),
  -- Travel / Outdoor Sports (11)
  (11, 60, TRUE), (11, 61, TRUE), (11, 62, TRUE), (11, 63, TRUE), (11, 64, TRUE),
  -- Auto / Moto (12)
  (12, 65, TRUE), (12, 66, TRUE), (12, 67, TRUE), (12, 68, TRUE),
  -- Pets / Home (13)
  (13, 69, TRUE), (13, 70, TRUE), (13, 71, TRUE), (13, 72, TRUE),
  (13, 73, TRUE), (13, 74, TRUE),
  -- Gym / Fitness (14) — physical training (gym, yoga, calisthenics, running)
  (14, 56, TRUE), (14, 57, TRUE), (14, 58, TRUE), (14, 59, TRUE),
  (11, 59, FALSE), -- running/marathon also surfaces under Travel & Outdoor Sports
  (10, 57, FALSE)  -- yoga also browsable under Wellness (mindfulness practitioners)
ON CONFLICT (creator_niche_id, content_class_id) DO NOTHING;

-- ── 4. Mapping from legacy niche_taxonomy → creator_niches ───────────
-- Used by PR3 (profile backfill) and PR2 (corpus backfill heuristic).
-- Stored as a function so call sites have a stable interface and the
-- mapping logic lives in one place.

CREATE OR REPLACE FUNCTION map_legacy_niche_to_creator_niche(legacy_id INTEGER)
RETURNS INTEGER
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT CASE legacy_id
    WHEN 1  THEN 9   -- Shopee review (retired) → Business & Finance
    WHEN 2  THEN 1   -- Skincare → Beauty
    WHEN 3  THEN 2   -- Thời trang → Fashion
    WHEN 4  THEN 3   -- Food → Food
    WHEN 5  THEN 9   -- Kinh doanh online → Business & Finance
    WHEN 6  THEN 4   -- Chị đẹp (retired) → Lifestyle (was aspirational)
    WHEN 7  THEN 6   -- Mẹ bỉm → Family
    WHEN 8  THEN 14  -- Gym / Fitness VN → Gym & Fitness
    WHEN 9  THEN 8   -- Tech → Tech & Gaming
    WHEN 10 THEN 9   -- Bất động sản → Business & Finance
    WHEN 11 THEN 7   -- EduTok → Education
    WHEN 12 THEN 9   -- Livestream (retired) → Business & Finance
    WHEN 13 THEN 5   -- Hài → Comedy
    WHEN 14 THEN 12  -- Auto/Moto → Auto & Moto
    WHEN 15 THEN 9   -- Tài chính → Business & Finance
    WHEN 16 THEN 11  -- Travel → Travel & Outdoor Sports
    WHEN 17 THEN 8   -- Gaming → Tech & Gaming
    WHEN 18 THEN 3   -- Nấu ăn (retired) → Food
    WHEN 19 THEN 13  -- Pets → Pets & Home
    WHEN 20 THEN 13  -- Home decor → Pets & Home
    WHEN 21 THEN 11  -- Sports → Travel & Outdoor Sports
    WHEN 22 THEN 5   -- K-pop (retired) → Comedy & Entertainment
    WHEN 23 THEN 7   -- Language (retired) → Education
    WHEN 24 THEN 9   -- Crypto (retired) → Business & Finance
    WHEN 25 THEN 12  -- Moto culture (retired) → Auto & Moto
    WHEN 26 THEN 10  -- Wellness → Wellness & Health
    ELSE NULL
  END;
$$;

-- ── 5. Douyin label cleanup — Vietnamese-first policy ────────────────
-- douyin_niche_taxonomy and creator_niches both render to VN users.
-- Two Douyin rows currently use English-first labels which break the
-- "VN primary, loanword in slot 2" policy applied to creator_niches:
--   id 2 ('beauty'): "Beauty · Skincare" → "Làm đẹp · Skincare"
--   id 6 ('tech'):   "Tech · Setup"      → "Công nghệ · Setup"
-- Other Douyin labels (Slow-life, F&B, Nội thất, Tài chính cá nhân,
-- Nuôi con · Gia đình) already comply and are intentionally distinct
-- from creator_niches (Douyin = Chinese TikTok corpus, different
-- ecosystem; aligning typography only, not scope).

DO $$
BEGIN
  IF to_regclass('public.douyin_niche_taxonomy') IS NOT NULL THEN
    UPDATE douyin_niche_taxonomy SET name_vn = 'Làm đẹp · Skincare' WHERE slug = 'beauty';
    UPDATE douyin_niche_taxonomy SET name_vn = 'Công nghệ · Setup'  WHERE slug = 'tech';
  END IF;
END $$;

COMMIT;
