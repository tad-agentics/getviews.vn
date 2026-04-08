# Figma Make Brief — GetViews.vn

**Date:** 2026-04-08  
**Screen count:** 10 screens  
**Platform:** Mobile-first PWA. 375px baseline. Desktop-capable.  
**Font:** TikTok Sans (primary), JetBrains Mono (data/numbers)  
**Palette:** Light mode only — oklch-based tokens (see styles.md below)

---

## Guidelines.md Setup

Before the first prompt, create these 5 files in Make's Guidelines folder. Content for each is below.

**File routing:** `Guidelines.md` (root) → reads `@styles.md`, `@components.md`, `@copy.md`, `@anti-patterns.md`

---

### guidelines/Guidelines.md

```markdown
# GetViews.vn — Design Guidelines

## Design System
Read: @styles.md

## Component Rules
Read: @components.md

## Copy Rules
Read: @copy.md

## Anti-patterns
Read: @anti-patterns.md
```

---

### guidelines/styles.md

```markdown
# Styles — GetViews.vn

## Colors
Use CSS custom properties ONLY. Never raw hex in components.

> **Token mapping note (for Frontend Developer):** Figma Make will generate code using the `--purple` / `--purple-dark` / `--purple-light` token names defined here. When porting Make TSX into `src/routes/`, replace them with the codebase tokens: `--purple` → `--color-primary`, `--purple-dark` → `--color-primary-dark`, `--purple-light` → `--color-primary-light`. All other tokens (`--background`, `--surface`, `--ink`, etc.) should be declared in `src/app.css` to match exactly.

- --purple: oklch(0.53 0.26 295) / #7C3AED — Send button, active states, gradient text, card hover border
- --purple-dark: oklch(0.45 0.28 295) / #6D28D9 — Hover on purple elements
- --purple-light: oklch(0.95 0.03 295) / #F3F0FF — Active sidebar bg, card hover bg, user message bubble bg
- --background: oklch(0.93 0.00 0) / #EDEDEE — Page background
- --surface: oklch(1.00 0.00 0) / #FFFFFF — Cards, input fields, chat message bg
- --surface-alt: oklch(0.97 0.00 0) / #F7F7F8 — Mode badges, secondary surfaces, brief blocks
- --ink: oklch(0.15 0.00 0) / #18181B — Primary text, headings, user messages
- --ink-soft: oklch(0.30 0.00 0) / #3F3F46 — Body text, card text
- --muted: oklch(0.55 0.00 0) / #71717A — Secondary text, icons
- --faint: oklch(0.68 0.00 0) / #A1A1AA — Placeholder text, disabled, char counter
- --border: oklch(0.90 0.00 0) / #E4E4E7 — Default borders, dividers (1px only)
- --border-active: oklch(0.85 0.00 0) / #D4D4D8 — Hover borders
- --brand-red: oklch(0.60 0.28 15) / #FE2C55 — Logo mark only. Do NOT use elsewhere.
- --success: oklch(0.60 0.18 145) / #25F4EE — ✓ markers in diagnosis, positive signals
- --danger: oklch(0.55 0.22 25) / #D93B3B — ✕ markers, error states, low credit warning

## Typography
- Headings: TikTok Sans — weight 800 (extra bold). Use for screen titles, section headings, result headings.
- Body: TikTok Sans — weight 400/500. 16px minimum on mobile (prevents iOS zoom).
- Data/Numbers: JetBrains Mono — credit counts, statistics, multipliers, corpus sizes, timestamps.
- Vietnamese diacritics must render correctly at all sizes.
- Mobile body: 16px. Desktop body: 15px.

IMPORTANT: Use font-display: swap for all @font-face declarations.

## Spacing
Base unit: 4px. Allowed multiples: 4, 8, 12, 16, 24, 32, 48, 64px.
IMPORTANT: No arbitrary spacing values. Stick to this scale.
Side padding on mobile: 12px. On desktop: 24px+ centered at 720px max-width.

## Border Radius
Cards: 12px. Buttons: 8px. Inputs: 8px. Badges/chips/pills: 980px (fully rounded). Thumbnails: 12px.
IMPORTANT: Do NOT use uniform border-radius across all elements.

## Borders
1px only. No shadows on any element. No elevation. No depth. Flat UI.
Active/hover states use border color change, not shadows.

## Transitions
- Instant (0ms): checkbox toggle, radio select, active press color
- Fast (120ms ease-out): hover bg, border color, icon color, focus ring
- Normal (200ms ease-out): panel slide, tab switch, tooltip
- Emphasis (400ms cubic-bezier(0.16, 1, 0.3, 1)): diagnosis row reveal, bar chart fill, card stagger
- Slow (600-800ms cubic-bezier(0.16, 1, 0.3, 1)): dopamine moments only

Hard rule: nothing in the product takes >800ms.

## Dark Mode
No — light mode only for v1. Do NOT generate dark mode variants.
```

---

### guidelines/components.md

```markdown
# Component Rules — GetViews.vn

## File Structure
- screens/ — one file per screen
- components/ui/ — shared primitives (Button, Input, Card, Badge, Tabs)
- components/ — shared feature components (CreditBar, ThumbnailStrip, DiagnosisRow, etc.)
- lib/ — mock data, helpers

IMPORTANT: Never put everything in App.tsx. Each screen is a separate file.
IMPORTANT: Screen-specific components colocate with their screen file.

## Interactive Components
- All buttons: visible hover (--surface-alt bg, Fast 120ms) + active (scale 0.95, 80ms)
- Send button: --faint bg when input empty (not clickable) → --purple bg when has input (Fast 120ms)
- All inputs: focus ring 1px --purple (Fast 120ms). Error state 1px --danger. 16px font minimum.
- Modals: use Radix Dialog. Dropdowns/selects: use Radix Select. Toasts: use Sonner.
- Accordion: use Radix Accordion (FAQ on landing page)
- IMPORTANT: Use Radix UI primitives for all interactive components — not raw divs.

## Chat-Specific Components
- UserMessageBubble: right-aligned, --purple-light bg, --ink text, max-width 80%, 12px border-radius
- AssistantMessageBlock: left-aligned, --surface bg, full-width, 1px --border top/bottom as separators (NOT bubble shape)
- DiagnosisRow: ✕ in --danger or ✓ in --success + finding text + benchmark. Left border 2px --purple on first ✕ row.
- HookRankingBar: label left + animated bar (bg: --purple for top, --border-active for others) + multiplier right in JetBrains Mono
- ThumbnailCard: 120px wide, 9:14 aspect, 12px border-radius, tap → open TikTok URL
- ThumbnailStrip: horizontal-scroll container showing 2.5 thumbnails in viewport
- CreditBar: fixed above input area, full-width, 48px height, 1px --border top
- FreeQueryPill: inline next to UserMessageBubble, --purple text on --purple-light bg, pill shape, fades after 2s
- StreamingStatusText: left-aligned text below last message, --muted color, transitions between phases

## Animations — Dopamine Moments
D1 (DiagnosisReveal): ✕/✓ rows stagger in from left, 150ms each (opacity 0→1, translateX -12px→0). Red ✕ rows first. 800ms total.
D2 (HookRankingBars): bars animate width 0→final, 400ms cubic-bezier(0.16,1,0.3,1), 100ms stagger. Multiplier fades in after bar. 600ms total.
D3 (BriefBlocks): sections slide in sequentially, 200ms delay each. "Copy brief" button scales in (0.95→1.0) after last block.
D4 (CreatorCards): cards stack in from bottom, opacity 0→1, 100ms stagger. 500ms for 5 cards.
D5 (CreditConsumption): CreditBar border flashes --purple 200ms, then credit count decrements by 1. "−1" ghost floats up (translateY 0→-12px, opacity 1→0, 400ms). Triggered after every deep-credit query.
D6 (FreeQueryConfirmation): FreeQueryPill ("Miễn phí ✓") fades in next to user bubble (120ms), lingers 2s, fades out (200ms). No bounce. Triggered for free-intent queries only.

Use motion (Framer Motion) ONLY for these D1–D6 moments. Not for every element.
Prefer transform + opacity. Never animate width/height directly (use scaleX for bars).

## Mobile Layout Rules
- Mobile first: 375px baseline. Side padding: 12px.
- Bottom navigation: 3 tabs only (Chat | Xu hướng | Lịch sử)
- Input fixed to bottom — always visible, does not scroll. 12px safe-area padding.
- Single-column vertical scroll as default layout.
- Prompt cards: 2-column grid, min-height 52px, text truncates at 2 lines.
- Touch targets: 44×44px minimum for all tappable elements. Gap between tappable elements: 8px min.
- No hover-dependent interactions — use tap as primary.

## States — Mandatory
Every data-dependent component must implement:
- Loading: use StreamingStatusText (chat) or skeleton placeholders (lists). NO spinner on main content.
- Error: inline error text with retry action. No modal.
- Empty: guided action (not just "No data").
```

---

### guidelines/copy.md

```markdown
# Copy Rules — GetViews.vn

## Formula
State the data → name the finding → give the specific fix. Evidence before opinion.
Length: 1–2 sentences per point. No paragraph answers.

## Language
- All copy in Vietnamese (tiếng Việt). 100% Vietnamese UI.
- Address user as "bạn". Never "bạn ấy" or "người dùng".
- English loanwords standard in Vietnamese creator culture — use without translation: hook, content, viral, trend, brief, format, niche, view, follower, like, creator, KOL, KOC.
- Vietnamese numbers: use dấu chấm as thousand separator: 1.000, 10.000, 1.000.000.
- VND amounts: display with "đ" or "VND" suffix: 249.000đ or 249K.

## Tone
- Peer-to-peer expert. Not teacher. Not guru. Not motivational.
- Direct, data-backed, specific. "92% top video trong niche mở bằng mặt" — not "nên cải thiện phần mở đầu".

## Forbidden Words (NEVER use anywhere)
tuyệt vời, hoàn hảo, bí mật, công thức vàng, đột phá, kỷ lục, triệu view, bùng nổ, siêu hot, thần thánh, hack, chiến lược độc quyền, ai cũng phải biết, không thể bỏ qua, chắc chắn thành công

## Forbidden Opening Words (NEVER start copy with)
Chào bạn, Xin chào, Rất vui, Tuyệt vời, Wow, Chúc mừng, Đây là, Dưới đây là

## Key Copy Patterns
- Empty state: Warm, not sorry. Always include next action. No "Oops" or "Rất tiếc."
  Example: "Chưa có phiên nào. Dán link TikTok hoặc hỏi câu đầu tiên để bắt đầu."
- Error: What failed + what to do. One sentence. No apology. No emoji.
  Example: "Video không tải được — thử dán lại hoặc dùng video khác."
- Paywall: Flat, honest, transactional. No FOMO. No countdown.
  Example: "Hết deep credit tháng này. Mua thêm 10 credit = 130.000 VND."
- Confirmation: State what happened + enable next action. Max 1 sentence.
  Example: "Đã copy — forward qua Zalo cho KOL luôn."
- Loading (chat): Describe what GetViews is doing, not generic "Đang tải..."
  Example: "Đang so sánh với 412 video trong niche..."
```

---

### guidelines/anti-patterns.md

```markdown
# Anti-patterns — NEVER generate these

## Visual Anti-patterns
- No gradient backgrounds (purple-to-blue, purple-to-pink, etc.) — flat color only
- No shadows on cards, buttons, or modals — 1px border only
- No decorative blobs, wavy dividers, ambient orbs, or floating shapes
- No 3-column icon-in-circle feature grids (the classic AI slop layout)
- No global text-align: center on body copy or card content — only for hero headings
- No emoji as visual design elements in UI chrome — ✕/✓ markers replace emoji
- No rounded avatar placeholders with stock photos — initial letters only
- No confetti, fireworks, or celebration animations — this is a work tool
- No skeleton loaders for chat — use StreamingStatusText instead
- No typing indicator dots — use phase-transitioning status text instead
- No colored left-border accent cards as a default pattern (only DiagnosisRow first ✕)
- No purple/violet gradient backgrounds anywhere in the app

## Layout Anti-patterns
- No bottom sheets or modals for content output — everything inline in chat flow
- No blocking modals or full-screen interstitials in the chat flow
- No horizontal scroll except ThumbnailStrip and NicheSelector chips
- No sidebar navigation — use bottom tab bar (mobile)
- No multiple dashboards or summary screens — ChatScreen IS the dashboard

## Copy Anti-patterns
- No "Unlock the power of...", "Your all-in-one solution for..."
- No urgency language in paywall: "Limited time!", "Act now!", "Chỉ còn X giờ!"
- No false certainty: "guaranteed", "100% accurate", "chắc chắn viral"
- No teacher tone: "Bạn nên biết rằng...", "Điều quan trọng là..."
- No apologetic errors: "Xin lỗi, đã xảy ra lỗi!"
- No upsell immediately after a diagnosis/brief result — let the result breathe

## Code Anti-patterns
- No inline styles for values that should be tokens (no style="color: #7C3AED")
- No unnamed div nesting — every wrapper needs semantic purpose
- No everything-in-App.tsx — one file per screen
- No raw hex colors in components — use CSS custom properties
```

---

## First Prompt (copy-paste into Make)

```
TASK: Build a Vietnamese TikTok creator intelligence tool called GetViews.vn with 10 screens:
LandingPage, LoginScreen, OnboardingScreen, ChatScreen, TrendScreen, HistoryScreen, PricingScreen, CheckoutScreen, PaymentSuccessScreen, SettingsScreen.

CONTEXT: GetViews is a chat-first AI product for Vietnamese TikTok creators. The primary user (Minh, 24) pastes a TikTok video URL and gets a Vietnamese-language diagnosis backed by a corpus of 46,000+ analyzed videos — frame-by-frame analysis, hook effectiveness rankings, and specific fixes. Secondary user (Linh, 28) manages KOL campaigns and needs creator discovery + brief generation. The core product is a streaming chat interface with inline structured output: diagnosis rows, hook ranking bars, creator cards, and brief blocks. Everything is inline — no modals, no popups.

Target audience: Vietnamese creators earning from Shopee affiliate + TikTok Shop. Phone-first. One-handed use at 7 AM.
Platform: Mobile-first PWA, 375px baseline. Desktop layout centers at 720px.
Visual register: Flat-minimal-professional. "Tool that works" — not "app that entertains." No gradients, no shadows. 1px borders. Purple accent (#7C3AED) on neutral gray/white backgrounds.

ELEMENTS (per screen):

[LandingPage — route: /]:
- Full-page single-scroll marketing page
- Section 1 — Hero: "Bạn lướt TikTok cả ngày để tìm ý tưởng. GetViews làm việc đó thay bạn." as H1 (bold, 2.5rem mobile). Subheadline: "Dán link video của bạn vào. 1 phút sau biết ngay lỗi ở đâu, nên fix gì, và hook nào đang chạy trong niche của bạn." Below: trust line "Không guru. Không screenshot. Data thực từ video thực." Live input field "Dán link TikTok để bắt đầu" with black CTA button "Soi Video Miễn Phí". Microcopy below button: "10 lần phân tích sâu miễn phí · Lướt xu hướng không giới hạn · Không cần thẻ"
- StickyBar: appears after scroll past hero. "GetViews · Soi Video Miễn Phí" compact bar at bottom, fixed.
- Section 2 — Pain points: 3 cards side-by-side (single column on mobile). "Lướt TikTok Cả Ngày", "Học Rồi Vẫn Không Biết Quay Gì", "Video Flop Mà Không Biết Tại Sao"
- Section 3 — Solutions: 3 matching cards. "Xem Video Thật, Nói Cho Bạn Thật", "Hôm Nay Hỏi, Hôm Nay Có", "Làm Cho Creator Việt Nam"
- Section 4 — Live demo: Static chat mockup showing 5 prompt chips. 1 visible response preview (truncated diagnosis rows).
- Section 5 — Social proof: Before/after stat block. "Video gốc: 2.000 views. GetViews phát hiện hook chậm 2.1 giây, không có mặt người. Quay lại theo gợi ý: 45.000 views."
- Section 6 — Pricing: 3-column tier cards (stacked on mobile). Billing toggle: Tháng | 6 tháng | Năm (Annual pre-selected). Starter highlighted "Phổ biến nhất". Prices: Free/0đ, Starter 249.000đ/199.000đ, Pro 499.000đ/399.000đ, Agency 1.490.000đ/1.190.000đ
- Section 7 — FAQ: Accordion, 6 questions. Vietnamese questions, direct conversational answers.
- Section 8 — Final CTA: Dark background section. "Thử dán 1 link video vào. Miễn phí. Xem GetViews nói gì." CTA button "Soi Video Ngay"

[LoginScreen — route: /login]:
- GetViews logo/wordmark centered at top (TikTok Sans, bold)
- Trust line below logo: "Data thực từ 46.000+ video TikTok Việt Nam — phân tích video của bạn trong 1 phút."
- Facebook login button (primary, full-width, black fill, white text, Facebook icon left): "Đăng nhập với Facebook"
- Google login button (secondary, full-width, --surface bg, 1px border, --ink text, Google icon left): "Đăng nhập với Google"
- Legal note: "Bằng cách đăng nhập, bạn đồng ý với Điều khoản dịch vụ và Chính sách bảo mật."
- Simple, minimal layout — center-aligned vertically on screen

[OnboardingScreen — route: /onboarding]:
- Header: "Bước 2/3" small pill indicator (top right or below logo)
- Heading: "Bạn tạo nội dung về chủ đề gì?" (24px, bold)
- Subtext: "GetViews sẽ dùng data đúng niche của bạn để cho kết quả chính xác hơn."
- Niche input: Full-width text input with placeholder "Nhập niche — ví dụ: review đồ gia dụng, skincare, hài..."
- Smart suggestion chips below input (horizontal scroll): "Review đồ gia dụng", "Làm đẹp / Skincare", "Shopee affiliate", "Review đồ ăn", "Hài phương ngữ", "Công nghệ", "Mẹ bỉm sữa"
- Divider "──── tùy chọn ────"
- Step 3 section: Label "Dán link TikTok profile của bạn" + subtext "Giúp GetViews xác nhận niche từ content thực." + URL input
- "Bỏ qua" skip text link below step 3
- Primary CTA button (bottom): "Bắt đầu phân tích" (--purple bg, white text, full-width, 48px height)

[ChatScreen — route: /app]:
- Header (fixed top): GetViews wordmark left + NicheBadge chip center (e.g., "Review đồ gia dụng") + settings icon right (24×24px, stroke)
- MessageList (scrollable, full-height between header and input): 
  - Empty state: Greeting text "Sẵn sàng phân tích content của bạn." (28px, bold). Below: 2-column grid of 4 PromptCards (52px min-height, 1px border, hover: 1px --purple + --purple-light bg). "Đổi gợi ý" link below grid.
  - User message: right-aligned bubble, --purple-light bg, --ink text, 80% max-width, 12px radius, 12px padding
  - System message block: full-width, --surface bg, 1px --border top/bottom, no bubble, 16px padding
  - StreamingStatusText: --muted color, left-aligned, italic-style (use --muted text, not italic font)
  - DiagnosisRow: ✕ (--danger) or ✓ (--success) marker + bold finding text + benchmark data + fix recommendation. First ✕ has 2px --purple left border.
  - HookRankingBar: label + bar (full-width container, bar fills %) + multiplier in JetBrains Mono right-aligned. Top bar --purple, others --border-active.
  - BriefBlock: --surface-alt bg, 1px --border, 12px radius, sections separated by 1px border within block.
  - CreatorCard: 1px --border, 12px radius, handle (@bold) + stats row (followers, likes in JetBrains Mono) + contact info + "Có data" purple badge if applicable.
  - ThumbnailStrip: horizontal scroll container, 2.5 thumbnails visible, each 120px wide, 9:14 aspect, 12px radius
  - CorpusCite: small --faint text in JetBrains Mono: "412 video · 7 ngày · Updated 4h ago"
  - CopyButton (mobile): full-width, --surface bg, 1px --border, 48px height, "Copy kết quả" text + copy icon. After copy: "Đã copy ✓" for 2s, bg flash --purple-light.
  - FreeQueryPill: small pill "Miễn phí ✓" next to user bubble, --purple text on --purple-light bg, appears and fades after 2s.
- CreditBar (fixed above input): full-width, 48px height, --surface bg, 1px --border top. JetBrains Mono: "{{count}} deep credits còn lại · Lướt xu hướng & tìm KOL không giới hạn". When zero: --purple bg, white text "Hết credit. Mua thêm →" (tappable).
- Input area (fixed bottom): URLChip (above input, purple left border, when URL detected), auto-grow textarea (1-3 lines, 1px --border, 12px radius, 16px font), char counter (JetBrains Mono --faint right-aligned), send button (44×44px, --faint bg when empty → --purple bg when has text).
- Bottom navigation: 3 tabs — Chat (bubble icon, active), Xu hướng (trending icon), Lịch sử (clock icon)
- Mock data: Show 3 messages in a diagnosis session. User: "Tại sao video này chỉ 2000 view? [TikTok URL]". System: StreamingStatusText "Đang xem video của bạn..." → then diagnosis with 3 DiagnosisRows: ✕ "Không mặt trong 3 giây đầu — 92% top video trong niche mở bằng mặt. Fix: Quay lại, mở bằng mặt nhìn camera trong 0.5 giây đầu." ✕ "Text overlay xuất hiện ở giây 3.2 — top video: 0.8 giây. Fix: Chuyển text lên frame đầu tiên." ✓ "Hook 'Cảnh Báo' — đúng pattern. Trung bình 3.2x views so với 'Kể Chuyện'." CorpusCite: "412 video review đồ gia dụng · 7 ngày · Updated 4h ago". ThumbnailStrip: 4 thumbnail cards.

[TrendScreen — route: /app/trends]:
- Header (fixed top): "Xu hướng" title center + settings icon right
- NicheSelector: horizontal scrollable chip row. Current niche chip has --purple bg + white text. Others: --surface bg, 1px --border. Chips: "Review đồ gia dụng", "Làm đẹp", "Shopee", "Đồ ăn", "Hài", "Công nghệ", "Mẹ bỉm sữa"
- HookRankingSection: heading "Hook đang chạy trong Review đồ gia dụng" + CorpusCite + 5 HookRankingBars. Mock data: "Cảnh Báo 3.2x", "Giá Sốc 2.4x", "Phản Ứng 1.9x", "Con Số Cụ Thể 1.7x", "Kể Chuyện 1.0x"
- FormatLifecycleSection: "Format đang lên" list (3 items) + "Format đang giảm" list (2 items)
- TrendingKeywordSection: keyword chips with usage count in JetBrains Mono
- ThumbnailStrip: top 5 reference videos for the week
- CreditBar (same as ChatScreen)
- Bottom navigation (same as ChatScreen, Xu hướng tab active)

[HistoryScreen — route: /app/history]:
- Header (fixed top): "Lịch sử" title center + settings icon right
- SearchBar: full-width input "Tìm trong lịch sử..." (1px --border, 8px radius)
- SessionList: scrollable. Group by date: "Hôm nay", "Hôm qua", date headings in --faint text. 
  - SessionItem: IntentBadge (small --purple-light + --purple text pill) + first query text (truncated 2 lines, --ink) + date/time (--faint JetBrains Mono right) + "−{{N}} credit" (--muted JetBrains Mono right)
- Mock data: 6 sessions. "Hôm nay": "Tại sao video review nồi chiên không dầu chỉ 2.000 view?" (Soi Video, today 8:14, −1 credit), "Hook nào đang hot trong review đồ gia dụng?" (Xu hướng, today 7:52, miễn phí). "Hôm qua": 2 items. Earlier: 2 items.
- Empty state (if no history): "Chưa có phiên nào. Dán link TikTok hoặc hỏi câu đầu tiên để bắt đầu."
- CreditBar (same as ChatScreen)
- Bottom navigation (same, Lịch sử tab active)

[PricingScreen — route: /app/pricing]:
- Header: back arrow left + "Chọn gói phù hợp" title center
- BillingToggle: 3-segment control "Tháng | 6 tháng | Năm" with "Tiết kiệm nhất" badge on Năm option. Năm pre-selected.
- PricingCards: vertical stack on mobile (horizontal 3-col on desktop). 4 cards. Card prices change based on BillingToggle selection:
  - Free: "Dùng thử" / "Miễn phí" / "10 lần phân tích sâu (lifetime)" / features list / "Bắt đầu miễn phí" button (outlined) — price unchanged across all billing periods
  - Starter: "Starter" / prices: Tháng→249.000đ, 6 tháng→219.000đ, Năm→199.000đ (per month) / "30 lần phân tích sâu/tháng + lướt xu hướng không giới hạn" / "Phổ biến nhất" badge / "Nâng cấp Starter" CTA (--purple bg)
  - Pro: "Pro" / prices: Tháng→499.000đ, 6 tháng→449.000đ, Năm→399.000đ (per month) / "80 lần phân tích sâu/tháng + không giới hạn browse" / "Nâng cấp Pro" CTA
  - Agency: "Agency" / prices: Tháng→1.490.000đ, 6 tháng→1.350.000đ, Năm→1.190.000đ (per month) / "250 lần phân tích sâu + 10 tài khoản" / "Nâng cấp Agency" CTA
  - Default shown in Make: Năm (annual) pre-selected
- SavingsCallout below cards: text changes per toggle: Tháng→(hidden), 6 tháng→"Tiết kiệm 180.000đ – 840.000đ khi mua 6 tháng", Năm→"Tiết kiệm 600.000đ – 3.600.000đ khi mua cả năm"
- OverageSection: heading "Mua thêm credits" + 2 cards side-by-side: "10 credits — 130.000đ" and "50 credits — 600.000đ (12.000đ/lần)"
- PaymentMethodRow: horizontal row of payment icons: MoMo, VNPay, bank icon, Visa/Mastercard
- CreditBar

[CheckoutScreen — route: /app/checkout]:
- Header: back arrow + "Thanh toán" title
- OrderSummary card: plan name + billing period + amount. "Starter · Thanh toán năm · 2.388.000đ"
- PaymentMethodSelector: radio group with 4 options (icons + labels): MoMo, VNPay, Chuyển khoản ngân hàng, Thẻ quốc tế
- PaymentContent area (changes based on selection):
  - MoMo: QR code (200×200px placeholder square) + "Mở app MoMo → Quét mã → Xác nhận" instruction
  - Bank: bank name + account number + account name + reference code (JetBrains Mono for all numbers). "Vietcombank · 1234567890 · GETVIEWS VN · Nội dung: GV-2026-0408-XXXXXX"
  - Card: card number input + expiry + CVV row
- ConfirmButton: "Xác nhận thanh toán" (--purple bg, full-width, 48px)
- CreditBar

[PaymentSuccessScreen — route: /app/payment-success]:
- Centered layout, vertical stack
- Icon: simple checkmark circle (--success color, no animation, no confetti)
- Heading: "Đã thêm 30 deep credits." (bold, large)
- Subtext: "Gói Starter đã kích hoạt. Credits có hiệu lực đến 08/04/2027."
- Large credit balance display: "30" in JetBrains Mono (large, --purple color) with label "deep credits còn lại" below in --muted
- CTA button: "Bắt đầu phân tích ngay" (--purple bg, full-width, 48px)

[SettingsScreen — route: /app/settings]:
- Header: back arrow + "Tài khoản" title
- ProfileSection: Initial-letter avatar (48×48px circle, --purple bg, white letter) + display_name bold + email --muted
- SubscriptionSection: section heading + current plan badge + credit count (JetBrains Mono) + expiry date + "Nâng cấp" button (--purple, small)
- NicheSection: section heading + niche chip display + "Thay đổi" text link
- CreditHistoryList: section heading + list of 5 events (intent badge + date + "−1 credit" in --muted JetBrains Mono)
- LogoutButton: full-width, --surface bg, 1px --border, --danger text "Đăng xuất"
- Mock data: Display name "Nguyễn Minh", niche "Review đồ gia dụng", Starter plan, 27 credits remaining, expiry 01/05/2026

BEHAVIOR:
- Bottom navigation bar on all /app/* screens with 3 tabs: Chat, Xu hướng, Lịch sử
- Active tab: icon + label in --purple
- All screens scroll vertically, no horizontal scroll (except ThumbnailStrip and NicheSelector)
- Back navigation via header back arrow on non-tab screens
- Forms validate on blur + submit
- ChatInput: auto-grows from 1 to 3 lines max (mobile). Fixed to bottom of screen.
- CreditBar: fixed above ChatInput on ChatScreen. Visible on all /app/* screens above bottom nav.
- NicheSelector on TrendScreen: horizontal scroll with touch momentum

CONSTRAINTS:
- Vietnamese language for ALL UI copy — use realistic Vietnamese mock data, not lorem ipsum
- Mock data must use realistic Vietnamese: names like "Nguyễn Minh", niches like "Review đồ gia dụng", handles like "@minhreview"
- Include 3–5 items in every list to test visual density (3 DiagnosisRows, 5 HookRankingBars, 4 CreatorCards, 6 SessionItems)
- Credit prices exact: Starter 249K/mo (199K annual), Pro 499K/mo (399K annual), Agency 1.49M/mo (1.19M annual), overage 10cr=130K, 50cr=600K
- Use Radix UI for all interactive components (Dialog, Accordion, RadioGroup, Tabs)
- Generate separate files per screen — do NOT put everything in App.tsx
- JetBrains Mono for ALL numerical data: credit counts, view counts, follower counts, multipliers, corpus sizes, timestamps
- TikTok Sans for all other text (or system sans-serif as fallback if TikTok Sans unavailable in Make)
- No gradient backgrounds anywhere — flat oklch colors only
- No shadows — 1px borders only
- Mobile-first: 375px baseline, 12px side padding
```

---

## Revision Prompts

Use these after reviewing Make's first output. Budget 10–15 revision prompts max.

### Revision 1 — Strengthen diagnosis animations
```
TARGET: ChatScreen — DiagnosisRow section
CHANGE: Add Framer Motion stagger animation to DiagnosisRows. Each row slides in from left (translateX -12px → 0) with opacity 0→1, 150ms each, 150ms stagger between rows. ✕ rows first, ✓ last. First ✕ row must have 2px left border in --purple color.
MAINTAIN: All other chat components, colors, spacing, CreditBar, input area, PromptCards, mock data — unchanged.
```

### Revision 2 — Hook ranking bar animation
```
TARGET: TrendScreen — HookRankingBars
CHANGE: Animate bars with Framer Motion. Width animates from 0% to final value using cubic-bezier(0.16, 1, 0.3, 1) over 400ms, with 100ms stagger between bars. Top bar (Cảnh Báo) is --purple, others are --border-active (progressively lighter if possible). Multiplier number ("3.2x") fades in after bar animation completes.
MAINTAIN: NicheSelector, layout, CorpusCite, FormatLifecycleSection, ThumbnailStrip — all unchanged.
```

### Revision 3 — CreditBar states
```
TARGET: ChatScreen — CreditBar
CHANGE: Create 3 states for CreditBar. (1) Normal: --surface bg, 1px --border-top, JetBrains Mono text "27 deep credits còn lại · Lướt xu hướng & tìm KOL không giới hạn". (2) Low (≤5 credits): "⚠ 3 deep credits còn lại" in --danger color. (3) Zero: full-width --purple bg, white text "Hết credit. Mua thêm →" with right arrow, tappable. Show state (3) in the mockup by default.
MAINTAIN: Everything else in ChatScreen including messages, input, header, bottom nav.
```

### Revision 4 — ThumbnailStrip horizontal scroll
```
TARGET: ChatScreen — ThumbnailStrip below DiagnosisRows
CHANGE: Show 2.5 thumbnails in viewport to signal swipeability. Each thumbnail: 120px wide, 9:14 aspect ratio (so height is ~187px), 12px border-radius. Show handle + view count overlay at bottom of each thumbnail in white text on dark gradient overlay. Add touch-scroll behavior.
MAINTAIN: All other chat message components, DiagnosisRows, CreditBar, input area.
```

### Revision 5 — FreeQueryPill
```
TARGET: ChatScreen — user message for free queries
CHANGE: Add "Miễn phí ✓" pill next to user message bubbles that are free (⑥⑦ intents or follow-ups). Pill: small rounded pill shape, --purple text on --purple-light bg, 8px horizontal padding, 4px vertical padding, 12px font. Appears inline immediately after message bubble sends. In mock data, add one "Xu hướng tuần này?" user message with this pill visible.
MAINTAIN: All other message bubble styles, DiagnosisRows, header, input area.
```

### Revision 6 — Mobile pricing cards
```
TARGET: PricingScreen — PricingCards on mobile
CHANGE: Stack all 4 cards vertically (single column) on 375px viewport. Each card full-width. Starter card has a subtle 2px --purple border (not shadow) to highlight. "Phổ biến nhất" badge positioned as an absolute top-right chip on the Starter card. Annual savings amount displayed in --purple color below price.
MAINTAIN: BillingToggle, OverageSection, PaymentMethodRow — all unchanged.
```

### Revision 7 — BottomNav active states
```
TARGET: All /app/* screens — BottomNav
CHANGE: Active tab: icon + label both in --purple color. Inactive tabs: icon + label in --muted. Tab item min-height: 56px (including safe area padding at bottom). Add hairline 1px --border-top to BottomNav container.
MAINTAIN: Tab labels (Chat, Xu hướng, Lịch sử), icons, routing behavior.
```

---

## Mock Data Guidance

Make will generate mock data. Structure to match real schema:

```typescript
// User profile
const mockProfile = {
  display_name: "Nguyễn Minh",
  primary_niche: "Review đồ gia dụng",
  deep_credits_remaining: 27,
  subscription_tier: "starter",
  credits_reset_at: "2026-05-01"
};

// Chat session messages
const mockMessages = [
  { 
    role: "user", 
    content: "Tại sao video này chỉ 2.000 view? https://www.tiktok.com/@minhreview/video/7123456789",
    intent_type: "video_diagnosis",
    credits_used: 1
  },
  {
    role: "assistant",
    content: null, // structured content
    diagnosis_rows: [
      { type: "fail", finding: "Không mặt trong 3 giây đầu", benchmark: "92% top video trong niche mở bằng mặt trong 0.5 giây đầu", fix: "Quay lại mở bằng mặt nhìn camera trong 0.5 giây đầu" },
      { type: "fail", finding: "Text overlay ở giây 3.2", benchmark: "Top video: text xuất hiện trước giây 1", fix: "Chuyển text lên frame đầu tiên" },
      { type: "pass", finding: "Hook 'Cảnh Báo' đúng pattern", benchmark: "Trung bình 3.2x views so với 'Kể Chuyện' trong niche" }
    ],
    corpus_cite: { count: 412, niche: "review đồ gia dụng", timeframe: "7 ngày", updated_hours_ago: 4 },
    thumbnails: [
      { handle: "@topniche1", views: "1.2M", url: "https://tiktok.com/..." },
      { handle: "@topniche2", views: "890K", url: "https://tiktok.com/..." },
      { handle: "@topniche3", views: "450K", url: "https://tiktok.com/..." }
    ]
  }
];

// Hook rankings for TrendScreen
const mockHookRankings = [
  { hook_name: "Cảnh Báo", multiplier: 3.2, percentage: 100 },
  { hook_name: "Giá Sốc", multiplier: 2.4, percentage: 75 },
  { hook_name: "Phản Ứng", multiplier: 1.9, percentage: 59 },
  { hook_name: "Con Số Cụ Thể", multiplier: 1.7, percentage: 53 },
  { hook_name: "Kể Chuyện", multiplier: 1.0, percentage: 31 }
];

// History sessions
const mockSessions = [
  { id: "s1", first_message: "Tại sao video review nồi chiên không dầu chỉ 2.000 view?", intent_type: "video_diagnosis", created_at: "2026-04-08T08:14:00", credits_used: 1 },
  { id: "s2", first_message: "Hook nào đang hot trong review đồ gia dụng tuần này?", intent_type: "trend_spike", created_at: "2026-04-08T07:52:00", credits_used: 0 },
  { id: "s3", first_message: "Soi kênh @reviewer_top1 — họ đang làm gì?", intent_type: "competitor_profile", created_at: "2026-04-07T15:30:00", credits_used: 1 },
  { id: "s4", first_message: "Viết brief cho KOL quay video nồi chiên không dầu", intent_type: "brief_generation", created_at: "2026-04-07T10:15:00", credits_used: 1 }
];

// Creator cards (Find Creators)
const mockCreators = [
  { handle: "@linhthuyskincare", followers: "4.2K", total_likes: "89K", contact: "zl: 0912345678", has_corpus_data: true },
  { handle: "@beautyvn_hana", followers: "2.8K", total_likes: "51K", contact: "ig: beautyvn_hana", has_corpus_data: false },
  { handle: "@skincare.thaovy", followers: "1.9K", total_likes: "34K", contact: "email: thaovy@gmail.com", has_corpus_data: true }
];
```

---

## Build Order

Match northstar §17 Feature Grouping:

**Wave 1 — Foundation (build in this order):**
1. LandingPage — validates theme tokens immediately
2. LoginScreen + OnboardingScreen — unblocks all auth-gated screens
3. ChatScreen — core product, highest priority fidelity
4. TrendScreen — second highest usage

**Wave 2 — Complete App:**
5. HistoryScreen
6. PricingScreen
7. CheckoutScreen + PaymentSuccessScreen
8. SettingsScreen

**Figma Make prompt order:** Start with ChatScreen prompt first (highest complexity, highest stakes). Then landing page. Then the rest.

---

## Prompt Budget

- First prompt (structural, all 10 screens): 1 prompt — get this right
- Dopamine animations (D1, D2): 2 prompts
- CreditBar states: 1 prompt
- ThumbnailStrip: 1 prompt
- FreeQueryPill: 1 prompt
- PricingScreen mobile: 1 prompt
- BottomNav: 1 prompt
- Visual polish (use Point and Edit tool for these — free): spacing tweaks, color adjustments, border radius corrections
- **Target: ≤10 prompts total**

---

## Quality Check

Before handing off to Frontend Developer, verify Make output has:

- [ ] All 10 screens in separate files under `screens/`
- [ ] ChatScreen shows all 4 dopamine moment component types (DiagnosisRow, HookRankingBar, BriefBlock, CreatorCard)
- [ ] ThumbnailStrip horizontal scroll visible with 2.5 thumbnails
- [ ] CreditBar persistent and visible on all /app/* screens
- [ ] FreeQueryPill visible next to at least one user message
- [ ] No gradient backgrounds anywhere
- [ ] No shadows — 1px borders only
- [ ] All numbers (follower counts, credit counts, multipliers) in JetBrains Mono
- [ ] Vietnamese copy throughout — no English placeholders or lorem ipsum
- [ ] Bottom navigation 3 tabs, active state in --purple
- [ ] Mobile layout: 375px, 12px side padding
- [ ] PromptCards 2-column grid in ChatScreen empty state
- [ ] Niche chip selector horizontal scroll in TrendScreen
- [ ] Billing period toggle on PricingScreen with annual pre-selected
- [ ] PayOS payment options visible in CheckoutScreen (QR code placeholder + bank details + card form)
