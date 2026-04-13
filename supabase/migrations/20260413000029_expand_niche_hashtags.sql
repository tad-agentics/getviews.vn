-- Expand niche_taxonomy.signal_hashtags from 3-4 entries to 20-30 per niche.
--
-- Goal: higher classification coverage for corpus_ingest.py's _detect_content_format()
-- and corpus_context.py's _resolve_niche_id().
--
-- Methodology per niche:
--   - Vietnamese primary tags (most common creator usage)
--   - English loanwords/variants used by VN creators
--   - Sub-niche tags (specific enough to reliably signal the parent niche)
--   - Brand-adjacent tags (brands heavily associated with one niche)
--   - Format-adjacent tags only when niche-specific (e.g. #reviewdo → review niche)
--
-- NOT included: tags in GENERIC_HASHTAGS (fyp, viral, trending, etc.)
-- NOT included: tags that would fire across >3 unrelated niches (e.g. #shopee alone)
--
-- Batch fetch cap: corpus_ingest.py uses only the first BATCH_HASHTAG_FETCH_LIMIT
-- hashtags for EnsembleData calls. All tags here are used for _resolve_niche_id()
-- matching (Postgres array contains, no API cost).

-- 1. Review đồ Shopee / Gia dụng
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#reviewdogiadung', '#dogiadung', '#reviewshopee', '#nhacua',
  '#unboxingshopee', '#muahangshopee', '#shopeehaul', '#haul',
  '#reviewdo', '#donoibat', '#noithat', '#trangtri',
  '#beptop', '#dobeprep', '#tidyup', '#organise',
  '#haulopee', '#reviewdochoian', '#maysay', '#noicook',
  '#reviewdoquan', '#shopeeaffiliate', '#muasamthongminh'
] WHERE id = 1;

-- 2. Làm đẹp / Skincare
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#lamdep', '#skincare', '#chamsocda', '#reviewmypham',
  '#duongda', '#kemduong', '#serum', '#chongnang',
  '#skincareroutine', '#skincarevietnam', '#reviewskincare',
  '#chamsocdamat', '#tretinoin', '#retinol', '#hyaluronicacid',
  '#innisfree', '#laneige', '#somebymikorea', '#cocoonvietnam',
  '#anessa', '#beautyreview', '#glowup', '#makeuptips',
  '#trangdiem', '#phunong', '#lipstick', '#foundation',
  '#dayduong', '#matna', '#tonerpad'
] WHERE id = 2;

-- 3. Thời trang / Outfit
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#thoitrang', '#ootd', '#outfit', '#mixdo',
  '#outfitideas', '#outfitinspo', '#outfitoftheday', '#fashiontiktok',
  '#thoitrangnu', '#thoitrangnam', '#thoitrangvietnam',
  '#phoidohanngay', '#phoidep', '#style', '#streetstyle',
  '#fashionvietnam', '#lookbook', '#phukien', '#giay',
  '#tui', '#vay', '#ao', '#quan',
  '#beachoutfit', '#summerfashion', '#workoutfit',
  '#thoitrangcongso', '#phoidocongso', '#shopfashion',
  '#reviewquanao', '#fashionhaul'
] WHERE id = 3;

-- 4. Review đồ ăn / F&B
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#reviewdoan', '#angi', '#foodtiktok', '#ancungtiktok',
  '#reviewanngon', '#foodreview', '#anngon', '#doananh',
  '#quananngon', '#reviewquan', '#nhahang', '#cafehanoi',
  '#cafesaigon', '#cafedep', '#cafevietnam', '#travelfood',
  '#streetfood', '#monngon', '#nau an', '#nauan',
  '#doanngon', '#comtam', '#pho', '#banhmi',
  '#reviewcafe', '#reviewrestaurant', '#foodie', '#yummy',
  '#banhngot', '#trachen', '#smoothie'
] WHERE id = 4;

-- 5. Kiếm tiền online / MMO
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#kiemtienonline', '#mmo', '#affiliate', '#thunhapthudong',
  '#kiemtien', '#makemoneyonline', '#passiveincome', '#affiliate marketing',
  '#dropshipping', '#freelance', '#khoidonghieptre', '#startup',
  '#banhangonline', '#kinhdonhonline', '#facebook ads', '#googleads',
  '#tiktokshop', '#tiktokaffiliate', '#contentcreator', '#koc',
  '#influencer', '#tiepthilienket', '#review san pham', '#hockinhdoanh',
  '#kiemtientiktok', '#banhangmxh'
] WHERE id = 5;

-- 6. Chị đẹp (Aspirational feminine lifestyle)
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#chidep', '#songdep', '#dailylife', '#morningroutine',
  '#girlboss', '#selfcare', '#selflove', '#hotgirl',
  '#grwm', '#gettingreadywithme', '#dayinmylife',
  '#routinesangcua', '#eveningroutine', '#lifestylevietnam',
  '#congviec', '#thanhcong', '#phunut', '#covai',
  '#livingalone', '#studywithme', '#productivitytips',
  '#mindset', '#tuvuytinh', '#relationship', '#congchua',
  '#girly', '#aesthetic', '#roomtour', '#apartmenttour'
] WHERE id = 6;

-- 7. Mẹ bỉm sữa / Parenting
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#mebimsua', '#baby', '#nuoiday', '#mevaebe',
  '#treem', '#tresosinh', '#nuoicon', '#daycon',
  '#mang thai', '#mangthai', '#lamme', '#congthuc an dam',
  '#andamcho be', '#treemhoc', '#thieunhi', '#hoathinh',
  '#treem hoctot', '#parentingtips', '#newborn', '#newmom',
  '#meviet', '#suabim', '#babygear', '#reviewdobe',
  '#dotreemshopee', '#dothoichoi', '#truonghoc'
] WHERE id = 7;

-- 8. Gym / Fitness VN
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#gymvietnam', '#tapgym', '#fitness', '#giamcan',
  '#workout', '#gymlife', '#bodybuilding', '#tancore',
  '#giammo', '#6 mui', '#sixpack', '#tang co',
  '#dinh duong', '#protein', '#whey', '#supplementvietnam',
  '#chedo an', '#tapthe duc', '#yoga', '#running',
  '#chaybovietnam', '#thethinh', '#fitnessvietnam',
  '#gymmotivation', '#homeworkout', '#personaltrainer',
  '#weightloss', '#bulking', '#cutting', '#reviewgym'
] WHERE id = 8;

-- 9. Công nghệ / Tech
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#congnghe', '#reviewdienthoai', '#tech', '#laptop',
  '#smartphone', '#iphone', '#android', '#samsung',
  '#macbook', '#reviewlaptop', '#techvietnam', '#techreview',
  '#gadget', '#ai', '#chatgpt', '#tinhoc',
  '#coding', '#laptrinhvien', '#developer', '#it',
  '#reviewtai nghe', '#tayamhoa', '#tivi', '#reviewtech',
  '#unboxing', '#setupgoc hoc', '#battlestation',
  '#gamingsetup', '#pcbuild'
] WHERE id = 9;

-- 10. Bất động sản
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#batdongsan', '#nhadat', '#muanha', '#thuenha',
  '#bantanha', '#canho', '#chungcu', '#vinhomes',
  '#masteri', '#batdongsanhanoi', '#batdongsansaigon',
  '#invertmentproperty', '#dautubds', '#nhapho',
  '#datchoviet', '#homedesign', '#noithathienroi', '#thietkenha',
  '#thuenhahanoi', '#chothue', '#kinhsbds', '#reviewcanho',
  '#mua ban nha dat', '#khu do thi', '#lien ke'
] WHERE id = 10;

-- 11. EduTok VN
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#edutokvn', '#hoctienganh', '#giaoduc', '#kienthuc',
  '#hoctot', '#tienganhonline', '#tienganh', '#ielts',
  '#toeic', '#hoctienghan', '#tienghan', '#tiengtrung',
  '#hoctiengtrung', '#kynang', '#kynangsong', '#kynanggiaotiep',
  '#lichsu', '#khoadan', '#tamly', '#sachdoc',
  '#booktokvn', '#bookreview', '#hoctokyo', '#onthitoeic',
  '#minhhoa', '#hientuong', '#khoahoc', '#toanhoc'
] WHERE id = 11;

-- 12. Shopee Live / Livestream bán hàng
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#shopeelive', '#livestream', '#banhang', '#liveshopee',
  '#live', '#banhangtructuyen', '#banhangfacebook',
  '#tiktokshoplive', '#tiktokshopping', '#shopeehaul',
  '#flashsale', '#muasam', '#voucher', '#khuyenmai',
  '#giaretaico', '#ban chay', '#banchayshopee',
  '#baocollab', '#pr', '#collab', '#reivewdanghoa',
  '#tinhnangmoi', '#thuong mai dien tu', '#ecommerce',
  '#kocvietnam', '#contentbanhang'
] WHERE id = 12;

-- 13. Hài / Giải trí
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#hai', '#haihuoc', '#comedy', '#cuoivoibui',
  '#sketch', '#sitcom', '#diennguoi', '#roleplay',
  '#phimhai', '#haivietnam', '#haikichban', '#reaction',
  '#reactvideo', '#duet', '#trending comedy', '#meme',
  '#tinhhuong', '#chuyen vui', '#skit', '#parody',
  '#hoidap', '#thuvui', '#cuoi', '#cuoinhet'
] WHERE id = 13;

-- 14. Ô tô / Xe máy
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#oto', '#xemay', '#reviewxe', '#otovietnam',
  '#car', '#motorvietnam', '#xe', '#drivervietnam',
  '#reviewoto', '#xedien', '#evcar', '#vinfast',
  '#honda', '#yamaha', '#suzuki', '#piaggio',
  '#vespa', '#sh', '#airblade', '#exciter',
  '#baodong xe', '#reviewxemay', '#moto', '#supermoto',
  '#xe dap dien', '#phutung xe', '#doixe', '#muaxe'
] WHERE id = 14;

-- 15. Tài chính / Đầu tư
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#taichinh', '#chungkhoan', '#crypto', '#dautu',
  '#tiemkiemtien', '#thitruong chungkhoan', '#cophieu',
  '#bitcoin', '#ethereum', '#blockchain', '#web3',
  '#quydautu', '#tietkiem', '#tietkiemthongminh',
  '#taichinhcanhan', '#hoachdinh taichinh', '#nghihuu',
  '#FIRE', '#richhabits', '#financial freedom',
  '#forex', '#gold', '#vangtaichinh', '#bat dong san dau tu',
  '#kiemtientaichinh', '#taichinhvietnam', '#canh bao dau tu'
] WHERE id = 15;

-- 16. Du lịch / Travel
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#dulich', '#travel', '#khampha', '#reviewkhachsan',
  '#reviewresort', '#dulichvietnam', '#vietnam travel',
  '#dulichdaly', '#sapa', '#danang', '#hoian', '#hanoitravel',
  '#saigonaphotour', '#phuquoc', '#dalat', '#ninhbinh',
  '#review hotel', '#airbnb', '#hostel', '#backpacker',
  '#dulich nuoc ngoai', '#dulichthailand', '#dulichnhat',
  '#dulichhan', '#phot tour', '#travelblogger',
  '#dulichgia dinh', '#reviewmayBay', '#travelguide'
] WHERE id = 16;

-- 17. Gaming
UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#game', '#lienquan', '#freefire', '#gamevietnam',
  '#lienminh', '#pubg', '#valorant', '#callofduty',
  '#minecraft', '#roblox', '#genshin', '#honkai',
  '#mobilegame', '#pcgame', '#consolegame', '#ps5',
  '#xbox', '#nintendo', '#switch', '#gaming',
  '#gamingvietnam', '#streamer', '#twitch', '#youtube gaming',
  '#esports', '#tournamentgame', '#rank', '#gameplay',
  '#reviewgame', '#gameguide'
] WHERE id = 17;
