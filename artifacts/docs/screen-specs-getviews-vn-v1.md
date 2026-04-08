# Screen Specs — GetViews.vn v1

**App:** GetViews.vn — Vietnamese TikTok creative intelligence chat tool  
**Date:** 2026-04-08  
**Deployment:** PWA (React Router v7 + Vite + Vercel)  
**Primary viewport:** 360–393px mobile. Desktop-capable for Linh.  
**Font:** TikTok Sans (primary), JetBrains Mono (data/numbers)  
**Auth:** Facebook OAuth (primary) + Google OAuth (secondary)  
**Payment:** PayOS — MoMo, VNPay, bank transfer, Visa/Mastercard

---

## Scope Plan

### Build Scope — 10 screens total

**Why 10:** GetViews is a chat-first AI tool. All 7 analytical intents render inline in a single ChatScreen — no separate result detail screens. The northstar §17 explicitly targets "8 screens" for Wave 1 MVP. Screens 9–10 (checkout + success) complete the monetization flow. This is the correct scope for a chat-first SaaS, not an under-scoped B2C app.

#### Core Loop (3 screens)


| #   | Screen        | Primary Action                                                     | Notes                                                                  |
| --- | ------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| 1   | ChatScreen    | Paste TikTok URL or ask question → streaming AI analysis           | All 7 intents, credit bar, URL detection, all dopamine moments (D1–D4) |
| 2   | TrendScreen   | Browse pre-computed niche trends (hook rankings, format lifecycle) | ⑥ intent pre-computed, free, D2 dopamine                               |
| 3   | HistoryScreen | Browse + resume past chat sessions                                 | Tap → resumes in ChatScreen                                            |


#### Retention (overlaps with Core Loop)

TrendScreen and HistoryScreen serve dual purpose. Dedicated retention mechanic: Monday weekly trend brief (email, Wave 2 feature — no screen needed).

#### Monetization (3 screens)


| #   | Screen               | Revenue Mechanic                              | Notes                                           |
| --- | -------------------- | --------------------------------------------- | ----------------------------------------------- |
| 4   | PricingScreen        | Select subscription plan or overage pack      | Triggered by low/zero credits or tap "Nâng cấp" |
| 5   | CheckoutScreen       | PayOS payment initiation                      | MoMo QR / VNPay QR / bank details / card form   |
| 6   | PaymentSuccessScreen | Confirm purchase, show updated credit balance | Returns to ChatScreen                           |


#### Infrastructure (4 screens)


| #   | Screen           | Purpose                                                          | Notes                                         |
| --- | ---------------- | ---------------------------------------------------------------- | --------------------------------------------- |
| 7   | LandingPage      | Conversion page at `/` — marketing + live demo                   | Pre-rendered, SEO, free Soi Kênh without auth |
| 8   | LoginScreen      | Facebook OAuth (primary) + Google OAuth (secondary)              | No email/password form                        |
| 9   | OnboardingScreen | Niche selection (step 2) + optional TikTok profile link (step 3) | Chat opens after step 2                       |
| 10  | SettingsScreen   | Profile, subscription info, niche change, credit history, logout |                                               |


**Total: 10 screens** (3 core loop + 3 monetization + 4 infrastructure)  
**Core loop ratio:** 3/(3+3) = 50% of product screens ✓ (at minimum threshold — appropriate for chat-first SaaS)  
**Completeness check:** All user scenarios from §16 walkable ✓

**Core loop summary:** User opens chat → pastes TikTok URL or asks text question → GetViews streams analysis backed by 46K+ Vietnamese video corpus → user acts on specific recommendations → explores trends in second tab → buys more credits when needed.

---

### Not Building

- English-language support — Vietnamese-only product
- MCP server access — developer market too small for v1
- Multi-platform (Reels, Shorts) — TikTok-only
- Creator marketplace / talent management (contracts, payments, ongoing relationships) — not GetViews scope
- Video editing tools — GetViews diagnoses, not edits
- Scheduling / posting — different category
- Shopee analytics / affiliate dashboard — Kalodata territory
- Notification management screen — email-based renewal reminders (no in-app preferences needed)
- Admin dashboard — use Supabase Dashboard
- Competitor tracking dashboard screen — managed as chat sessions in Wave 2

---

## Screen Metadata

---

## LandingPage

**Route:** `/`

**Components:**

- `HeroSection` — headline + subheadline + trust line + live input field + CTA button + microcopy
- `StickyBar` — appears after scrolling past hero; icon + CTA + risk reducer
- `PainPointCard` — 3× named enemy cards (title + copy)
- `SolutionCard` — 3× mirror cards
- `LiveDemoSection` — 5 prompt chips, embedded chat preview (static mockup)
- `SocialProofSection` — pre-launch: before/after video result stat
- `PricingCard` — 3× tier cards, billing toggle (Monthly | 6 months | Annual)
- `FAQAccordion` — 6 items, accordion behavior
- `FinalCTASection` — repeat hero CTA, dark bg

**Data:**


| Variable                     | Source | Default if null |
| ---------------------------- | ------ | --------------- |
| — (all static, pre-rendered) | —      | —               |


**States:**

- Loading: none (pre-rendered HTML, instant)
- Error: none (static page)
- Empty: none

**Interaction flow:**

1. Page loads → Hero section visible above fold. Input field shows placeholder "Dán link TikTok để bắt đầu". CTA button visible below.
2. User scrolls past hero → StickyBar slides in from bottom (translateY animation, 200ms).
3. User taps CTA "Soi Video Miễn Phí" → IF not logged in → LoginScreen. IF logged in → `/app` (ChatScreen).
4. User pastes TikTok URL into hero live input → URL chip appears above input (same UX as ChatScreen). "Soi Kênh" button activates.
5. User taps "Soi Kênh" → IF not logged in → one free anonymous Soi Kênh runs (no auth) → result appears inline below hero → login prompt overlaid below result.
6. Scroll down → PainPointCards appear (no stagger — landing page is calm). Continue scrolling → SolutionCards → LiveDemoSection → SocialProof → PricingCards → FAQAccordion → FinalCTASection.
7. FAQ item tapped → accordion expands (Normal 200ms). Tap again → collapses.
8. Billing toggle tapped → prices update instantly (Instant 0ms). Annual is pre-selected.
9. Tap "Bắt đầu" on pricing card → LoginScreen (free tier: no payment). Tap paid tier → LoginScreen → OnboardingScreen → PricingScreen with that tier pre-selected.

**Navigation:**

- Enters from: Direct URL, shared link, search result
- Exits to: LoginScreen via CTA taps; ChatScreen if already logged in
- Back: Browser back (no in-app back)

**Dopamine moment:** none — landing page is calm/professional, measured, not celebratory

**Copy slots (production-ready):**

- hero_headline: "Bạn lướt TikTok cả ngày để tìm ý tưởng. GetViews làm việc đó thay bạn." — Ambient
- hero_sub: "Dán link video của bạn vào. 1 phút sau biết ngay lỗi ở đâu, nên fix gì, và hook nào đang chạy trong niche của bạn." — Ambient
- hero_trust: "Không guru. Không screenshot. Data thực từ video thực." — Ambient
- hero_cta: "Soi Video Miễn Phí" — Ambient
- hero_microcopy: "10 lần phân tích sâu miễn phí · Lướt xu hướng không giới hạn · Không cần thẻ" — Ambient
- input_placeholder: "Dán link TikTok để bắt đầu" — Ambient
- sticky_cta: "Soi Video Miễn Phí" — Ambient
- sticky_risk: "Không cần thẻ" — Ambient
- pain_1_title: "Lướt TikTok Cả Ngày" — Ambient
- pain_1_body: "Sáng mở TikTok 'nghiên cứu' — 2 tiếng sau vẫn đang lướt. Screenshot mấy video hay, quăng vô Google Sheet rồi quên luôn. Hôm sau lại lướt lại từ đầu. Quen không?" — Ambient
- pain_2_title: "Học Rồi Vẫn Không Biết Quay Gì" — Ambient
- pain_2_body: "Mua khóa học 3-5 triệu xong cũng nắm được lý thuyết. Nhưng mở app lên vẫn không biết hôm nay nên quay cái gì. Algorithm thay đổi liên tục — kiến thức tháng trước tháng này đã khác." — Ambient
- pain_3_title: "Video Flop Mà Không Biết Tại Sao" — Ambient
- pain_3_body: "Quay xong đăng lên, ngồi chờ. 500 view. Không biết lỗi ở hook, ở nhịp, hay ở format. Video đối thủ triệu view — cũng không biết họ làm gì khác mình." — Ambient
- sol_1_title: "Xem Video Thật, Nói Cho Bạn Thật" — Ambient
- sol_1_body: "GetViews không đoán. Nó xem thật video của bạn — mặt xuất hiện giây nào, text overlay ở đâu, nhịp cắt cảnh ra sao — rồi so với video đang chạy tốt nhất trong niche của bạn. Mọi gợi ý đều kèm video thật có view thật, bạn bấm vào xem được luôn." — Ambient
- sol_2_title: "Hôm Nay Hỏi, Hôm Nay Có" — Ambient
- sol_2_body: "Khóa học dạy bạn tháng 1, tháng 4 đã cũ. GetViews biết hook nào đang chạy tuần này, trong đúng niche của bạn. Hỏi lúc nào cũng được, data luôn mới." — Ambient
- sol_3_title: "Làm Cho Creator Việt Nam" — Ambient
- sol_3_body: "Đây không phải tool Tây dịch ra tiếng Việt. GetViews hiểu review đồ gia dụng, làm đẹp, Shopee affiliate, hài phương ngữ — 17 niche của creator Việt. Hỏi bằng tiếng Việt, trả lời bằng tiếng Việt, data từ TikTok Việt Nam." — Ambient
- social_proof_pre_launch: "Video gốc: 2.000 views. GetViews phát hiện hook chậm 2.1 giây, không có mặt người. Quay lại theo gợi ý: 45.000 views." — Ambient
- pricing_popular_label: "Phổ biến nhất" — Ambient
- pricing_annual_callout: "Tiết kiệm 600.000đ khi mua cả năm" — Ambient
- pricing_sixmo_callout: "Tặng 1 tháng miễn phí khi mua 6 tháng" — Ambient
- pricing_methods: "Thanh toán qua MoMo, VNPay, chuyển khoản, hoặc thẻ quốc tế." — Ambient
- faq_1_q: "Khác gì ChatGPT?" — Ambient
- faq_1_a: "ChatGPT không có data TikTok và không xem được video. Bạn hỏi 'hook nào đang hot trong skincare' — ChatGPT bịa ra câu trả lời nghe hợp lý nhưng không dựa trên video nào cả. GetViews trả lời dựa trên video thật, view thật, bạn bấm vào xem kiểm chứng được." — Ambient
- faq_2_q: "Tôi mua khóa học rồi, cần thêm cái này không?" — Ambient
- faq_2_a: "Khóa học dạy bạn nền tảng — algorithm, cách quay, cách edit. Tốt. Nhưng nó không nói cho bạn biết tuần này hook nào đang chạy trong đúng niche của bạn. GetViews bổ sung chỗ khóa học không cover được: data thực, cập nhật mỗi ngày, cho đúng niche." — Ambient
- faq_3_q: "Khác gì Kalodata?" — Ambient
- faq_3_a: "Kalodata chỉ cho bạn biết sản phẩm nào bán chạy. GetViews chỉ cho bạn biết TẠI SAO cái video bán được chạy — hook kiểu gì, mở đầu ra sao, nhịp cắt thế nào. Hai cái khác nhau, dùng song song được." — Ambient
- faq_4_q: "1 credit là gì?" — Ambient
- faq_4_a: "Phân tích sâu (soi video, phân tích đối thủ, viết brief) = 1 credit. Lướt xu hướng, tìm KOL, và hỏi thêm trong cùng phiên — miễn phí, không giới hạn." — Ambient
- faq_5_q: "Thanh toán sao?" — Ambient
- faq_5_a: "MoMo, VNPay, chuyển khoản, hoặc thẻ Visa/Mastercard. Mua xong dùng được ngay." — Ambient
- faq_6_q: "Lỡ không hiệu quả thì sao?" — Ambient
- faq_6_a: "Không hợp đồng, hủy lúc nào cũng được. Mua gói tháng thử trước, thấy ổn thì chuyển gói dài hơn." — Ambient
- final_cta_headline: "Thử dán 1 link video vào. Miễn phí. Xem GetViews nói gì." — Ambient
- final_cta_button: "Soi Video Ngay" — Ambient

**Edge cases:**

- User already logged in and visits `/` → CTA navigates directly to `/app` (skip login)
- User completes free Soi Kênh (anonymous) → login prompt appears below result with: "Kết quả của bạn đã sẵn sàng — đăng ký miễn phí để lưu và tiếp tục phân tích."
- No internet → static pre-rendered HTML still loads; live input gives error "Không kết nối được — kiểm tra mạng và thử lại."
- iOS: install prompt not available → hero microcopy changes to "Truy cập ngay trong trình duyệt"

**Credit cost:** N/A

---

## LoginScreen

**Route:** `/login`

**Components:**

- `GetViewsLogo` — wordmark + TikTok red mark
- `TrustLine` — single-line value statement below logo
- `OAuthButton` — Facebook variant (primary, `--ink` bg, white text, Facebook icon)
- `OAuthButton` — Google variant (secondary, `--surface` bg, `--ink` text, 1px border, Google icon)
- `LegalNote` — terms + privacy link

**Data:**


| Variable                        | Source | Default if null |
| ------------------------------- | ------ | --------------- |
| — (static, no user data needed) | —      | —               |


**States:**

- Loading: OAuth button shows 16px spinner replacing icon, text changes to "Đang kết nối...", button disabled
- Error: Error text below button "Đăng nhập không thành công — thử lại." in `--danger` color, button re-enables
- Empty: n/a (static form)

**Interaction flow:**

1. Screen loads → GetViews logo centered, Facebook button primary (black fill), Google button below (outlined).
2. User taps "Đăng nhập với Facebook" → Facebook OAuth popup/redirect. Button spinner activates.
3. IF OAuth success + new user → OnboardingScreen.
4. IF OAuth success + returning user → ChatScreen (app home).
5. IF OAuth fails or user cancels → error text appears below the tapped button. Button re-enables.
6. User taps "Đăng nhập với Google" → same flow via Google OAuth.

**Navigation:**

- Enters from: LandingPage via CTA, ChatScreen auth guard redirect, OnboardingScreen back (if user cancels)
- Exits to: `/auth/callback` (OAuth provider redirects here) → OnboardingScreen (new user) or ChatScreen (returning user)
- Back: Browser back → LandingPage

**Auth callback note:** The route `/auth/callback` is a non-UI handler that exchanges the OAuth code for a Supabase session, then redirects. It is not designed in Figma Make — it is already implemented in `src/routes/_auth/callback/route.tsx`.

**Dopamine moment:** none

**Copy slots (production-ready):**

- trust_line: "Data thực từ 46.000+ video TikTok Việt Nam — phân tích video của bạn trong 1 phút." — Ambient
- btn_facebook: "Đăng nhập với Facebook" — Ambient
- btn_google: "Đăng nhập với Google" — Ambient
- loading_facebook: "Đang kết nối Facebook..." — Loading
- loading_google: "Đang kết nối Google..." — Loading
- error_oauth: "Đăng nhập không thành công — thử lại." — Error
- legal_note: "Bằng cách đăng nhập, bạn đồng ý với Điều khoản dịch vụ và Chính sách bảo mật của GetViews." — Ambient

**Edge cases:**

- Facebook OAuth blocked by corporate browser → show "Thử đăng nhập bằng Google hoặc mở trong Safari/Chrome."
- User returns to login after already being logged in (e.g., navigates back) → auto-redirect to ChatScreen

**Credit cost:** N/A

---

## OnboardingScreen

**Route:** `/onboarding`

**Components:**

- `StepIndicator` — pill that reads "Bước 2/3" on step 2 (niche input) and updates to "Bước 3/3" on step 3 (TikTok profile). Step 1 = the OAuth login screen. The pill advances inline without navigation.
- `NicheInput` — single text input with Vietnamese smart autocomplete suggestions
- `NicheChip` — suggestion chips below input: "Review đồ gia dụng", "Làm đẹp / Skincare", "Shopee affiliate", "Review đồ ăn", "Hài phương ngữ"
- `SkipLink` — text link "Bỏ qua" for step 3 (TikTok profile)
- `TikTokProfileInput` — text/URL input for step 3 (optional)
- `PrimaryButton` — "Bắt đầu phân tích" CTA

**Data:**


| Variable               | Source              | Default if null                        |
| ---------------------- | ------------------- | -------------------------------------- |
| profiles.display_name  | Supabase Auth OAuth | "Bạn"                                  |
| profiles.primary_niche | profiles table      | null (required — must complete step 2) |
| profiles.tiktok_handle | profiles table      | null (optional)                        |


**States:**

- Loading: Button shows spinner "Đang thiết lập..." while profile saves
- Error: "Không lưu được — thử lại." below button in `--danger`
- Empty: Input placeholder text visible, button disabled until niche is entered

**Interaction flow:**

1. Screen loads → Greeting: "{{profiles.display_name}}, bạn tạo nội dung về chủ đề gì?" (heading). NicheInput focused immediately.
2. User types → autocomplete chips appear below input matching Vietnamese niche taxonomy (§7): "Review đồ gia dụng", "Làm đẹp", "Shopee affiliate", "Hài phương ngữ", etc.
3. User taps a chip → chip text populates input. Input clears and moves to step 3 section.
4. Step 3 appears: "Dán link TikTok profile của bạn (tùy chọn)" with SkipLink "Bỏ qua".
5. IF user enters TikTok URL → stored as `profiles.tiktok_handle`. IF user taps "Bỏ qua" → step 3 skipped.
6. User taps "Bắt đầu phân tích" → profiles.primary_niche saves to Supabase → navigate to ChatScreen.
7. ChatScreen first message auto-populated: "Sẵn sàng phân tích content của bạn. Thử dán link TikTok hoặc hỏi gì đang hot trong {{user.primary_niche}}."

**Navigation:**

- Enters from: LoginScreen (new user OAuth success)
- Exits to: ChatScreen via "Bắt đầu phân tích" button
- Back: Disabled (no back from onboarding — user must complete step 2 minimum)

**Dopamine moment:** none — niche selection is neutral, no animation

**Copy slots (production-ready):**

- step_heading: "{{profiles.display_name}}, bạn tạo nội dung về chủ đề gì?" — Ambient
- step_sub: "GetViews sẽ dùng data đúng niche của bạn để cho kết quả chính xác hơn." — Ambient
- niche_placeholder: "Nhập niche — ví dụ: review đồ gia dụng, skincare, hài..." — Ambient
- step3_label: "Dán link TikTok profile của bạn (tùy chọn)" — Ambient
- step3_sub: "Giúp GetViews xác nhận niche từ content thực của bạn." — Ambient
- step3_placeholder: "[https://www.tiktok.com/@handle](https://www.tiktok.com/@handle)" — Ambient
- skip_link: "Bỏ qua" — Ambient
- cta_button: "Bắt đầu phân tích" — Ambient
- loading_save: "Đang thiết lập..." — Loading
- error_save: "Không lưu được — thử lại." — Error
- first_chat_message: "Sẵn sàng phân tích content của bạn. Thử dán link TikTok hoặc hỏi gì đang hot trong {{user.primary_niche}}." — Ambient

**Edge cases:**

- User enters a niche not in the taxonomy → stored as-is; system maps to closest niche in §7 taxonomy on first query
- TikTok URL invalid format → "Link không hợp lệ — dán link profile TikTok (ví dụ: tiktok.com/@handle)." below input. Step 3 can still be skipped.
- Profile save fails (network error) → retry button; niche data preserved in input

**Credit cost:** N/A

---

## ChatScreen

**Route:** `/app`

**Components:**

- `ChatHeader` — GetViews wordmark (left) + NicheBadge (center, current niche) + SettingsIcon (right, tap → SettingsScreen)
- `MessageList` — scrollable chat history; auto-scroll to bottom
- `UserMessageBubble` — right-aligned, `--purple-light` bg, `--ink` text
- `AssistantMessageBlock` — left-aligned, `--surface` bg, full-width, 1px `--border` top/bottom
- `StreamingStatusText` — phase-transitioning loading text (see EDS §5b loading table)
- `DiagnosisRow` — ✕/✓ marker + finding + benchmark. D1 animation: stagger-in from left, 150ms each (D1)
- `HookRankingBar` — animated horizontal bar, purple top, gray others. Multiplier fades in at bar end (D2)
- `BriefBlock` — hook options + shot structure + KOL tier, slide-in sequential (D3)
- `CreatorCard` — @handle + followers + likes + contact + "Có data" badge (D4)
- `ThumbnailStrip` — horizontal scrollable strip of `ThumbnailCard` items (120px each, 9:14 aspect)
- `CorpusCite` — "412 video · 7 ngày · Updated 4h ago" below ranked content
- `CopyButton` — "Copy kết quả" full-width button below structured outputs (mobile)
- `ShareButton` — Web Share API trigger (mobile only, next to CopyButton)
- `FreeQueryPill` — "Miễn phí ✓" pill next to user message for free intents
- `PromptCards` — 2-column grid of 4 suggested questions (empty state only)
- `RefreshPromptsLink` — "Đổi gợi ý" text link below PromptCards
- `URLChip` — above input when TikTok URL detected; purple left border
- `ChatInput` — auto-grow textarea (1→3 lines mobile, 1→5 desktop), 1000 char limit
- `CharCounter` — "{{current}}/1000" JetBrains Mono `--faint` → `--danger` at 900+
- `SendButton` — 44×44px; `--faint` bg when empty, `--purple` bg when has input; spinner on send
- `ScrollDownPill` — "↓ Cuộn xuống" appears when user scrolls up during stream
- `CreditBar` — persistent bottom bar above input area; tap → PricingScreen when zero

**Data:**


| Variable                        | Source              | Default if null                  |
| ------------------------------- | ------------------- | -------------------------------- |
| profiles.display_name           | profiles table      | "Bạn"                            |
| profiles.primary_niche          | profiles table      | "creator" (fallback niche label) |
| profiles.deep_credits_remaining | profiles table      | 0                                |
| sessions[].id                   | chat_sessions table | —                                |
| sessions[].messages             | chat_messages table | []                               |
| sessions[].intent_type          | chat_sessions table | null                             |


**States:**

- Loading (pre-stream): StreamingStatusText shows phased text (intent-specific, see EDS §5b). No skeleton loader.
- Error: Inline error appended to last message. No modal. "Video không tải được — thử dán lại hoặc dùng video khác." with retry tap target.
- Empty (first use): PromptCards grid, greeting heading, input focused.

**Interaction flow:**

*Empty state (first use / new session):*

1. Screen loads → Greeting: "Sẵn sàng phân tích content của bạn." (28px, 2 lines max). NicheBadge shows `profiles.primary_niche`. PromptCards grid visible (2 columns). CreditBar at bottom.
2. User taps a PromptCard → card text populates ChatInput. All cards fade out (opacity 0, 150ms). Input auto-focuses.
3. User types their own message → PromptCards remain until send.

*Message send flow:*
4. User types or pastes text → SendButton activates (`--purple` bg).
5. URL detected in input → URLChip appears above input: "Video TikTok — @{{handle}}" (purple left border). Intent pre-classified as ①/③/④.
6. User taps SendButton → UserMessageBubble appears right-aligned. FreeQueryPill appears IF free intent (⑥⑦ or follow-up). StreamingStatusText appears in AssistantMessageBlock position.
7. IF deep intent (①-⑤): credit check. IF credits ≥ 1 → proceed. IF credits = 0 → inline paywall appears: "Hết deep credit tháng này. Mua thêm 10 credit = 130K VND." + tappable "Mua thêm →" link.
8. IF credits ≥ 1 → StreamingStatusText phases (e.g., for ①: "Đang tải video..." → "Đang xem video của bạn..." → "Đang so sánh với {{count}} video trong niche..."). D5: CreditBar pulses, number decrements, "−1" floats up.
9. Tokens stream in: text appears token-by-token (opacity 0→1, 60ms each).
10. Structured content (DiagnosisRows, HookRankingBars, BriefBlocks, CreatorCards) buffers during stream → appears as complete units with dopamine animations when ready.
11. ThumbnailStrip appears inline after corpus-backed responses. Swipeable horizontal. 2.5 thumbnails visible.
12. CopyButton + ShareButton appear below structured output blocks.
13. Auto-scroll pins to bottom. IF user scrolls up → ScrollDownPill appears. Tap pill → scroll resumes.

*Stream interruption:*
14. User sends new message during stream → current stream truncates ("..."). New query starts immediately.
15. IF stream fails (503/timeout) → append inline: "— Bị gián đoạn. Gõ 'tiếp' để tiếp tục." User types "tiếp" → system replays from last complete sentence.

**Navigation:**

- Enters from: OnboardingScreen (new user), LoginScreen (returning user), HistoryScreen (tap session → resume), PricingScreen/PaymentSuccessScreen (after payment)
- Exits to: TrendScreen (bottom nav tab), HistoryScreen (bottom nav tab), SettingsScreen (header icon tap), PricingScreen (CreditBar tap when zero, or "Mua thêm" inline)
- Back: No back from ChatScreen — it is the home screen

**Dopamine moment:** D1 (DiagnosisReveal), D2 (HookRankingBars), D3 (BriefDelivered), D4 (CreatorCardsFound), D5 (CreditConsumption), D6 (FreeQueryConfirmation) — all inline, triggered by AI response content

**Dopamine moment definitions (D5–D6, extends EDS §5c D1–D4):**

- **D5 — CreditConsumption:** After a deep-credit query, `CreditBar` pulses once (border flashes `--purple` for 200ms), then the credit count decrements by 1 with a "−1" ghost that floats upward and fades (opacity 1→0, translateY 0→-12px, 400ms). Signals value exchange — user got something for their credit.
- **D6 — FreeQueryConfirmation:** `FreeQueryPill` ("Miễn phí ✓") appears inline next to the user's message bubble, fades in (opacity 0→1, 120ms), lingers 2 seconds, then fades out (opacity 1→0, 200ms). No sound, no bounce. Reinforces the free intent without interrupting flow.

**Copy slots (production-ready):**

- empty_greeting: "Sẵn sàng phân tích content của bạn." — Ambient
- empty_niche_sub: "Hỏi gì đang hot trong {{user.primary_niche}} — hoặc dán link TikTok để bắt đầu." — Ambient
- prompt_card_1: "Tại sao video này ít view — lỗi ở đâu?" — Ambient
- prompt_card_2: "Hook nào đang hot trong {{user.primary_niche}} tuần này?" — Ambient
- prompt_card_3: "Soi kênh @đối_thủ — họ đang làm gì?" — Ambient
- prompt_card_4: "Viết brief cho KOL quay video {{user.primary_niche}}" — Ambient
- refresh_prompts: "Đổi gợi ý" — Ambient
- input_placeholder: "Dán link TikTok hoặc hỏi bất cứ thứ gì..." — Ambient
- url_chip_valid: "Video TikTok — @{{handle}}" — Ambient
- url_chip_invalid: "Link không hợp lệ — cần link TikTok" — Error
- char_overflow: "Đã cắt — giới hạn 1.000 ký tự" — Ambient
- scroll_down_pill: "↓ Cuộn xuống" — Ambient
- free_pill: "Miễn phí ✓" — Ambient
- credit_bar_normal: "{{count}} deep credits còn lại · Lướt xu hướng & tìm KOL không giới hạn" — Ambient
- credit_bar_low: "⚠ {{count}} deep credits còn lại" — Ambient
- credit_bar_zero: "Hết credit. Mua thêm →" — Paywall
- paywall_inline: "Hết deep credit tháng này. Mua thêm 10 credit = 130.000 VND." — Paywall
- loading_diagnosis_1: "Đang tải video..." — Loading
- loading_diagnosis_2: "Đang xem video của bạn..." — Loading
- loading_diagnosis_3: "Đang so sánh với {{count}} video trong niche..." — Loading
- loading_brief: "Đang viết brief..." — Loading
- loading_creator: "Đang tìm KOL..." — Loading
- loading_trends: "Đang phân tích {{count}} video..." — Loading
- error_video_fail: "Video không tải được — thử dán lại hoặc dùng video khác." — Error
- error_gemini_fail: "Đang bận — thử lại sau vài giây." — Error
- stream_interrupted: "— Bị gián đoạn. Gõ 'tiếp' để tiếp tục." — Ambient
- copy_success: "Đã copy ✓" — Confirmation
- copy_zalo: "Đã copy — forward qua Zalo cho KOL luôn." — Confirmation
- diagnosis_pass: "✓ {{finding}} — {{benchmark}}" — Diagnosis
- diagnosis_fail: "✕ {{finding}} — {{benchmark}}. Fix: {{recommendation}}" — Diagnosis
- corpus_cite: "Dựa trên {{count}} video {{niche}} {{timeframe}}" — Ambient
- creator_card_label: "@{{handle}} · {{followers}} followers · {{total_likes}} likes · {{contact}}" — Creator Discovery
- brief_hook: "{{number}}. {{hook_text}} — {{delivery_note}}" — Brief Generation
- brief_kol: "{{tier}} {{follower_range}} · Est. {{cost_range}} · Commission {{commission_pct}}" — Brief Generation

**Edge cases:**

- User pastes non-TikTok URL → URLChip shows error state; send button still enabled
- User pastes carousel (image slides) URL → intent ① handles slide-by-slide; no special UI needed
- User types 1000+ characters → input stops, overflow message appears 3s then fades
- Session with many messages (100+) → MessageList virtualizes; scroll performance maintained
- Network lost mid-stream → error message "— Bị gián đoạn. Gõ 'tiếp' để tiếp tục." appended inline
- iOS keyboard opens → ChatInput scrolls up; CreditBar stays above keyboard

**Credit cost:** 1 deep credit per deep intent (①–⑤). Free for ⑥, ⑦, and follow-ups within same session.

---

## TrendScreen

**Route:** `/app/trends`

**Components:**

- `NicheSelector` — horizontal scrollable chip row at top; current niche highlighted in `--purple`; all 17 niches available
- `TrendHeader` — niche name + "Xu hướng tuần này" heading + corpus citation
- `HookRankingSection` — section heading + list of `HookRankingBar` items (D2 animation on mount)
- `HookRankingBar` — hook name + animated bar (0→% width, 400ms cubic) + multiplier number (fades in at bar end)
- `CorpusCite` — "{{count}} video · 7 ngày · Updated {{hours}}h ago" in JetBrains Mono `--faint`
- `FormatLifecycleSection` — "Formats đang lên ↑" + "Formats đang xuống ↓" lists (use arrow text characters, not emoji)
- `TrendingKeywordSection` — sound/keyword chips with usage count
- `ThumbnailStrip` — horizontal strip of top-performing reference videos for the week

**Data:**


| Variable                             | Source                   | Default if null               |
| ------------------------------------ | ------------------------ | ----------------------------- |
| niche_intelligence.hook_rankings     | niche_intelligence table | [] (show empty state)         |
| niche_intelligence.format_lifecycle  | niche_intelligence table | []                            |
| niche_intelligence.trending_keywords | niche_intelligence table | []                            |
| niche_intelligence.indexed_at        | niche_intelligence table | — (show "Data chưa cập nhật") |
| niche_intelligence.video_count_7d    | niche_intelligence table | 0                             |
| profiles.primary_niche               | profiles table           | first niche in taxonomy list  |


**States:**

- Loading: StreamingStatusText "Đang tải xu hướng {{niche}}..." (Normal 200ms transition). HookRankingBars show as gray placeholders.
- Error: "Không tải được data tuần này — thử lại sau vài phút." in-place, retry button.
- Empty (no data for niche yet): "Chưa có đủ data cho niche {{niche}} tuần này. Thử xem xu hướng của Review đồ gia dụng — niche có data đầy đủ nhất."

**Interaction flow:**

1. Screen loads → NicheSelector shows at top with `profiles.primary_niche` selected (purple). HookRankingSection shows skeleton bars.
2. D2 animation triggers on mount: bars animate width from 0% → final value, 400ms, 100ms stagger. Top bar is purple, others lighter gray. Multiplier fades in last.
3. User taps a different niche chip → niche selection updates, data reloads for new niche. Animation re-runs.
4. User scrolls down → FormatLifecycleSection → TrendingKeywordSection → ThumbnailStrip.
5. User taps ThumbnailCard → opens TikTok URL in external browser.
6. User taps "Phân tích video này" (in ThumbnailCard) → navigates to ChatScreen with that URL pre-loaded in input.
7. CreditBar visible at bottom (same as ChatScreen).

**Navigation:**

- Enters from: ChatScreen (bottom nav "Xu hướng" tab), any screen via bottom nav
- Exits to: ChatScreen (bottom nav), HistoryScreen (bottom nav), PricingScreen (CreditBar tap)
- Back: None (tab screen — back gesture stays in tab)

**Dopamine moment:** D2 (HookRankingBars animate on mount and on niche change)

**Copy slots (production-ready):**

- screen_title: "Xu hướng" — Ambient
- section_hook_ranking: "Hook đang chạy trong {{niche}}" — Ambient
- corpus_cite_trend: "{{count}} video · 7 ngày · Updated {{hours}}h ago" — Ambient
- section_format_rising: "Format đang lên" — Ambient
- section_format_falling: "Format đang giảm" — Ambient
- section_keywords: "Âm thanh & từ khóa trending" — Ambient
- empty_trend: "Chưa có đủ data cho {{niche}} tuần này. Thử xem xu hướng của Review đồ gia dụng — niche có data đầy đủ nhất." — Empty
- error_trend: "Không tải được data tuần này — thử lại sau vài phút." — Error
- thumbnail_action: "Phân tích video này" — Ambient

**Edge cases:**

- Batch job failed (data >36h old) → CorpusCite shows warning color and "Data cũ hơn 36 tiếng — đang cập nhật."
- Niche has <10 videos indexed → empty state with redirect to best-data niche
- TikTok URL in ThumbnailCard opens in TikTok app if installed (deep link), else browser

**Credit cost:** Free (⑥ Trend Spike is unlimited)

---

## HistoryScreen

**Route:** `/app/history`

**Components:**

- `HistoryHeader` — "Lịch sử" title (left) + `SettingsIcon` (right, tap → SettingsScreen)
- `HistorySearchBar` — search input to filter sessions by query text
- `SessionList` — scrollable list of `SessionItem` components
- `SessionItem` — intent type icon + first query truncated to 2 lines + date + credit cost used
- `IntentBadge` — small badge: "Soi Video" | "Xu hướng" | "KOL" | "Brief" | "Đối thủ" | "Soi Kênh"
- `BottomNav` — Lịch sử tab active

**Data:**


| Variable                      | Source              | Default if null |
| ----------------------------- | ------------------- | --------------- |
| chat_sessions[].id            | chat_sessions table | —               |
| chat_sessions[].first_message | chat_sessions table | "Phiên trống"   |
| chat_sessions[].intent_type   | chat_sessions table | null            |
| chat_sessions[].created_at    | chat_sessions table | —               |
| chat_sessions[].credits_used  | chat_sessions table | 0               |


**States:**

- Loading: 3 skeleton SessionItem placeholders (gray bars, pulsing)
- Error: "Không tải được lịch sử — thử lại." with retry button
- Empty: "Chưa có phiên nào. Dán link TikTok hoặc hỏi câu đầu tiên để bắt đầu."

**Interaction flow:**

1. Screen loads → SessionList renders with most recent sessions first.
2. User taps HistorySearchBar → keyboard opens, session list filters as user types.
3. User taps a SessionItem → navigates to ChatScreen with that session's messages loaded (resumed mode). SessionItem's first message pre-fills context.
4. ChatScreen in resumed mode shows full previous conversation. User can continue asking follow-ups.
5. CreditBar visible at bottom.

**Navigation:**

- Enters from: Any screen via bottom nav "Lịch sử" tab
- Exits to: ChatScreen (tap session → resume), ChatScreen (bottom nav Chat tab)
- Back: None (tab screen)

**Dopamine moment:** none

**Copy slots (production-ready):**

- screen_title: "Lịch sử" — Ambient
- search_placeholder: "Tìm trong lịch sử..." — Ambient
- empty_history: "Chưa có phiên nào. Dán link TikTok hoặc hỏi câu đầu tiên để bắt đầu." — Empty
- error_history: "Không tải được lịch sử — thử lại." — Error
- session_date_today: "Hôm nay" — Ambient
- session_date_yesterday: "Hôm qua" — Ambient
- intent_badge_diagnosis: "Soi Video" — Ambient
- intent_badge_trends: "Xu hướng" — Ambient
- intent_badge_creator: "Tìm KOL" — Ambient
- intent_badge_brief: "Brief" — Ambient
- intent_badge_competitor: "Đối thủ" — Ambient
- intent_badge_soikenh: "Soi Kênh" — Ambient

**Edge cases:**

- > 100 sessions → infinite scroll (load 20 at a time)
- Session with failed response → still shows in list; content shows error state when reopened

**Credit cost:** N/A (history browsing is free)

---

## PricingScreen

**Route:** `/app/pricing`

**Components:**

- `BillingToggle` — 3-state: "Tháng" | "6 tháng" | "Năm" (annual pre-selected, badge "Tiết kiệm nhất")
- `PricingCard` — tier card: name + price + credit count + feature list + CTA button. Free / Starter / Pro / Agency
- `PricingCardHighlight` — Starter card has "Phổ biến nhất" badge
- `OverageSection` — heading "Mua thêm credits" + 2 overage pack cards
- `PaymentMethodRow` — icons for MoMo, VNPay, bank transfer, card
- `CurrentPlanBadge` — shown on user's current plan (non-interactive)

**Data:**


| Variable                        | Source         | Default if null |
| ------------------------------- | -------------- | --------------- |
| profiles.subscription_tier      | profiles table | "free"          |
| profiles.deep_credits_remaining | profiles table | 0               |
| profiles.credits_reset_at       | profiles table | —               |


**States:**

- Loading: Skeleton pricing cards (gray boxes, pulsing)
- Error: "Không tải được gói cước — thử lại." with retry
- Empty: n/a (static pricing)

**Interaction flow:**

1. Screen loads → Annual billing toggle pre-selected. Starter card highlighted with "Phổ biến nhất" badge. User's current plan has "Gói hiện tại" badge.
2. User taps billing period toggle → prices update instantly (Instant 0ms). Savings callouts appear/update.
3. User taps "Nâng cấp" on a paid tier → CheckoutScreen with selected plan + billing period.
4. User taps "Bắt đầu miễn phí" (Free tier) → already on free, button shows "Gói hiện tại" (inactive).
5. User taps overage pack → CheckoutScreen with overage pack selected.
6. User scrolls down → OverageSection → PaymentMethodRow → FAQ link.

**Navigation:**

- Enters from: ChatScreen (CreditBar tap), ChatScreen ("Mua thêm →" inline tap), SettingsScreen ("Nâng cấp" button), any screen via SettingsScreen
- Exits to: CheckoutScreen (tap plan/pack), ChatScreen (back/close)
- Back: ChatScreen (back arrow or hardware back)

**Dopamine moment:** none

**Copy slots (production-ready):**

- screen_title: "Chọn gói phù hợp" — Ambient
- billing_monthly: "Tháng" — Ambient
- billing_6month: "6 tháng" — Ambient
- billing_annual: "Năm" — Ambient
- annual_badge: "Tiết kiệm nhất" — Ambient
- popular_badge: "Phổ biến nhất" — Ambient
- current_plan_badge: "Gói hiện tại" — Ambient
- tier_free_name: "Dùng thử" — Ambient
- tier_free_price: "Miễn phí" — Ambient
- tier_free_credits: "10 lần phân tích sâu · Lifetime" — Ambient
- tier_free_cta: "Bắt đầu miễn phí" — Ambient
- tier_starter_name: "Starter" — Ambient
- tier_starter_price_monthly: "249.000đ/tháng" — Ambient
- tier_starter_price_sixmo: "219.000đ/tháng · thanh toán 6 tháng" — Ambient
- tier_starter_price_annual: "199.000đ/tháng · thanh toán cả năm" — Ambient
- tier_starter_credits: "30 lần phân tích sâu/tháng" — Ambient
- tier_starter_cta: "Nâng cấp Starter" — Ambient
- tier_pro_name: "Pro" — Ambient
- tier_pro_price_monthly: "499.000đ/tháng" — Ambient
- tier_pro_price_sixmo: "449.000đ/tháng · thanh toán 6 tháng" — Ambient
- tier_pro_price_annual: "399.000đ/tháng · thanh toán cả năm" — Ambient
- tier_pro_credits: "80 lần phân tích sâu/tháng" — Ambient
- tier_pro_cta: "Nâng cấp Pro" — Ambient
- tier_agency_name: "Agency" — Ambient
- tier_agency_price_monthly: "1.490.000đ/tháng" — Ambient
- tier_agency_price_sixmo: "1.350.000đ/tháng · thanh toán 6 tháng" — Ambient
- tier_agency_price_annual: "1.190.000đ/tháng · thanh toán cả năm" — Ambient
- tier_agency_credits: "250 lần phân tích sâu/tháng · 10 tài khoản" — Ambient
- tier_agency_cta: "Nâng cấp Agency" — Ambient
- annual_starter_saving: "Tiết kiệm 600.000đ so với gói tháng" — Ambient
- annual_pro_saving: "Tiết kiệm 1.200.000đ so với gói tháng" — Ambient
- annual_agency_saving: "Tiết kiệm 3.600.000đ so với gói tháng" — Ambient
- sixmo_starter_saving: "Tiết kiệm 180.000đ so với gói tháng" — Ambient
- sixmo_pro_saving: "Tiết kiệm 300.000đ so với gói tháng" — Ambient
- sixmo_agency_saving: "Tiết kiệm 840.000đ so với gói tháng" — Ambient
- sixmo_callout: "Tặng 1 tháng miễn phí khi mua 6 tháng" — Ambient
- overage_section_title: "Mua thêm credits" — Ambient
- overage_10: "10 lần phân tích sâu — 130.000đ" — Ambient
- overage_50: "50 lần phân tích sâu — 600.000đ (12.000đ/lần)" — Ambient
- payment_methods: "Thanh toán qua MoMo, VNPay, chuyển khoản, hoặc thẻ quốc tế." — Ambient

**Edge cases:**

- User on Starter tries to buy Agency → goes directly to checkout for Agency, no downgrade warning
- User on paid plan tries to buy overage → allowed (credits stack)
- Annual plan price display: show "199.000đ/tháng" with "thanh toán cả năm = 2.388.000đ" clarification below

**Credit cost:** N/A

---

## CheckoutScreen

**Route:** `/app/checkout`

> **⚠ Phase 4 flag — N2:** Payment method pre-selection rule (from northstar §14): if billing period is **monthly or 6-month** → pre-select MoMo; if billing period is **annual** → pre-select bank transfer (chuyển khoản). This logic lives in the Frontend Developer's checkout hook — Figma Make will render with MoMo as default for all. The pre-selection swap happens at runtime via state, not by changing the static Make layout.

**Components:**

- `OrderSummary` — plan name + billing period + total amount in VND
- `PaymentMethodSelector` — 4 options: MoMo | VNPay | Chuyển khoản | Thẻ quốc tế (radio buttons)
- `MoMoQR` — QR code image + "Mở app MoMo để quét" instruction (shown when MoMo selected)
- `VNPayQR` — QR code image + instruction (shown when VNPay selected)
- `BankTransferDetails` — bank name + account number + account name + reference code (shown when bank selected)
- `CardForm` — card number + expiry + CVV inputs (shown when card selected)
- `ConfirmButton` — "Xác nhận thanh toán" primary button
- `PaymentStatusPoll` — status polling indicator while awaiting PayOS webhook

**Data:**


| Variable                | Source                           | Default if null                       |
| ----------------------- | -------------------------------- | ------------------------------------- |
| order.plan_id           | route state (from PricingScreen) | — (redirect to PricingScreen if null) |
| order.amount_vnd        | derived from plan_id             | —                                     |
| order.billing_period    | route state                      | "annual"                              |
| payos.payment_link_id   | PayOS API response               | —                                     |
| payos.qr_code           | PayOS API response               | —                                     |
| payos.bank_transfer_ref | PayOS API response               | —                                     |


**States:**

- Loading: QR generation loading skeleton + "Đang tạo mã thanh toán..." text
- Error: "Không tạo được đơn hàng — thử lại hoặc dùng phương thức khác." with retry
- Pending (after confirm): "Đang chờ xác nhận thanh toán..." status text + polling indicator

**Interaction flow:**

1. Screen loads → OrderSummary visible at top. PaymentMethodSelector below. MoMo pre-selected (monthly packs) or bank transfer pre-selected (annual/6-month packs, per northstar §14).
2. PayOS API called on load → QR code or bank details generated.
3. IF MoMo/VNPay selected → QR code displays. User opens MoMo/VNPay app, scans QR.
4. IF bank transfer selected → bank details + unique reference number display. User makes bank transfer with reference code.
5. IF card selected → CardForm displays. User fills card details.
6. Payment confirmed → PayOS webhook fires → credit ledger updates → navigate to PaymentSuccessScreen.
7. IF user taps "Xác nhận thanh toán" on MoMo/VNPay → starts polling PayOS for confirmation.

**Navigation:**

- Enters from: PricingScreen (tap plan CTA)
- Exits to: PaymentSuccessScreen (payment confirmed), PricingScreen (back/cancel)
- Back: PricingScreen (back arrow)

**Dopamine moment:** none

**Copy slots (production-ready):**

- screen_title: "Thanh toán" — Ambient
- summary_plan: "{{plan_name}} · {{billing_period}}" — Ambient
- summary_amount: "{{amount_vnd}}đ" — Ambient
- method_momo: "MoMo" — Ambient
- method_vnpay: "VNPay" — Ambient
- method_bank: "Chuyển khoản ngân hàng" — Ambient
- method_card: "Thẻ quốc tế" — Ambient
- qr_instruction_momo: "Mở app MoMo → Quét mã → Xác nhận" — Ambient
- qr_instruction_vnpay: "Mở app VNPay → Quét mã → Xác nhận" — Ambient
- bank_ref_label: "Nội dung chuyển khoản (bắt buộc)" — Ambient
- confirm_button: "Xác nhận thanh toán" — Ambient
- loading_qr: "Đang tạo mã thanh toán..." — Loading
- pending_payment: "Đang chờ xác nhận thanh toán..." — Loading
- error_order: "Không tạo được đơn hàng — thử lại hoặc dùng phương thức khác." — Error

**Edge cases:**

- QR code expires (PayOS default 15 minutes) → show "Mã đã hết hạn" + "Tạo mã mới" button
- Bank transfer not confirmed within 48h → credits not added; user sees status in SettingsScreen "Đang chờ xác nhận"
- Card declined → "Thẻ không hợp lệ hoặc không đủ tiền — thử thẻ khác hoặc dùng MoMo." in-place error

**Credit cost:** N/A

---

## PaymentSuccessScreen

**Route:** `/app/payment-success`

> **⚠ Phase 4 flag — N1:** This route must receive payment result data (plan name, credit delta) via React Router `state` (e.g., `navigate('/app/payment-success', { state: { planName, creditsDelta } })`). On page refresh, `state` is lost — fall back to a Supabase `profiles` fetch for the credit balance, and show the heading as "Credits đã được cập nhật." without the plan name. Do NOT pass data as query params (leaks to logs).

**Components:**

- `SuccessIcon` — static checkmark icon (no confetti — work tool, not game)
- `SuccessSummary` — plan activated + new credit balance
- `CreditBalanceDisplay` — large JetBrains Mono number: new credit count
- `BackToChat` — primary button "Bắt đầu phân tích ngay"

**Data:**


| Variable                        | Source                       | Default if null |
| ------------------------------- | ---------------------------- | --------------- |
| profiles.deep_credits_remaining | profiles table (post-update) | 0               |
| profiles.subscription_tier      | profiles table (post-update) | "free"          |
| order.plan_name                 | route state                  | —               |


**States:**

- Loading: "Đang kích hoạt gói..." skeleton (brief, payment has succeeded by this point)
- Error: "Thanh toán thành công nhưng credits chưa cập nhật — liên hệ [support@getviews.vn](mailto:support@getviews.vn)" (rare edge case)
- Empty: n/a

**Interaction flow:**

1. Screen loads (after PayOS webhook confirmed) → SuccessIcon. Heading: "Đã thêm {{count}} deep credits." Credit balance displays in large JetBrains Mono.
2. D5 (CreditConsumption, refill variant): CreditBar border flashes `--purple` 200ms, then credit count increments from old balance to new balance over 800ms (same component as in ChatScreen, but direction is upward — adding credits).
3. User taps "Bắt đầu phân tích ngay" → ChatScreen. First chat session pre-populated prompt: "Dán link video đầu tiên để phân tích."
4. Hardware back while on this screen → ChatScreen (not PricingScreen — payment is done).

**Navigation:**

- Enters from: CheckoutScreen (payment confirmed)
- Exits to: ChatScreen (button or back)
- Back: ChatScreen (hardware back goes home, not pricing)

**Dopamine moment:** Credit balance increment animation (variant of D5 — upward instead of downward)

**Copy slots (production-ready):**

- screen_heading: "Đã thêm {{count}} deep credits." — Confirmation
- plan_activated: "Gói {{plan_name}} đã kích hoạt. Credits có hiệu lực đến {{expiry_date}}." — Confirmation
- credit_label: "Deep credits còn lại" — Ambient
- cta_button: "Bắt đầu phân tích ngay" — Ambient
- loading_activate: "Đang kích hoạt gói..." — Loading
- error_credits_delay: "Thanh toán thành công nhưng credits chưa cập nhật — liên hệ [support@getviews.vn](mailto:support@getviews.vn) nếu chưa thấy sau 5 phút." — Error

**Edge cases:**

- User navigates away before screen loads → credits still added via webhook; visible in SettingsScreen
- Annual plan: expiry_date shown as "{{31 Dec 2026}}"

**Credit cost:** N/A

---

## SettingsScreen

**Route:** `/app/settings`

**Components:**

- `ProfileSection` — avatar (initial letter from display_name) + display_name + email (from OAuth)
- `SubscriptionSection` — current plan name + credits remaining + expiry date + "Nâng cấp" button
- `NicheSection` — current niche label + "Thay đổi" button → inline input to change niche
- `CreditHistoryList` — list of credit consumption events: date + intent type + amount
- `RenewalSection` — next renewal date or pack expiry + "Gia hạn" button (links to PricingScreen)
- `LogoutButton` — secondary style, `--danger` text color

**Data:**


| Variable                        | Source              | Default if null |
| ------------------------------- | ------------------- | --------------- |
| profiles.display_name           | profiles table      | "Bạn"           |
| profiles.email                  | profiles table      | —               |
| profiles.subscription_tier      | profiles table      | "free"          |
| profiles.deep_credits_remaining | profiles table      | 0               |
| profiles.credits_reset_at       | profiles table      | —               |
| profiles.primary_niche          | profiles table      | —               |
| credit_ledger[].intent_type     | credit_ledger table | —               |
| credit_ledger[].created_at      | credit_ledger table | —               |


**States:**

- Loading: Skeleton rows for ProfileSection + SubscriptionSection
- Error: "Không tải được thông tin tài khoản — thử lại."
- Empty: n/a (always has profile data post-auth)

**Interaction flow:**

1. Screen loads → ProfileSection (avatar, name, email). SubscriptionSection below.
2. User taps "Thay đổi" in NicheSection → NicheInput appears inline (same component as OnboardingScreen). User selects new niche → saves to `profiles.primary_niche` → NicheBadge in ChatScreen updates.
3. User taps "Nâng cấp" → PricingScreen.
4. User taps "Gia hạn" → PricingScreen with current tier pre-selected.
5. User scrolls → CreditHistoryList shows last 20 credit events with intent types.
6. User taps LogoutButton → inline confirmation "Đăng xuất khỏi GetViews?" with "Đăng xuất" and "Hủy". Confirms → auth cleared → LoginScreen.

**Navigation:**

- Enters from: ChatScreen (settings icon tap in header), TrendScreen or HistoryScreen (via settings icon)
- Exits to: PricingScreen ("Nâng cấp"/"Gia hạn" taps), LoginScreen (logout), ChatScreen (back)
- Back: ChatScreen (back arrow)

**Dopamine moment:** none — settings screen is zero animation

**Copy slots (production-ready):**

- screen_title: "Tài khoản" — Ambient
- section_profile: "Thông tin" — Ambient
- section_subscription: "Gói cước" — Ambient
- subscription_tier_label: "Gói {{tier_name}}" — Ambient
- subscription_credits: "{{count}} deep credits còn lại" — Ambient
- subscription_expiry: "Credits hết hạn: {{expiry_date}}" — Ambient
- upgrade_button: "Nâng cấp" — Ambient
- renew_button: "Gia hạn" — Ambient
- section_niche: "Niche của bạn" — Ambient
- niche_change: "Thay đổi" — Ambient
- niche_save: "Lưu" — Confirmation
- section_history: "Lịch sử credit" — Ambient
- credit_event_label: "{{intent_name}} · {{date}} · −1 credit" — Ambient
- logout_button: "Đăng xuất" — Ambient
- logout_confirm: "Đăng xuất khỏi GetViews?" — Ambient
- logout_confirm_cta: "Đăng xuất" — Ambient
- logout_cancel: "Hủy" — Ambient
- error_settings: "Không tải được thông tin tài khoản — thử lại." — Error

**Edge cases:**

- Free tier user: SubscriptionSection shows "10 lần phân tích sâu miễn phí (lifetime)" with no expiry
- Expired pack: credits_reset_at in past → "Gói đã hết hạn — gia hạn để tiếp tục phân tích sâu."
- User changes niche to one not in taxonomy → stored as-is; niche inference resolves on next query

**Credit cost:** N/A

---

## Navigation Plan

### Bottom Navigation (mobile PWA)


| Tab | Label    | Route          | Icon             |
| --- | -------- | -------------- | ---------------- |
| 1   | Chat     | `/app`         | Chat bubble icon |
| 2   | Xu hướng | `/app/trends`  | Trending up icon |
| 3   | Lịch sử  | `/app/history` | Clock icon       |


Settings accessed via header icon in ChatScreen, TrendScreen, HistoryScreen.

### Complete Navigation Graph

```
/ (LandingPage)
  → /login (CTA tap, if not logged in)
    → /onboarding (new user OAuth success)
      → /app (onboarding complete)
    → /app (returning user OAuth success)

/app (ChatScreen — home)
  → /app/trends (bottom nav tab 2)
  → /app/history (bottom nav tab 3)
  → /app/settings (header icon)
  → /app/pricing (CreditBar zero tap, inline "Mua thêm" tap)
  ← /app/history (tap session → resume)
  ← /app/payment-success (after payment)

/app/trends (TrendScreen)
  → /app (bottom nav tab 1)
  → /app/history (bottom nav tab 3)
  → /app/settings (header icon)
  → /app/pricing (CreditBar zero tap)

/app/history (HistoryScreen)
  → /app (bottom nav tab 1, or tap session → resume)
  → /app/trends (bottom nav tab 2)
  → /app/settings (header icon)

/app/settings (SettingsScreen)
  → /app/pricing (Nâng cấp / Gia hạn)
  → /login (logout)
  ← back → previous screen

/app/pricing (PricingScreen)
  → /app/checkout (tap plan CTA)
  ← back → previous screen

/app/checkout (CheckoutScreen)
  → /app/payment-success (payment confirmed)
  ← back → /app/pricing

/app/payment-success (PaymentSuccessScreen)
  → /app (button tap or back)
```

---

## Completeness Validation

### User Scenario 01 (Minh — Starter):

- Opens app → ChatScreen (empty state) ✓
- Pastes URL → ChatScreen (streaming D1) ✓
- Follow-up questions → ChatScreen (free, same session) ✓
- Checks trends → TrendScreen (D2) ✓
- Credits low → CreditBar warning → PricingScreen → CheckoutScreen → PaymentSuccessScreen ✓

### User Scenario 02 (Linh — Pro):

- Asks trends → TrendScreen or ChatScreen ✓
- Video analysis (deep credit) → ChatScreen ✓
- Find creators (free ⑦) → ChatScreen inline ✓
- Competitor profile (deep credit) → ChatScreen ✓
- Brief generation (deep credit) → ChatScreen (D3) ✓
- Copy brief → copy button → plain text for Zalo ✓

### Auth Flow:

- New user: LandingPage → LoginScreen → OnboardingScreen → ChatScreen ✓
- Returning user: LandingPage → LoginScreen → ChatScreen ✓
- Logout: SettingsScreen → LoginScreen ✓

### Payment Flow:

- See credits → PricingScreen → CheckoutScreen → PaymentSuccessScreen → ChatScreen with updated credits ✓

All flows validated. No dead ends. No teleports.