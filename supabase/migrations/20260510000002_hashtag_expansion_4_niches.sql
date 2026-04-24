-- 2026-05-10 — hashtag pool expansion for 4 undersized niches.
--
-- Wave 1 PR #5 of the revised implementation plan. Closes the
-- Axis 1 "hashtag-starved niche" gap: 4 niches were operating at
-- 21-25 signal_hashtags (vs Travel at 106, Ô tô 82, Skincare 88),
-- bottlenecking ingest pool diversity.
--
-- Targets (pre → post):
--   Tài chính / Đầu tư        21 → 68
--   Chị đẹp                    23 → 68
--   Bất động sản               24 → 67
--   Nấu ăn / Công thức         25 → 68
--
-- Additions curated from:
--   - Common Vietnamese creator hashtag patterns in each domain
--   - English equivalents commonly used by VN creators (crypto,
--     trading, ootd, foodie)
--   - Sub-genre / specific-topic tags (sector names, city tags,
--     product/style categories)
--   - Existing richly-provisioned niches as templates (Travel,
--     Ô tô, Skincare)
--
-- NOT added: cross-niche trend tags (#xuhuong, #fyp, #tiktokviet)
-- — those are signal-noise on any niche query and dilute per-niche
-- ingest precision. Keep signal_hashtags narrow-topical.
--
-- Reader/writer: cloud-run/getviews_pipeline/corpus_ingest.py
-- `_fetch_niche_pool` iterates signal_hashtags up to
-- BATCH_HASHTAG_FETCH_LIMIT (6 by default) ordered by 14-day ingest
-- yield — so adding more hashtags doesn't explode cost, it gives
-- the yield-ranker more options to pick from each run.

-- ── Tài chính / Đầu tư (id=15) ──────────────────────────────────────
-- 21 → 68 (+47 additions)
UPDATE public.niche_taxonomy
SET signal_hashtags = ARRAY[
  -- existing 21 preserved
  '#taichinh', '#taichinhcanhan', '#tietkiem', '#dautu', '#quanlychitieu',
  '#tietkiemthongminh', '#chungkhoan', '#cophieu', '#quydautu', '#nghihuu',
  '#FIRE', '#financialfreedom', '#richhabits', '#hoachdinhcuocsong', '#taichinhvietnam',
  '#kiemtienthongminh', '#canhbaodautu', '#thitruong', '#laisuatnganhang', '#vangbac',
  '#kinhte',
  -- 47 additions
  '#crypto', '#bitcoin', '#btc', '#ethereum', '#eth',
  '#forex', '#trading', '#tradingcrypto', '#tradingchungkhoan', '#daytrader',
  '#vnindex', '#chungkhoanviet', '#chungkhoanvietnam', '#phantichcophieu', '#phantichkythuat',
  '#etf', '#traiphieu', '#vang', '#vangmieng', '#giavang',
  '#lamgiau', '#tudotaichinh', '#kiemtienonline', '#thunhapphudong', '#thunhapthudong',
  '#budget', '#budgeting', '#savings', '#saving', '#investment',
  '#investing', '#passiveincome', '#moneytips', '#financialliteracy', '#quanlytien',
  '#thetindung', '#vayonline', '#nganhang', '#fintech', '#startup',
  '#taichinh2026', '#dauthilam', '#kienthuctaichinh', '#huongdantaichinh', '#kiemtien',
  '#laisuat2026', '#nhadautu'
]
WHERE id = 15;

-- ── Chị đẹp (id=6) ──────────────────────────────────────────────────
-- 23 → 68 (+45 additions)
UPDATE public.niche_taxonomy
SET signal_hashtags = ARRAY[
  -- existing 23 preserved
  '#chidep', '#hotgirl', '#hotgirlviet', '#covai', '#songdep',
  '#dailylife', '#girlboss', '#phunut', '#congviec', '#thanhcong',
  '#dayinmylife', '#livingalone', '#tuvuytinh', '#girly', '#congchua',
  '#lifestylevietnam', '#livingmybestlife', '#phongcachsong', '#hotgirllifestyle', '#chilamdep',
  '#chidepdapgioresong', '#chidepconcert', '#trangphap',
  -- 45 additions
  '#phunudep', '#phunuduyen', '#phunuviet', '#phunutudo', '#doidep',
  '#phongcachphunu', '#girlsgirl', '#womenempowerment', '#girlpower', '#femininelifestyle',
  '#aestheticlife', '#softgirl', '#softlife', '#thatlife', '#slowliving',
  '#coffeetime', '#brunchvibes', '#weekendvibes', '#morningroutine', '#nighttimeroutine',
  '#selfcare', '#selflove', '#meetgirl', '#chamsocbanthan', '#dayinmylifevn',
  '#ootd', '#makeuplook', '#makeupviet', '#outfitcongso', '#phoidocongso',
  '#chidepvang', '#chidepbold', '#chidepthekien', '#mixmatch', '#thoitrangnu',
  '#beauty', '#beautyaesthetic', '#chidepkita', '#sgirlvibes', '#musoft',
  '#workingwoman', '#executivewoman', '#girlceo', '#chidepcafe', '#chidepdaily'
]
WHERE id = 6;

-- ── Bất động sản (id=10) ────────────────────────────────────────────
-- 24 → 67 (+43 additions)
UPDATE public.niche_taxonomy
SET signal_hashtags = ARRAY[
  -- existing 24 preserved
  '#batdongsan', '#nhadat', '#muanha', '#thuenha', '#bantanha',
  '#canho', '#chungcu', '#vinhomes', '#masteri', '#batdongsanhanoi',
  '#batdongsansaigon', '#dautubds', '#nhapho', '#datchoviet', '#khodoithi',
  '#lienke', '#thuenhahanoi', '#chothue', '#kinhsbds', '#reviewcanho',
  '#muabannhadat', '#batdongsanviet', '#investproperty', '#realestatevietnam',
  -- 43 additions
  '#canhotpk', '#canhocaocap', '#biethu', '#biethulienke', '#nhamattpho',
  '#nhaphocentrumviet', '#duan', '#duanbds', '#bdshanoi', '#bdssaigon',
  '#bdsthucdduc', '#bdsbinhduong', '#bdsbinhthanh', '#nhadatdep', '#nhadatgiare',
  '#tongquanbds', '#review_nhapho', '#review_canho', '#vinhomesgrandpark', '#vinhomesriverside',
  '#vinhomesoceanpark', '#ecopark', '#sungroup', '#kdcfuture', '#novaland',
  '#sunhoang', '#khaihoang', '#nhadatsaigon', '#nhadathanoi', '#cantho',
  '#longan', '#bacgiang', '#canthodoivien', '#bdscantho', '#nhamotre',
  '#nhaphotthi', '#landinvestment', '#property', '#propertyinvestment', '#homeownership',
  '#muadatmucchau', '#phanlo', '#hominhomoi'
]
WHERE id = 10;

-- ── Nấu ăn / Công thức (id=18) ──────────────────────────────────────
-- 25 → 68 (+43 additions)
UPDATE public.niche_taxonomy
SET signal_hashtags = ARRAY[
  -- existing 25 preserved
  '#nauan', '#nauanngon', '#congthucnauan', '#nauanmoiday', '#buacomgiadinh',
  '#monngonmoingay', '#daubepper', '#nauanhanoi', '#nauansaigon', '#recipevietnam',
  '#cookingtutorial', '#nauanfacebook', '#congthucmoingay', '#amthucviet', '#nauancungcon',
  '#monchay', '#nauanchay', '#anlanh', '#chefvietnam', '#homecooking',
  '#mealprep', '#benhnaunan', '#nauankhoe', '#combinh', '#nauantaigia',
  -- 43 additions
  '#amthucvietnam', '#foodreview', '#monngon', '#monngondagia', '#monngonhangngay',
  '#monnhanhdongian', '#moncanh', '#moncuon', '#monkho', '#monchien',
  '#monxao', '#monbun', '#monpho', '#monmien', '#monmy',
  '#banhmi', '#banhxeo', '#che', '#chenong', '#chegiolanh',
  '#trangmieng', '#dokho', '#dongan', '#caytrai', '#buacomme',
  '#buatoi', '#buasang', '#buatrua', '#monanbaby', '#anansangkhong',
  '#cachamcon', '#foodie', '#foodievn', '#vietnameserecipe', '#asiancooking',
  '#vietnamesecooking', '#nauanonline', '#chiase_congthuc', '#congthucdonhan', '#nauanbackoc',
  '#nauancongso', '#mealprep_viet', '#batonbubao'
]
WHERE id = 18;

-- Verification query (run manually after apply):
-- SELECT name_vn, array_length(signal_hashtags, 1) FROM public.niche_taxonomy
--   WHERE id IN (6, 10, 15, 18) ORDER BY id;
-- Expect: Chị đẹp 68, Bất động sản 67, Tài chính 68, Nấu ăn 68.
