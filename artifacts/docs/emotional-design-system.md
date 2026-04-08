# Emotional Design System — GetViews
**Version:** 1.1 — April 2026

---

## 1. Core Emotional Thesis

GetViews exists to transform **Minh** (a Vietnamese TikTok creator earning from Shopee affiliate commissions) from *anxious guessing — posting videos hoping for views, not knowing why content flops, doomscrolling for 2 hours every morning pretending it's "research"* — to **informed certainty: knowing exactly what to film, why it will work, and what the data says right now.** The primary feeling we create is **competence** — the feeling of being the smartest creator in the room, not because of talent, but because of intelligence. Delivered through real video analysis grounded in 46,000+ analyzed Vietnamese TikTok videos that no course, no guru, and no amount of scrolling can replicate.

The persona is not a tool. The persona is **the expert you wish you had on speed dial** — the TikTok strategist who charges 5 triệu per session but you get 24/7 access for 249K/month. They don't guess. They show you the data. They don't motivate. They tell you exactly what's wrong and exactly how to fix it.

---

## 2. Emotional Layers (Priority Order)

When two layers conflict in a design decision, higher priority wins.

1. **Clarity** — The user knows exactly what to do next. Every response ends with a specific, actionable recommendation. No "nên cân nhắc" (should consider). Only "quay lại video với hook Cảnh Báo, mở bằng mặt, text trong 0.5 giây đầu."
2. **Authority** — Every claim is backed by a number from real data. "Dựa trên 412 video tháng này" is not a decoration — it's the sentence that separates GetViews from ChatGPT. If we can't cite a number, we don't make the claim.
3. **Speed** — The user gets their answer before they finish their coffee. 30 seconds for a diagnosis. 2 minutes for a brief. Time saved is the most tangible value for a creator who posts daily.
4. **Respect** — The user is a working creator, not a student. We don't teach — we inform. We don't motivate — we equip. The tone is peer-to-peer expert, not teacher-to-student.

---

## 3. Primary User Persona

**Minh, 24, Shopee affiliate creator in Ho Chi Minh City.**

**Core identity:** Minh sees himself as an entrepreneur, not a content creator. He doesn't love making videos — he loves making money from videos. He measures success in commission VND, not follower count.

**Daily context:** 7 AM, sitting on his bed with coffee, phone in hand. He posted a video last night reviewing a kitchen gadget. 2,000 views. His usual is 10K+. Commission from yesterday: 45K VND instead of the usual 200K. He opens TikTok to "research" — 2 hours later he's still scrolling, no closer to knowing what to film today. He has 3 products from Shopee waiting to be reviewed. He doesn't know which hook to use. He doesn't know why yesterday's video flopped. He doesn't even know if "review đồ gia dụng" is still working this week.

**What he notices:** Speed. If the answer takes more than 30 seconds, it's too slow. Specificity. "Mở bằng mặt, text trong 0.5 giây đầu" is useful. "Nên cải thiện phần mở đầu" is useless. Real videos he can tap and watch — proof, not opinion.

**What he shares:** Screenshots of diagnosis results in his Zalo creator group. "Thấy chưa — hook Cảnh Báo đang 3.2x views hơn Kể Chuyện." He shares data that makes him look smart.

**What breaks trust:** Generic advice he could get from ChatGPT. Responses that don't mention his specific niche. Numbers that feel made up. Responses in robotic Vietnamese. Being told to "thử nhiều cách khác nhau" (try different approaches) — he needs ONE approach, backed by data.

**Primary device:** Phone. 360-393px screen. One-handed use. Vietnamese Telex keyboard. Browses at 7 AM in bed, at lunch between shoots, at 10 PM reviewing the day's performance.

---

## 4. Design Principles

1. **Show the evidence before the recommendation.** Data first, then advice. "412 video trong niche này tháng này → 92% mở bằng mặt → video của bạn không có mặt" — the conclusion writes itself.
2. **Name the specific fix, not the general category.** Wrong: "Cần cải thiện hook." Right: "Đổi hook thành 'ĐỪNG MUA [sản phẩm] nếu chưa xem video này' + mở bằng mặt nhìn camera trong 0.5 giây đầu."
3. **Include a tappable reference for every claim.** Every corpus-backed statement includes a thumbnail card the user can tap to see the actual TikTok video. The evidence is one tap away. This is the opposite of guru culture.
4. **Finish with the next action, not a summary.** Last line of every response is what Minh should do in the next 10 minutes. Not "Tóm lại..." — instead "Quay lại video hôm nay: hook Cảnh Báo + mặt + text 0.5s. Đây là 3 video mẫu."
5. **Treat credits like the user's money — because they are.** Never waste a deep credit on something that could be answered with a free follow-up. If the user asks a clarifying question, don't charge. If they ask for a new analysis, charge. Intent detection is conservative: ambiguous = free.
6. **Stay quiet after delivering a big result.** No upsell after diagnosis. No "Bạn cũng có thể thử..." after a brief. Let the result breathe. The user needs 10 seconds to absorb before the next prompt.

---

## 5. Visual Direction

### Brand Colors
| Role | Name | OKLCH | Hex | Usage |
|---|---|---|---|---|
| Primary/Accent | TikTok Purple | oklch(0.53 0.26 295) | #7C3AED | Send button, active states, gradient text, card hover |
| Primary Dark | Purple Deep | oklch(0.45 0.28 295) | #6D28D9 | Hover on purple elements |
| Primary Light | Purple Tint | oklch(0.95 0.03 295) | #F3F0FF | Active sidebar bg, card hover bg |
| Background | Light Gray | oklch(0.93 0.00 0) | #EDEDEE | Page background |
| Surface | White | oklch(1.00 0.00 0) | #FFFFFF | Cards, input fields, sidebar |
| Surface Alt | Warm Gray | oklch(0.97 0.00 0) | #F7F7F8 | Mode badges, secondary surfaces |
| Foreground | Ink | oklch(0.15 0.00 0) | #18181B | Primary text, headings |
| Foreground 2 | Ink Soft | oklch(0.30 0.00 0) | #3F3F46 | Body text, card text |
| Muted | Gray | oklch(0.55 0.00 0) | #71717A | Secondary text, icons |
| Faint | Light Muted | oklch(0.68 0.00 0) | #A1A1AA | Placeholder text, disabled |
| Border | Light Border | oklch(0.90 0.00 0) | #E4E4E7 | Default borders, dividers |
| Border Active | Medium Border | oklch(0.85 0.00 0) | #D4D4D8 | Hover borders |

### Semantic Colors
| Role | OKLCH | Hex | Usage |
|---|---|---|---|
| Brand Mark | oklch(0.60 0.28 15) | #FE2C55 | Logo mark only. TikTok Red identity. |
| Success / Good | oklch(0.60 0.18 145) | #25F4EE | ✓ markers in diagnosis, positive signals |
| Danger / Bad | oklch(0.55 0.22 25) | #D93B3B | ✕ markers in diagnosis, error states, low credit warning |
| Data Highlight | oklch(0.53 0.26 295) | #7C3AED | Data numbers in JetBrains Mono |

### Visual Register
- **Flat-minimal-professional** — no shadows, no gradients (except heading text), no decorative elements. Borders are 1px, colors are neutral except purple accent. The aesthetic says "tool that works" not "app that entertains."
- **In a flat UI, every state change IS the design.** Transitions, micro-interactions, and feedback replace visual chrome as the primary UX mechanism. See §5a Interaction System below.

### Typography Direction
- **Primary:** TikTok Sans — Vietnamese diacritic support native. The typeface creators see 100 min/day.
- **Data/Mono:** JetBrains Mono — statistics, credit counts, timestamps, multipliers. Signals precision.
- **Heading weight:** 800 (extra bold). Body: 400/500. Weight contrast creates hierarchy without color or size variation.
- **Mobile body:** 16px minimum (prevents iOS auto-zoom on input focus). Desktop body: 15px.

### Iconography
- Minimal stroke icons, 1.8px stroke weight, round linecap. Consistent with sidebar and prompt card icons.
- No emoji in UI chrome. No filled icons. No illustrations.
- Icons are functional, not decorative — every icon is a tappable affordance.

### Dark Mode
- No — v1 is light mode only. Revisit in v2.

---

## 5a. Interaction System

In a flat UI with no shadows and 1px borders, **transitions and state changes carry the entire UX weight.** Every interactive element must provide clear feedback through color, opacity, and motion — not through depth or elevation.

### Global Timing System

All transitions in the product use these tiers. No custom durations — consistency is how flat UI feels cohesive.

| Tier | Duration | Easing | Use |
|---|---|---|---|
| **Instant** | 0ms | — | Checkbox toggle, radio select, active press color |
| **Fast** | 120ms | `ease-out` | Hover bg tint, border color, icon color, focus ring |
| **Normal** | 200ms | `ease-out` | Card expand, panel slide, tab switch, tooltip appear |
| **Emphasis** | 400ms | `cubic-bezier(0.16, 1, 0.3, 1)` | Diagnosis row reveal, bar chart fill, card stack stagger |
| **Slow** | 600–800ms | `cubic-bezier(0.16, 1, 0.3, 1)` | Full dopamine moments only (D1–D4). Reserved. |

**Hard rule: nothing in the product takes >800ms.** If it feels slow, the system is broken, not the animation.

### Element State Specifications

#### Input Field
| State | Border | Background | Text | Transition |
|---|---|---|---|---|
| Default | 1px `--border` | `--surface` | — | — |
| Hover | 1px `--border-active` | `--surface` | — | Fast (120ms) |
| Focus | 1px `--purple` | `--surface` | caret visible | Fast (120ms) |
| Filled | same as Focus | `--surface` | `--ink` | — |
| Disabled | 1px `--border` | `--surface-alt` | `--faint` | — |
| Error | 1px `--danger` | `--surface` | error text `--danger` below | Fast (120ms) |

#### Send Button
| State | Visual | Transition |
|---|---|---|
| Default (empty input) | bg `--faint`, not clickable, cursor default | — |
| Active (has input) | bg `--purple`, cursor pointer | Fast (120ms) bg change |
| Hover | bg `--purple-dark` | Fast (120ms) |
| Pressed | scale 0.95 | 80ms `ease-out` |
| Sending | Replace with 16px stroke spinner (`--purple`), button disabled | Instant swap |
| Sent | Return to Default state | Fast (120ms) |

#### Prompt Cards
| State | Border | Background | Transition |
|---|---|---|---|
| Default | 1px `--border` | `--surface` | — |
| Hover | 1px `--purple` | `--purple-light` | Fast (120ms) |
| Pressed | 1px `--purple` | `--purple-light`, scale 0.98 | 80ms `ease-out` |
| After tap | Card text populates input field. All cards fade out (opacity 0, 150ms). Input auto-focuses. | Normal (200ms) |

#### Sidebar Icon Buttons
| State | Background | Icon color | Transition |
|---|---|---|---|
| Default | transparent | `--muted` | — |
| Hover | `--surface-alt` | `--ink` | Fast (120ms) |
| Active (current page) | `--purple-light` | `--purple` | — |
| Pressed | `--surface-alt`, scale 0.95 | `--ink` | 80ms |

#### Copy/Share Buttons (in chat responses)
| State | Visual | Transition |
|---|---|---|
| Default | text "Copy" + icon, color `--muted` | — |
| Hover | color `--ink` | Fast (120ms) |
| Pressed | scale 0.95 | 80ms |
| Success | text changes "Đã copy ✓", bg flash `--purple-light` 200ms, then fade back. Text reverts after 2s. | Normal (200ms) |

### Touch Targets (Mobile)

Minh uses this one-handed on a 360–393px phone screen. Every tappable element must meet minimum touch standards.

| Element | Visual size | Tap target | Notes |
|---|---|---|---|
| Send button | 44×44px | 44×44px | Increased from 32px. Non-negotiable. |
| Sidebar icons | 40×40px | 44×44px | 2px invisible padding extends tap area |
| Prompt cards | Full card | Full card | min-height 52px on mobile |
| Copy/Share button | Text + icon | 44px height, full width | Extend tap zone with padding |
| Thumbnail reference cards | 120×168px | Full card | Opens TikTok URL on tap |
| Mode badge (niche selector) | Text badge | 44px height | Padding extends tap zone |
| Input field | Full width | 48px min-height on mobile | 16px font prevents iOS zoom |

**Gap between tappable elements:** minimum 8px. No two tap zones may overlap.

---

## 5b. Streaming Behavior

Streaming is the #1 UX in a chat product. This section is mandatory for implementation — it replaces traditional loading patterns.

### Token Streaming
- Each text token fades in: opacity 0→1, 60ms. No cursor blink animation — just text appearing naturally.
- Streaming text uses the same font/color as final text. No "draft" styling.

### Auto-Scroll
- Chat auto-scrolls as tokens stream, pinned to bottom.
- If user scrolls UP manually during stream → auto-scroll pauses. A "↓ Cuộn xuống" pill appears at bottom.
- When user taps pill or scrolls back to bottom → auto-scroll resumes.

### Structured Content in Stream
**Critical distinction:** Plain text streams token-by-token. Structured UI elements (✕/✓ diagnosis rows, hook ranking bars, brief blocks, creator cards, thumbnail cards) appear as **complete units**, never token-by-token.

Implementation: Buffer structured content during stream. When a full block is ready → reveal with the appropriate dopamine animation (D1/D2/D3/D4). This means the user sees flowing text → then a polished data card pops in → then more flowing text. The contrast between streaming text and finished UI elements creates a sense of quality.

### Stream Interruption
- User can type and send a new message while stream is active.
- Current stream truncates: append "..." at cut point.
- New query starts immediately. No "please wait" modal. No blocking.

### Stream Error
- If Gemini drops mid-stream (503, timeout, network):
  - Append at the cut point: "— Bị gián đoạn. Gõ 'tiếp' để tiếp tục." (inline, not modal)
  - User types "tiếp" → system replays from last complete sentence with the same session context.
  - No page reload. No lost context. No error modal.

### Loading States (pre-stream)
Before tokens start flowing, show streaming status text that describes what GetViews is doing:

| Intent | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| ① Video Diagnosis | "Đang tải video..." | "Đang xem video của bạn..." | "Đang so sánh với {{count}} video trong niche..." |
| ② Content Directions | "Đang tìm xu hướng..." | "Đang phân tích {{count}} video..." | — |
| ③ Competitor Profile | "Đang tải video của @{{handle}}..." | "Đang phân tích 3 video gần nhất..." | — |
| ④ Soi Kênh | "Đang tải {{count}} video..." | "Đang phân tích patterns..." | "Đang so sánh với niche norms..." |
| ⑤ Brief Generation | "Đang viết brief..." | — | — |
| ⑥ Trend Spike | (instant — pre-computed) | — | — |
| ⑦ Find Creators | "Đang tìm KOL..." | — | — |

Status text transitions: each phase fades in (opacity 0→1, 200ms), previous phase fades out. Not a progress bar — just evolving text that shows the system is working.

---

## 5c. Keyboard & Input Behavior

### URL Paste Detection
- When user pastes a TikTok URL → auto-detect via regex (`tiktok.com/@.+/video/\d+` or `vm.tiktok.com/.+`).
- Show URL preview chip above input: parsed handle + "Video" label. Purple left border.
- Intent pre-classified as ①/③/④ before user hits send.
- If URL is invalid or not TikTok → chip shows "Link không hợp lệ — cần link TikTok" in `--danger` color. Send still enabled (user may want to ask a text question).

### Vietnamese IME Handling
- Vietnamese Telex/VNI input creates intermediate characters (e.g., typing "aw" → "ă", "dd" → "đ").
- **Do not trigger intent detection or URL parsing on intermediate keystrokes.** Only process on explicit send (button tap or Enter key).
- Do not auto-correct or modify Vietnamese text. The user's input is authoritative.

### Multi-line Input
- Textarea auto-grows: 1 line default → max 3 lines on mobile, max 5 lines on desktop → then internal scroll.
- Shift+Enter for new line. Enter alone sends (desktop). On mobile, Enter adds new line (send via button only).

### Character Limit
- 1000 character limit. Counter shows `{{current}}/1000` in `--faint` JetBrains Mono.
- At 900+ chars: counter changes to `--danger` color.
- At 1000: input stops accepting characters. Counter shows "1000/1000" in `--danger`.
- If user pastes text >1000 chars: truncate silently, show "Đã cắt — giới hạn 1000 ký tự" below input for 3s.

---

## 5d. Mobile Layout

Minh's primary device is a phone (360–393px). The desktop layout (centered 720px) is for Linh's agency workflow. Mobile is the default design target.

### Chat Screen (mobile)
- **Full-width** — 12px side padding. No centered max-width on mobile.
- **Input fixed to bottom** — always visible, does not scroll with chat history. 12px bottom padding (safe area for gesture bar).
- **Messages** — full-width bubbles. User messages: right-aligned, `--purple-light` bg. System messages: left-aligned, `--surface` bg.
- **Structured output blocks** (diagnosis, brief, creator cards): full-width, no bubble styling. White bg, 1px `--border` top/bottom as separators.

### Prompt Cards (mobile)
- 2-column grid on 360–768px. Single column on <360px (rare).
- min-height 52px (reduced from desktop 130px). Text truncates at 2 lines with ellipsis.
- "Đổi gợi ý" button below cards.

### Thumbnail Reference Cards (mobile)
- **Horizontal scroll strip** — not vertical stack. Swipeable left/right.
- Each thumbnail: 120px wide, 9:14 aspect ratio, 12px border-radius.
- Show 2.5 thumbnails in viewport → signals there are more to scroll.
- Tap thumbnail → opens TikTok URL in external browser / TikTok app (deep link if installed).

### Brief Output (mobile)
- Full-width blocks. Each section (Hook, Shot Structure, KOL) separated by 1px `--border`.
- **"Copy brief" button sticky at bottom of brief block** — not inline. Full-width, 48px height, `--purple` bg, white text.
- After copy: button changes to "Đã copy ✓ — forward qua Zalo" for 2s.

### Empty State (mobile)
- Greeting text: 28px heading (not 44px desktop). 2 lines max.
- Prompt cards: 2-column.
- Input at bottom, always visible.
- No sidebar — replaced by bottom tab bar or hamburger menu.

---

## 6. Dopamine Moments

### D1 — Diagnosis Reveal
**Screen:** Chat — after user pastes a TikTok URL
**Trigger:** Gemini analysis completes, synthesis starts streaming
**Emotion target:** Competence — "Now I know exactly what went wrong"
**Mechanism:**
- Loading: Streaming status text (see §5b loading table)
- Reveal: ✕/✓ markers appear one at a time with 150ms stagger. Each row slides in from left, opacity 0→1. Red ✕ items appear first (what's wrong), green ✓ last (what's right).
- Highlight: The first ✕ row has a subtle purple-tinted left border (2px) — draws eye to the most important fix.
**Duration:** 800ms total for 3-row stagger
**After this moment:** No upsell. No "Bạn cũng có thể..." The next input prompt waits. Let Minh absorb.

### D2 — Hook Ranking Bars
**Screen:** Chat — trend spike or content directions response
**Trigger:** Niche hook ranking data loads
**Emotion target:** Authority — "This is data I can't get anywhere else"
**Mechanism:**
- Loading: None — data is pre-computed, instant
- Reveal: Horizontal bars animate width from 0% to final value, 400ms `cubic-bezier(0.16, 1, 0.3, 1)`, 100ms stagger between bars. Top bar (highest performing) animates first.
- Highlight: Top bar is purple. Others are progressively lighter gray. The multiplier number (e.g., "3.2x") fades in at the end of bar animation.
**Duration:** 600ms total
**After this moment:** Corpus citation appears below: "412 video · 7 ngày · Updated 4h ago" — reinforces authority.

### D3 — Brief Delivered
**Screen:** Chat — after brief generation completes
**Trigger:** Full brief with hook scripts, shot structure, KOL recommendation streams
**Emotion target:** Relief — "I can forward this to the KOL right now"
**Mechanism:**
- Loading: "Đang viết brief..." streaming text
- Reveal: Brief blocks (Hook Options, Shot Structure, KOL) appear sequentially, each sliding in with 200ms delay. Each block has a subtle background tint (`--surface-alt`).
- Highlight: "Copy brief" button appears at the end with a subtle scale-in (0.95→1.0, 200ms).
**Duration:** 600ms reveal, button appears 200ms after last block
**After this moment:** No "Bạn muốn chỉnh gì không?" — let Linh copy and forward. She'll come back if she needs changes.

### D4 — Creator Cards Found
**Screen:** Chat — after Find Creators (⑦) query
**Trigger:** ED search returns matching creators
**Emotion target:** Discovery — "I found my next KOL in 10 seconds"
**Mechanism:**
- Loading: "Đang tìm KOL..." text
- Reveal: Creator cards appear in a vertical stack with 100ms stagger. Each card slides in from bottom, opacity 0→1.
- Highlight: Creators with corpus data get a small purple "Có data" badge — signals deeper analysis is available.
**Duration:** 500ms for 5-card stack
**After this moment:** Natural prompt: user taps a creator → "Phân tích @handle chi tiết hơn" (triggers ③, costs 1 deep credit).

### D5 — Credit Consumption Feedback
**Screen:** Credit bar (persistent at bottom of chat)
**Trigger:** A deep credit is consumed (intents ①–⑤)
**Emotion target:** Awareness — "I know I was charged, it's transparent"
**Mechanism:**
- Credit count number pulses: scale 1→1.15→1, 300ms `ease-out`. Color briefly flashes `--danger` then back to `--purple`.
- Number decrements during the pulse animation.
- A small "−1" floats up from the number and fades out (opacity 1→0, translateY 0→-12px, 400ms).
**Duration:** 400ms
**Thresholds:**
- Credits ≤5: bar text changes to `--danger` color, prefix "⚠" added: "⚠ 5 deep credits còn lại"
- Credits = 0: bar becomes a tappable CTA with `--purple` bg: "Hết credit. Mua thêm →"

### D6 — Free Query Confirmation
**Screen:** Chat — inline next to user's message
**Trigger:** A free intent (⑥⑦) or follow-up fires
**Emotion target:** Generosity — "I didn't get charged for this"
**Mechanism:**
- Small "Miễn phí ✓" pill appears next to user's message bubble. Fade-in 150ms.
- Pill fades out after 2s (opacity 1→0, 400ms).
- Color: `--purple` text on `--purple-light` bg. Rounded pill, 10px padding.
**Duration:** 150ms in + 2s hold + 400ms out
**Why this matters:** Reduces credit hoarding. Vietnamese users are price-sensitive — explicitly confirming "this was free" encourages more browsing, which drives engagement, which drives deep credit consumption on insights they discover.

### No-Dopamine Zones
- **Paywall / credit exhaustion:** Flat, transactional. "Hết deep credit tháng này. Mua thêm 10 credit = 130K." No urgency, no FOMO, no countdown.
- **Error states:** Calm, specific. "Video không tải được — TikTok CDN chặn. Thử dán lại hoặc dùng video khác." No emoji. No "Oops."
- **Onboarding niche selection:** Neutral. The user is choosing their niche, not celebrating. Clean dropdown, no animation.
- **Settings / account screens:** Zero animation. Static. These are utility, not experience.

---

## 6a. Share & Export

Linh's #1 output action: forward a brief to a KOL on Zalo. Minh's #1 share action: screenshot diagnosis results to his Zalo creator group. Both actions must be frictionless.

### Copy Button
- Appears at the end of every structured output block (diagnosis summary, brief, creator card list, hook ranking).
- **Desktop:** Text button "Copy" with clipboard icon. Right-aligned below the block.
- **Mobile:** Full-width button, 48px height, `--surface` bg, 1px `--border`. Text: "Copy kết quả".
- Copy feedback: button text → "Đã copy ✓" for 2s, bg flash `--purple-light` 200ms.

### Share Button (mobile only)
- Appears next to Copy button on mobile.
- Triggers Web Share API: `navigator.share({ text: formattedText })`.
- If Share API unavailable → falls back to clipboard copy with toast "Đã copy — dán vào Zalo".
- Share icon: standard iOS/Android share icon (not custom).

### What Gets Copied

| Output type | Copied format |
|---|---|
| Diagnosis | Condensed summary: "✕ Không mặt 3 giây đầu ✕ Text overlay muộn ✓ Hook Cảnh Báo đúng. Dựa trên 412 video." One paragraph, no formatting. |
| Brief | Full structured text: Hook options (numbered), Shot structure (timestamps), KOL tier + budget. Line breaks preserved. No markdown. |
| Hook ranking | "Hook ranking — {{niche}} tuần này: 1. Cảnh Báo 3.2x · 2. Giá Sốc 2.4x · 3. Phản Ứng 1.9x. Dựa trên 412 video." |
| Creator list | "@handle1 · 1.8K followers · email@example.com\n@handle2 · 923 followers · zl: 09xxxxxxx" |

**Rule:** Copied text is plain text optimized for Zalo paste — no HTML, no markdown, no formatting characters. Line breaks only. Vietnamese creators paste into Zalo text input which strips all formatting.

### Screenshot Optimization
- Diagnosis ✕/✓ rows, hook ranking bars, and brief blocks should render cleanly when screenshotted on mobile (iOS screenshot, Android screen capture).
- No content should be cut off at standard screenshot boundaries (393×852px viewport).
- High-contrast text (`--ink` on `--surface`) ensures readability in compressed JPEG screenshots shared on Zalo/Facebook.

---

## 7. Copy Slot Inventory (Partial)

| Context Type | Slot Name | Template | Variables |
|---|---|---|---|
| Diagnosis | diagnosis_pass | "✓ {{finding}} — {{benchmark}}" | finding, benchmark |
| Diagnosis | diagnosis_fail | "✕ {{finding}} — {{benchmark}}. Fix: {{recommendation}}" | finding, benchmark, recommendation |
| Diagnosis | corpus_cite | "Dựa trên {{count}} video {{niche}} {{timeframe}}" | count, niche, timeframe |
| Trend | hook_ranking | "{{hook_name}}: {{multiplier}}x views — {{direction}} trong {{niche}}" | hook_name, multiplier, direction, niche |
| Brief | brief_hook_option | "{{number}}. \"{{hook_text}}\" — {{delivery_note}}" | number, hook_text, delivery_note |
| Brief | brief_kol_suggest | "{{tier}} {{follower_range}} · Est. {{cost_range}} · Commission {{commission_pct}}" | tier, follower_range, cost_range, commission_pct |
| Creator | creator_card | "@{{handle}} · {{followers}} followers · {{total_likes}} likes · {{contact}}" | handle, followers, total_likes, contact |
| Empty | no_niche | "Cho biết niche của bạn để GetViews phân tích đúng data." | — |
| Empty | no_results | "Không tìm được video phù hợp trong {{niche}} tuần này. Thử mở rộng thời gian?" | niche |
| Error | video_fail | "Video không tải được — thử dán lại hoặc dùng video khác." | — |
| Error | gemini_fail | "Đang bận — thử lại sau vài giây." | — |
| Error | stream_interrupted | "— Bị gián đoạn. Gõ 'tiếp' để tiếp tục." | — |
| Paywall | credit_depleted | "Hết deep credit tháng này. Mua thêm 10 credit = 130K VND." | — |
| Paywall | credit_low | "⚠ {{remaining}} deep credits còn lại" | remaining |
| Paywall | credit_bar | "{{count}} deep credits còn lại · Lướt xu hướng & tìm KOL không giới hạn" | count |
| Free | free_pill | "Miễn phí ✓" | — |
| Ambient | nav_chat | "Chat" | — |
| Ambient | nav_trends | "Xu hướng" | — |
| Ambient | nav_history | "Lịch sử" | — |
| Confirmation | copy_success | "Đã copy ✓" | — |
| Confirmation | copy_zalo | "Đã copy — forward qua Zalo cho KOL luôn." | — |
| Confirmation | credit_purchased | "Đã thêm {{count}} deep credit. Balance: {{total}}." | count, total |
| Loading | diagnosis_p1 | "Đang tải video..." | — |
| Loading | diagnosis_p2 | "Đang xem video của bạn..." | — |
| Loading | diagnosis_p3 | "Đang so sánh với {{count}} video trong niche..." | count |
| Loading | brief_loading | "Đang viết brief..." | — |
| Loading | creator_loading | "Đang tìm KOL..." | — |
| Input | url_detected | "Video TikTok — @{{handle}}" | handle |
| Input | url_invalid | "Link không hợp lệ — cần link TikTok" | — |
| Input | char_overflow | "Đã cắt — giới hạn 1000 ký tự" | — |
| Scroll | scroll_down | "↓ Cuộn xuống" | — |

---

## 8. Forbidden Patterns

### Forbidden Words
tuyệt vời, hoàn hảo, bí mật, công thức vàng, đột phá, kỷ lục, triệu view, bùng nổ, siêu hot, thần thánh, hack, chiến lược độc quyền, ai cũng phải biết, không thể bỏ qua, chắc chắn thành công

### Forbidden Openings
Chào bạn, Xin chào, Rất vui, Tuyệt vời, Wow, Chúc mừng, Đây là, Dưới đây là

### Forbidden Design Patterns
- No gradient backgrounds, decorative blobs, or ambient orbs in the product UI
- No emoji as visual design elements in chat responses — ✕/✓ markers replace emoji
- No shadows on any element — flat 1px borders only
- No rounded avatar placeholders with stock photos — initial letters or handle text
- No skeleton loaders — streaming status text replaces them (see §5b)
- No confetti, fireworks, or celebration animations — work tool, not game
- No spinners on primary chat flow — only on send button during processing (see §5a)
- No bottom sheets or modals for content — everything inline in chat flow
- No "typing indicator" dots animation — use streaming status text instead

### Forbidden Behaviors
- **GURU LANGUAGE:** Any copy that sounds like a Vietnamese TikTok course — "bí mật triệu view," "công thức vàng," "ai cũng phải biết." GetViews is anti-guru. We show data, not secrets.
- **FALSE CERTAINTY:** "Video này chắc chắn sẽ viral" — we never promise outcomes. "Hook này trung bình 3.2x views trong niche" is factual. "Hook này sẽ giúp bạn viral" is forbidden.
- **GENERIC ADVICE:** Any recommendation without the user's specific niche, video, or data. "Nên đăng thường xuyên hơn" is generic. "Top 5 trong niche này đăng 6 video/tuần, bạn đăng 2" is specific.
- **INTERRUPT AFTER WIN:** Upsell, upgrade prompt, or suggestion immediately after diagnosis/brief. Let the result breathe. Wait for user's next message.
- **APOLOGETIC ERRORS:** "Xin lỗi, đã xảy ra lỗi!" — just state what happened and what to do: "Video không tải được. Thử lại."
- **TEACHER TONE:** "Bạn nên biết rằng..." or "Điều quan trọng là..." — Minh is not a student. He's a working creator who needs answers.
- **CREDIT ANXIETY:** Any language that makes the user feel bad about spending a credit. No "Bạn có chắc muốn dùng 1 credit?" — just charge and show the result. The "Miễn phí ✓" pill on free queries handles the positive reinforcement.
- **BLOCKING UI:** Any modal, popup, or full-screen interstitial that prevents the user from continuing. Everything is inline. Errors are inline. Paywalls are inline. Nothing blocks the chat flow.
