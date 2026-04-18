// ============================================================
// Mock data — feels like a real TikTok intelligence product
// ============================================================

const NICHES = [
  { id: 'tech', label: 'Công Nghệ / Tech', emoji: null, count: 661, hot: 12 },
  { id: 'beauty', label: 'Làm Đẹp', emoji: null, count: 1240, hot: 28 },
  { id: 'food', label: 'Ẩm Thực', emoji: null, count: 980, hot: 19 },
  { id: 'fashion', label: 'Thời Trang', emoji: null, count: 540, hot: 8 },
  { id: 'fitness', label: 'Thể Hình', emoji: null, count: 312, hot: 5 },
  { id: 'finance', label: 'Tài Chính', emoji: null, count: 188, hot: 3 },
  { id: 'parenting', label: 'Gia Đình', emoji: null, count: 720, hot: 11 },
  { id: 'edu', label: 'Giáo Dục', emoji: null, count: 410, hot: 6 },
];

const QUICK_ACTIONS = [
  { id: 'video',     title: 'Soi Video',         desc: 'Dán link TikTok — phân tích hook, nhịp, CTA',     icon: 'film' },
  { id: 'channel',   title: 'Soi Kênh Đối Thủ',  desc: 'Dán @handle — xem công thức content của họ',       icon: 'eye' },
  { id: 'trends',    title: 'Xu Hướng Tuần Này', desc: 'Hook nào đang chạy trong ngách của bạn',           icon: 'trend' },
  { id: 'script',    title: 'Lên Kịch Bản Quay', desc: 'Từ chủ đề → shotlist sẵn sàng quay',               icon: 'script' },
  { id: 'kol',       title: 'Tìm KOL / Creator', desc: 'Gợi ý tài khoản đáng theo dõi hoặc hợp tác',       icon: 'users' },
  { id: 'consult',   title: 'Tư Vấn Content',    desc: 'Hướng nội dung + format phù hợp ngách',            icon: 'sparkle' },
];

const SUGGESTED_PROMPTS = [
  'Xu hướng đang hot trong Công nghệ / Tech tuần này?',
  'Hook nào đang hiệu quả nhất trong Công nghệ?',
  'Phân tích kênh @sammie.tech — họ đang làm gì hay?',
  'Format nào đang tăng view nhanh nhất ngách Beauty?',
];

const RECENT_CHATS = [
  { id: 1, title: 'Hướng nội dung TikTok cho ngách Tech',  when: 'Hôm nay' },
  { id: 2, title: 'Hook 3s cho video review tai nghe',     when: 'Hôm qua' },
  { id: 3, title: 'So sánh @minhtuan vs @khoavu',           when: '2 ngày trước' },
  { id: 4, title: 'Lên 5 ý tưởng video về AI tools',       when: 'Tuần trước' },
  { id: 5, title: 'Format storytelling cho ngách Edu',     when: 'Tuần trước' },
];

// Video grid mock — diverse aspect-friendly entries
const VIDEOS = [
  { id:'v1', title:'Khi bạn mô tả trường học của bạn', creator:'@chinasecrets', views:'34.5K', date:'18/04', niche:'Edu',     hook:'Khi bạn ___', dur:'0:18', breakout:true,  bg:'#3D2F4A' },
  { id:'v2', title:'Kiếm được quà hình nền máy tính',   creator:'@gigi.gaming',  views:'524K',  date:'18/04', niche:'Gaming',  hook:'Kiếm được quà ___', dur:'0:42', breakout:true, bg:'#7C2A4A' },
  { id:'v3', title:'112.3K views — em bé phản ứng',     creator:'@babyreacts',   views:'112K',  date:'18/04', niche:'Family',  hook:'Reaction style', dur:'0:23', bg:'#2A4A5C' },
  { id:'v4', title:'Mukbang thịt heo cay',              creator:'@anuong',       views:'159K',  date:'18/04', niche:'Food',    hook:'POV mukbang', dur:'0:55', viral:true, bg:'#2A5C4A' },
  { id:'v5', title:'Lướt thấy video một ông nội say xỉn', creator:'@vietviral',  views:'92K',   date:'17/04', niche:'Funny',   hook:'Lướt thấy ___', dur:'0:31', bg:'#C2325C' },
  { id:'v6', title:'9 chữ và cái khoảnh khắc tình bạn',  creator:'@hongphuc',    views:'40K',   date:'17/04', niche:'Lifestyle', hook:'9 chữ ___', dur:'0:48', bg:'#3A4A5C' },
  { id:'v7', title:'Đây là cái thế giới của em bạn giới thiệu', creator:'@phuongmy', views:'175K', date:'17/04', niche:'Drama', hook:'Đây là ___', dur:'1:02', viral:true, bg:'#8C2A4A' },
  { id:'v8', title:'Đây là con cá gì tao đời tôi mới ăn được',  creator:'@cauca',     views:'44K',   date:'17/04', niche:'Food',    hook:'Đây là con ___', dur:'0:27', bg:'#3A5A6B' },
  { id:'v9', title:'Review tai nghe 200k vs 2 triệu',   creator:'@tech.minh',    views:'87K',   date:'16/04', niche:'Tech',    hook:'200k vs 2 triệu', dur:'1:12', bg:'#2A3A4A' },
  { id:'v10', title:'Setup bàn làm việc <5 triệu',      creator:'@deskvn',       views:'128K',  date:'16/04', niche:'Tech',    hook:'<5 triệu', dur:'0:50', bg:'#3D2F4A' },
  { id:'v11', title:'5 app AI miễn phí mà chưa ai nói', creator:'@aifreelance',  views:'234K',  date:'16/04', niche:'Tech',    hook:'5 thứ chưa ai nói', dur:'0:58', breakout:true, bg:'#1F3A5C' },
  { id:'v12', title:'Test pin iPhone 17 sau 6 tháng',   creator:'@phongvu.tech', views:'71K',   date:'15/04', niche:'Tech',    hook:'Sau 6 tháng', dur:'1:30', bg:'#4A2A3D' },
];

// Hook patterns trending
const HOOKS = [
  { pattern: 'Khi bạn ___',         delta: '+248%', uses: 1240, avg: '128K', sample: 'Khi bạn lần đầu thử...' },
  { pattern: 'Lướt thấy ___',       delta: '+182%', uses: 890,  avg: '92K',  sample: 'Lướt thấy video này mà...' },
  { pattern: '5 thứ chưa ai nói',   delta: '+156%', uses: 412,  avg: '76K',  sample: '5 app AI mà chưa ai nói tới' },
  { pattern: 'POV: ___',            delta: '+98%',  uses: 2100, avg: '54K',  sample: 'POV: Bạn là sales TikTok' },
  { pattern: '___ vs ___',          delta: '+74%',  uses: 680,  avg: '88K',  sample: '200k vs 2 triệu — chọn cái nào?' },
  { pattern: 'Đây là ___',          delta: '+42%',  uses: 1870, avg: '47K',  sample: 'Đây là con cá tôi chưa từng thấy' },
];

// Creators / KOL mock
const CREATORS = [
  { handle:'@sammie.tech',   name:'Sammie Trần',     niche:'Tech',    followers:'412K', avg:'89K',  growth:'+12%', match:94, tone:'Giải thích — chậm, rõ' },
  { handle:'@minhtuan.dev',  name:'Tuấn Minh',       niche:'Tech',    followers:'278K', avg:'124K', growth:'+34%', match:88, tone:'Chiến tà — thẳng thừng' },
  { handle:'@khoavu',        name:'Khoa Vũ',         niche:'Tech',    followers:'1.2M', avg:'310K', growth:'+8%',  match:81, tone:'Hài hước — meme heavy' },
  { handle:'@gigi.gaming',   name:'Gigi Nguyễn',     niche:'Gaming',  followers:'890K', avg:'410K', growth:'+22%', match:62, tone:'Năng lượng cao' },
  { handle:'@phongvu.tech',  name:'Phong Vũ Tech',   niche:'Tech',    followers:'654K', avg:'92K',  growth:'+5%',  match:79, tone:'Review nghiêm túc' },
  { handle:'@aifreelance',   name:'Mai AI',          niche:'Tech',    followers:'198K', avg:'156K', growth:'+89%', match:91, tone:'Hướng dẫn nhanh' },
];

// Channel deep dive
const CHANNEL_DETAIL = {
  handle: '@sammie.tech',
  name: 'Sammie Trần',
  bio: 'Tech đơn giản. Mỗi sáng một video.',
  followers: '412K',
  totalVideos: 248,
  avgViews: '89K',
  engagement: '6.4%',
  postingCadence: 'Hàng ngày · 7:30 sáng',
  topHook: 'Khi bạn ___',
  formula: [
    { step: 'Hook', detail: '0–3s: câu hỏi POV', pct: 22 },
    { step: 'Setup', detail: '3–8s: vấn đề cụ thể', pct: 18 },
    { step: 'Body', detail: '8–35s: 3 ý chính, b-roll dày', pct: 45 },
    { step: 'Payoff', detail: '35–45s: tóm tắt + CTA', pct: 15 },
  ],
};

Object.assign(window, {
  NICHES, QUICK_ACTIONS, SUGGESTED_PROMPTS, RECENT_CHATS,
  VIDEOS, HOOKS, CREATORS, CHANNEL_DETAIL,
});
