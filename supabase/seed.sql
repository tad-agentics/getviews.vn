-- seed.sql — GetViews.vn
-- Run after migrations to populate development data.
-- All user IDs are fake UUIDs — replace with real auth.users IDs from Supabase Dashboard
-- after running migrations.

-- ─── Niche Taxonomy ──────────────────────────────────────────────────────────

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

-- Reset sequence if inserting with explicit IDs
SELECT setval('niche_taxonomy_id_seq', 17);

-- ─── Dev User Profiles (seed only — real users created by auth trigger) ──────
-- Note: These UUIDs must match real auth.users rows when testing locally.
-- Create test users in Supabase Dashboard → Auth → Users, then update these UUIDs.

-- Minh — Starter plan creator
INSERT INTO profiles (
  id, display_name, email, avatar_url,
  primary_niche, niche_id, tiktok_handle,
  subscription_tier, deep_credits_remaining, lifetime_credits_used,
  credits_reset_at, daily_free_query_count, is_processing
) VALUES (
  '00000000-0000-0000-0000-000000000001',
  'Nguyễn Minh', 'minh.nguyen@example.com',
  'https://i.pravatar.cc/150?img=12',
  'Review đồ Shopee / Gia dụng', 1, '@minhreview',
  'starter', 27, 3,
  now() + interval '23 days', 0, false
) ON CONFLICT (id) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  subscription_tier = EXCLUDED.subscription_tier,
  deep_credits_remaining = EXCLUDED.deep_credits_remaining;

-- Linh — Pro plan agency user
INSERT INTO profiles (
  id, display_name, email, avatar_url,
  primary_niche, niche_id, tiktok_handle,
  subscription_tier, deep_credits_remaining, lifetime_credits_used,
  credits_reset_at, daily_free_query_count, is_processing
) VALUES (
  '00000000-0000-0000-0000-000000000002',
  'Trần Thị Linh', 'linh.tran@agency.vn',
  'https://i.pravatar.cc/150?img=23',
  'Làm đẹp / Skincare', 2, '@linhagency',
  'pro', 65, 15,
  now() + interval '18 days', 0, false
) ON CONFLICT (id) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  subscription_tier = EXCLUDED.subscription_tier,
  deep_credits_remaining = EXCLUDED.deep_credits_remaining;

-- Free tier user
INSERT INTO profiles (
  id, display_name, email, avatar_url,
  primary_niche, niche_id, tiktok_handle,
  subscription_tier, deep_credits_remaining, lifetime_credits_used,
  daily_free_query_count, is_processing
) VALUES (
  '00000000-0000-0000-0000-000000000003',
  'Phạm Văn Hùng', 'hung.pham@gmail.com',
  'https://i.pravatar.cc/150?img=33',
  'Gaming', 17, '@hungfreefire',
  'free', 7, 3,
  0, false
) ON CONFLICT (id) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  subscription_tier = EXCLUDED.subscription_tier,
  deep_credits_remaining = EXCLUDED.deep_credits_remaining;

-- ─── Subscriptions ────────────────────────────────────────────────────────────

INSERT INTO subscriptions (
  id, user_id, tier, billing_period,
  amount_vnd, deep_credits_granted,
  starts_at, expires_at,
  payos_order_code, payos_payment_id, status
) VALUES (
  '10000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000001',
  'starter', 'monthly',
  249000, 30,
  now() - interval '7 days',
  now() + interval '23 days',
  'GV-SEED-001', 'payos_test_001', 'active'
), (
  '10000000-0000-0000-0000-000000000002',
  '00000000-0000-0000-0000-000000000002',
  'pro', 'annual',
  4788000, 80,
  now() - interval '12 days',
  now() + interval '353 days',
  'GV-SEED-002', 'payos_test_002', 'active'
) ON CONFLICT (id) DO NOTHING;

-- ─── Credit Transactions ──────────────────────────────────────────────────────

INSERT INTO credit_transactions (id, user_id, delta, balance_after, reason, subscription_id) VALUES
  ('20000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001',  30, 30, 'purchase', '10000000-0000-0000-0000-000000000001'),
  ('20000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001',  -1, 29, 'query', null),
  ('20000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000001',  -1, 28, 'query', null),
  ('20000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000001',  -1, 27, 'query', null),
  ('20000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000002',  80, 80, 'purchase', '10000000-0000-0000-0000-000000000002'),
  ('20000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000002',  -1, 79, 'query', null)
ON CONFLICT (id) DO NOTHING;

-- ─── Chat Sessions ────────────────────────────────────────────────────────────

INSERT INTO chat_sessions (id, user_id, first_message, intent_type, credits_used, is_pinned) VALUES
  ('30000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001',
   'Tại sao video review nồi chiên không dầu chỉ 2.000 view?', 'video_diagnosis', 1, false),
  ('30000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001',
   'Hook nào đang hot trong review đồ gia dụng tuần này?', 'trend_spike', 0, false),
  ('30000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000001',
   'Soi kênh @reviewer_top1 — họ đang làm gì?', 'competitor_profile', 1, true),
  ('30000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000001',
   'Viết brief cho KOL quay video nồi chiên không dầu', 'brief_generation', 1, false),
  ('30000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000002',
   'Tìm 10 KOL skincare micro có email trong bio', 'find_creators', 0, false),
  ('30000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000002',
   'Soi kênh của tôi — @linhagency', 'soi_kenh', 1, false)
ON CONFLICT (id) DO NOTHING;

-- ─── Chat Messages (sample per session) ──────────────────────────────────────

INSERT INTO chat_messages (id, session_id, user_id, role, content, intent_type, credits_used, is_free, structured_output) VALUES
  -- Session 1: Video Diagnosis
  ('40000000-0000-0000-0000-000000000001',
   '30000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001',
   'user', 'Tại sao video review nồi chiên không dầu chỉ 2.000 view? https://www.tiktok.com/@minhreview/video/7123456789',
   'video_diagnosis', 1, false, null),
  ('40000000-0000-0000-0000-000000000002',
   '30000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001',
   'assistant', null,
   'video_diagnosis', 0, true,
   '{"diagnosis_rows": [
     {"type": "fail", "finding": "Không mặt trong 3 giây đầu", "benchmark": "92% top video trong niche mở bằng mặt trong 0.5 giây đầu", "fix": "Quay lại mở bằng mặt nhìn camera trong 0.5 giây đầu"},
     {"type": "fail", "finding": "Text overlay ở giây 3.2", "benchmark": "Top video: text xuất hiện trước giây 1", "fix": "Chuyển text lên frame đầu tiên"},
     {"type": "pass", "finding": "Hook Cảnh Báo đúng pattern", "benchmark": "Trung bình 3.2x views so với Kể Chuyện trong niche", "fix": null}
   ], "corpus_cite": {"count": 412, "niche": "review đồ gia dụng", "timeframe": "7 ngày", "updated_hours_ago": 4}}'::jsonb),
  -- Follow-up (free)
  ('40000000-0000-0000-0000-000000000003',
   '30000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001',
   'user', 'Cho mình 3 hook cụ thể để fix video này?',
   'follow_up', 0, true, null),
  ('40000000-0000-0000-0000-000000000004',
   '30000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001',
   'assistant', 'Dựa trên 412 video review đồ gia dụng tháng này, đây là 3 hook đang hiệu quả nhất: 1) "ĐỪNG MUA [sản phẩm] nếu chưa xem video này" — Cảnh Báo hook, 3.2x views. 2) "Chỉ [giá] mà được [lợi ích]" — Giá Sốc hook, 2.8x views. 3) Mặt nhìn thẳng camera + text shock frame 0 — Visual hook.',
   'follow_up', 0, true, null),
  -- Session 5: Find Creators
  ('40000000-0000-0000-0000-000000000005',
   '30000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000002',
   'user', 'Tìm 10 KOL skincare micro có email trong bio',
   'find_creators', 0, true, null),
  ('40000000-0000-0000-0000-000000000006',
   '30000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000002',
   'assistant', null,
   'find_creators', 0, true,
   '{"creator_cards": [
     {"handle": "@skincarebylinh", "display_name": "Linh Beauty", "followers": 28400, "total_likes": 892000, "bio_contact": "linh@beauty.vn", "dominant_hook_type": "Cảnh báo", "posting_frequency_per_week": 5.2, "has_corpus_data": true},
     {"handle": "@dalichda_official", "display_name": "Đa Lịch Da", "followers": 15600, "total_likes": 423000, "bio_contact": "zalo: 0901234567", "dominant_hook_type": "Trước/Sau", "posting_frequency_per_week": 3.8, "has_corpus_data": true},
     {"handle": "@skintips_vn", "display_name": "Skin Tips VN", "followers": 42000, "total_likes": 1200000, "bio_contact": "skintips.vn@gmail.com", "dominant_hook_type": "Kể chuyện", "posting_frequency_per_week": 4.1, "has_corpus_data": false}
   ]}'::jsonb)
ON CONFLICT (id) DO NOTHING;

-- ─── Video Corpus (sample seeded entries for Explore screen) ─────────────────

INSERT INTO video_corpus (
  id, video_id, content_type, niche_id,
  creator_handle, tiktok_url,
  thumbnail_url, video_url,
  frame_urls,
  analysis_json,
  views, likes, comments, shares, engagement_rate,
  indexed_at
) VALUES
  ('50000000-0000-0000-0000-000000000001',
   '7123456001', 'video', 1,
   '@reviewcungme', 'https://www.tiktok.com/@reviewcungme/video/7123456001',
   'https://frames.getviews.vn/7123456001/0.webp',
   'https://media.getviews.vn/videos/7123456001.mp4',
   ARRAY['https://frames.getviews.vn/7123456001/0.webp','https://frames.getviews.vn/7123456001/1.webp'],
   '{"hook_type": "warning", "face_appears_at": 0.0, "first_frame_type": "face_product", "text_overlays": [{"text": "ĐỪNG MUA CÁI NÀY", "appears_at_seconds": 0.0}], "scene_transitions_per_second": 0.8, "audio_transcript_excerpt": "Đừng mua cái này nếu bạn chưa xem hết video", "hook_classification": "canh_bao", "duration_seconds": 28}'::jsonb,
   1200000, 89000, 3200, 42000, 0.1118, now() - interval '3 days'),

  ('50000000-0000-0000-0000-000000000002',
   '7123456002', 'video', 1,
   '@giadungviet', 'https://www.tiktok.com/@giadungviet/video/7123456002',
   'https://frames.getviews.vn/7123456002/0.webp',
   'https://media.getviews.vn/videos/7123456002.mp4',
   ARRAY['https://frames.getviews.vn/7123456002/0.webp'],
   '{"hook_type": "price_shock", "face_appears_at": 0.3, "first_frame_type": "face_product", "text_overlays": [{"text": "Chỉ 89K mà được cái này?!", "appears_at_seconds": 0.2}], "scene_transitions_per_second": 0.6, "audio_transcript_excerpt": "Các bạn ơi chỉ 89 nghìn thôi mà được cái nồi chiên này...", "hook_classification": "gia_soc", "duration_seconds": 22}'::jsonb,
   890000, 67000, 2100, 28000, 0.1092, now() - interval '2 days'),

  ('50000000-0000-0000-0000-000000000003',
   '7123456003', 'video', 2,
   '@skincarebylinh', 'https://www.tiktok.com/@skincarebylinh/video/7123456003',
   'https://frames.getviews.vn/7123456003/0.webp',
   'https://media.getviews.vn/videos/7123456003.mp4',
   ARRAY['https://frames.getviews.vn/7123456003/0.webp','https://frames.getviews.vn/7123456003/1.webp'],
   '{"hook_type": "warning", "face_appears_at": 0.0, "first_frame_type": "face_closeup", "text_overlays": [{"text": "Da tôi hủy vì retinol", "appears_at_seconds": 0.0}], "scene_transitions_per_second": 0.9, "audio_transcript_excerpt": "Mình suýt bỏ skincare luôn vì retinol sai cách...", "hook_classification": "canh_bao", "duration_seconds": 30}'::jsonb,
   2100000, 180000, 8400, 96000, 0.1354, now() - interval '5 days'),

  ('50000000-0000-0000-0000-000000000004',
   '7123456004', 'carousel', 2,
   '@routine.vn', 'https://www.tiktok.com/@routine.vn/video/7123456004',
   'https://frames.getviews.vn/7123456004/0.webp',
   null,
   ARRAY['https://frames.getviews.vn/7123456004/0.webp'],
   '{"slide_count": 7, "hook_slide": 0, "slides": [{"index": 0, "visual_type": "text_graphic", "text_overlays": [{"text": "3 bước routine ban đêm cho da dầu", "appears_at_seconds": null}]},{"index": 1, "visual_type": "product_flat_lay", "text_overlays": [{"text": "Bước 1: Cleansing", "appears_at_seconds": null}]}], "story_arc": "list_steps", "swipe_incentive": "Lướt để xem đủ 3 bước"}'::jsonb,
   450000, 38000, 1800, 22000, 0.1378, now() - interval '1 day'),

  ('50000000-0000-0000-0000-000000000005',
   '7123456005', 'video', 17,
   '@hungfreefire', 'https://www.tiktok.com/@hungfreefire/video/7123456005',
   'https://frames.getviews.vn/7123456005/0.webp',
   'https://media.getviews.vn/videos/7123456005.mp4',
   ARRAY['https://frames.getviews.vn/7123456005/0.webp'],
   '{"hook_type": "curiosity_gap", "face_appears_at": 0.1, "first_frame_type": "gameplay_screen", "text_overlays": [{"text": "Trick Free Fire 99% người không biết", "appears_at_seconds": 0.0}], "scene_transitions_per_second": 1.4, "audio_transcript_excerpt": "Trick này mình mất 6 tháng mới tìm ra...", "hook_classification": "to_mo", "duration_seconds": 25}'::jsonb,
   380000, 29000, 4200, 18000, 0.1345, now() - interval '4 days')
ON CONFLICT (video_id) DO NOTHING;

-- ─── Trend Velocity (sample — week of April 7, 2026) ─────────────────────────

INSERT INTO trend_velocity (id, niche_id, week_start, hook_type_shifts, format_changes, new_hashtags, sound_trends) VALUES
  ('60000000-0000-0000-0000-000000000001', 1, '2026-04-07',
   '{"canh_bao": {"prev_pct": 58, "curr_pct": 62, "delta": 4}, "gia_soc": {"prev_pct": 28, "curr_pct": 21, "delta": -7}, "ke_chuyen": {"prev_pct": 14, "curr_pct": 17, "delta": 3}}'::jsonb,
   '{"unboxing_tinh": {"lifecycle": "declining", "volume_delta": 15, "er_delta": -18}}'::jsonb,
   ARRAY['#mau_do_noi_that','#dogiadung2026'],
   '{"trending_sounds": [{"sound_id": "VN_SOUND_001", "name": "Nhạc lo-fi chill", "niche_count": 4}]}'::jsonb),
  ('60000000-0000-0000-0000-000000000002', 2, '2026-04-07',
   '{"canh_bao": {"prev_pct": 45, "curr_pct": 51, "delta": 6}, "truoc_sau": {"prev_pct": 32, "curr_pct": 28, "delta": -4}}'::jsonb,
   '{"storytime": {"lifecycle": "emerging", "volume_delta": 22, "er_delta": 12}}'::jsonb,
   ARRAY['#routine2026','#damyeu'],
   '{"trending_sounds": []}'::jsonb)
ON CONFLICT (id) DO NOTHING;

-- ─── Hook Effectiveness (sample data — review đồ gia dụng niche) ─────────────

INSERT INTO hook_effectiveness (id, niche_id, hook_type, avg_views, avg_engagement_rate, avg_completion_rate, sample_size, trend_direction, computed_at) VALUES
  ('70000000-0000-0000-0000-000000000001', 1, 'canh_bao',   920000, 0.1084, 0.68, 48, 'rising',  now() - interval '1 day'),
  ('70000000-0000-0000-0000-000000000002', 1, 'gia_soc',    680000, 0.0921, 0.54, 35, 'stable',  now() - interval '1 day'),
  ('70000000-0000-0000-0000-000000000003', 1, 'ke_chuyen',  288000, 0.0742, 0.41, 29, 'stable',  now() - interval '1 day'),
  ('70000000-0000-0000-0000-000000000004', 2, 'canh_bao',  1450000, 0.1220, 0.72, 62, 'rising',  now() - interval '1 day'),
  ('70000000-0000-0000-0000-000000000005', 2, 'truoc_sau',  820000, 0.0980, 0.61, 44, 'stable',  now() - interval '1 day')
ON CONFLICT (id) DO NOTHING;
