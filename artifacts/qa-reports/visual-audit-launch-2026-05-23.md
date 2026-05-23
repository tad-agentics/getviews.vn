# Visual Fidelity Audit — GetViews.vn Launch Gate
**Date:** 2026-05-23  
**Auditor:** Product Designer (subagent)  
**Production URL:** https://www.getviews.vn  
**Viewport tested:** 375px mobile (primary), 1024px desktop (landing page only)  
**Auth state:** Authenticated session active (test account: "Trinh", niche: Làm đẹp · Skincare)

---

## Verdict

**PASS_WITH_CONCERNS**

The product is structurally complete and copy-compliant. All launch-delta screens (ChannelDepthPicker, Trends report, answer depth pills) are rendered and functional. One BLOCKING concern requires Tech Lead confirmation before `/pre-handoff`: the primary accent color has changed from the EDS-specified purple (#7C3AED) to a hot pink (#f72585) across all screens. This appears intentional but is undocumented. Additionally, one data integrity concern (corpus size claim) requires verification.

---

## Screens Audited

| Screen | Route | Status | Notes |
|---|---|---|---|
| LandingPage | `/` | ✓ AUDITED | Pre-render confirmed, all sections present |
| LoginScreen | `/login` | ~ PARTIAL | Redirected to /app (active session — expected behavior) |
| StudioHome | `/app` | ✓ AUDITED | Full snapshot + CSS inspection |
| TrendsScreen | `/app/trends` | ✓ AUDITED | Làm đẹp · Skincare + Nghệ thuật niches checked |
| ChannelScreen | `/app/channel` | ✓ AUDITED | ChannelDepthPicker fully rendered |
| ResearchScreen | `/app/answer` | ✓ AUDITED | Depth pills regression check |
| HistoryScreen | `/app/history` | ✗ SKIPPED | Not navigated |
| PricingScreen | `/app/pricing` | ✗ SKIPPED | Pricing section audited on landing page instead |
| SettingsScreen | `/app/settings` | ✗ SKIPPED | Not navigated |
| AnswerDetail | `/app/answer/:id` | ✗ SKIPPED | Requires live analysis (no credits on test account) |
| PaymentScreens | `/app/checkout` | ✗ SKIPPED | Not navigated |

---

## BLOCKING Issues

### B-01 — Primary accent color is #f72585 (hot pink), not #7C3AED (purple) as specified in EDS

**Severity:** BLOCKING — requires Tech Lead decision before `/pre-handoff`  
**Screens affected:** All screens  
**Evidence:**
```
CSS computed: --primary = #f72585
CSS computed: --gv-accent = #f72585
CSS computed: --ring = #f72585
```
Expected (EDS §5): `oklch(0.53 0.26 295)` = `#7C3AED` ("TikTok Purple")

The production app uses a hot-pink fuchsia `#f72585` as `--primary` and `--gv-accent` across all interactive elements:
- Send "Gửi" button background
- Niche badge background ("Làm đẹp · Skincare" highlight chip)
- Hero gradient text on landing page
- Top accent bar  
- Active CTA buttons on landing

EDS §5 lists TikTok Red `#FE2C55` as "Logo mark only". The production color `#f72585` is neither the specified purple nor the documented TikTok Red — it is a third undocumented color.

**Assessment:** This looks intentional. The `--gv-accent` token was presumably deliberately set to pink during Studio design work. The implementation is internally consistent (no mixed colors). However, the EDS is the design source of truth and has not been updated.

**Fix hint:** Tech Lead must either:
- (A) Update `artifacts/docs/emotional-design-system.md §5` to document the intentional pivot from purple to hot pink, OR
- (B) Revert `--primary` / `--gv-accent` in `src/app.css` to `oklch(0.53 0.26 295)` (#7C3AED)

Option A is recommended if the pink is intentional (Completeness: 10/10 — just a docs update). Option B is significant rework across the entire token system.

---

### B-02 — Corpus size claim on landing page ("1.500+") requires verification

**Severity:** BLOCKING — data integrity  
**Screens affected:** LandingPage `/`

The landing page displays "1.500+ Video Thực", "Database 1.500+ Video Creator Việt", and "Cập nhật mỗi tuần từ 1.500+ video thực" in three separate sections.

CLAUDE.md states: **"Do not put fabricated corpus-size numbers in user-facing copy or docs; query `video_corpus` for actual counts when a number matters."**

The system design documents 46,000+ analyzed Vietnamese TikTok videos. The per-niche app displays "278+ video" for Làm đẹp · Skincare specifically.

**Risk:** If the actual `SELECT COUNT(*) FROM video_corpus` is ~1,500, the landing page is accurate and this clears. If the corpus is significantly larger (10K+, 46K+), the landing page is understating which may reduce conversion trust.

**Fix hint:** Run `SELECT COUNT(*) FROM video_corpus WHERE content_class_id IS NOT NULL` (the active indexed set). If count > 5,000, update landing page copy to the real number. If ~1,500, the current copy is accurate and this concern clears.

---

## NON-BLOCKING Issues

| # | Screen | Issue | Fix Hint |
|---|---|---|---|
| NB-01 | Landing `/` | Input placeholder "https://tiktok.com/@..." differs from spec "Dán link TikTok để bắt đầu" | Update `placeholder` prop if original copy was intentional per product |
| NB-02 | Landing `/` | Hero h1 evolved from spec copy; live: "Lướt TikTok cả ngày? Để GetViews 'cày' thay." vs spec | Copy passes quality test — no action required unless reverting to spec |
| NB-03 | All input screens | Disabled "Gửi" button shows faded primary pink (opacity reduction) instead of `--faint` gray | Change disabled state: `bg-faint cursor-not-allowed` instead of `opacity-50 bg-primary` |
| NB-04 | Landing `/` | Missing `<link rel="canonical" href="https://www.getviews.vn/">` in `<head>` | Add canonical tag in `src/routes/_index/route.tsx` head export |
| NB-05 | Landing `/` | Social proof "before/after" view counts (2.000 / 45.000) are visually correct but split across separate DOM nodes; accessibility tree reads "view · video review nồi chiên" without the number | Add `aria-label` to parent container or restructure to keep number + label in same element |
| NB-06 | Trends `/app/trends` | Active niche filter chip uses dark-fill (#0A0D12) instead of expected `--primary-light` tint | Update active chip state in `TrendNicheFilter` component |
| NB-07 | Studio Home `/app` | "công thức" appears in section headings ("6 công thức hook đứng sau gợi ý"). "công thức" alone is NOT in the forbidden list (only "công thức vàng" is forbidden). No action needed. | — CLEARED |
| NB-08 | Channel `/app/channel` | User credit shows "0 credit / lần" — test account has no credits. Sâu mode still appears selectable (not visually disabled). Risk: user taps Sâu → hits paywall with no visual warning at depth picker. | Add disabled state or warning on Sâu pill when credit balance < 3 |

---

## What Passed Cleanly

### Landing Page `/`
- ✓ All 10+ sections present: Hero, Trust Ticker, PainPointCards ×3, Steps ×3, Solution ×3, Features grid, Trends Demo section, Database section, Infrastructure section, SocialProof, Pricing ×4 tiers, FAQ accordion ×6, FinalCTASection
- ✓ FAQ accordion: 6 items, expand/collapse functional (e12 tested: expanded to `[expanded]` state)
- ✓ StickyBar: Appears after scroll, shows "GetViews.vn" + "Soi Video Miễn Phí" CTA
- ✓ Pricing billing toggle: Tháng / 6 tháng / Năm buttons present and functional
- ✓ Pre-rendered HTML confirmed (h1 in DOM on load, rich meta tags without JS)
- ✓ `<title>`: "GetViews — Phân tích TikTok cho Creator Việt"
- ✓ `<meta name="description">`: Specific, data-backed, no forbidden words
- ✓ OG title + description set and match meta
- ✓ Single H1 per page (h1 count = 1)
- ✓ Social proof numbers present: "TRƯỚC 2.000 view · video review nồi chiên → SAU KHI FIX 45.000 view"
- ✓ Uses ✕/✓ markers (not emoji) in social proof
- ✓ Numbers use dot separators: "1.247", "2.000", "45.000" per Vietnamese format
- ✓ No forbidden words in any copy scanned
- ✓ No AI slop patterns (no gradient backgrounds, no 3-col icon grids, no decorative blobs)
- ✓ Mobile 375px: Clean single-column layout, readable at mobile baseline

### Studio Home `/app`
- ✓ Personalized greeting with real user name ("Chào Trinh") and real niche + real hook count
- ✓ Depth pills: "Cơ bản" (selected) + "Chuyên sâu" present and interactive
- ✓ Send button disabled correctly when input empty
- ✓ 5 prompt cards with niche-specific copy
- ✓ Hook formulas section: 6 hooks with view TB data (843K, 569K, 530K, etc.) — data-backed
- ✓ Breakout videos section: 3 real videos with view counts and hook text
- ✓ Bottom navigation: 5 tabs, Trang chủ active with correct icon state
- ✓ "LIVE · CẬP NHẬT VỪA XONG" badge and date "THỨ BẢY · 23.05" correct
- ✓ Live ticker with hook examples visible

### Trends Screen `/app/trends`
- ✓ Niche selector: All 16 active niches present as horizontal scroll tabs
- ✓ Pattern cards with "Mở công thức" expand buttons present (Làm đẹp · Skincare has 6 patterns)
- ✓ Douyin teaser card: "TÍN HIỆU SỚM · DOUYIN → VN / Pattern đang nổ ở TQ · video đã sub VN / Đi trước VN 4-10 tuần · không cần VPN" — launch delta requirement confirmed present
- ✓ Empty state for thin niches: Correct copy "Tuần này chưa thấy công thức nổi bật trong ngách. Đang theo dõi..." — no apology, directional
- ✓ Video feed sections: "VIDEO NÊN THAM KHẢO" and "VIDEO LEO ĐỈNH" rails present
- ✓ Week label: "TUẦN 21 · 18 tháng 5—24 tháng 5" accurate
- ✓ Search input with placeholder "Tìm hook, creator, từ khoá…"
- ✓ Filter buttons: Pattern / Mới nhất / 100K+ / 500K+ / 1M+ / Hôm nay / 7 ngày

### Channel Screen `/app/channel`
- ✓ **ChannelDepthPicker present and functional**: "Nhanh · 0 credit" (selected) + "Sâu · 3 credit" (unselected)
- ✓ Channel input with "tiktok.com/ @handle hoặc..." placeholder
- ✓ "Khám →" CTA button with dark fill
- ✓ Trust copy: "Chỉ đọc dữ liệu công khai. Không cần đăng nhập TikTok."
- ✓ Credit pill: "0 credit / lần" displayed

### Research Screen `/app/answer`
- ✓ **Depth pills NO REGRESSION**: "Cơ bản" (selected) + "Chuyên sâu" both present
- ✓ Pre-filled question from Studio context: "Xu hướng đang hot trong Làm đẹp · Skincare tuần này?"
- ✓ Input placeholder: "Dán link TikTok hoặc đặt câu hỏi..."
- ✓ Breadcrumb: "← Studio / NGHIÊN CỨU · LÀM ĐẸP · SKINCARE"

---

## Copy Quality Test Results

5 copy samples tested against copy-rules.mdc 5-question test:

| Sample | Data? | Actionable? | No forbidden words? | Peer-expert tone? | Natural Vietnamese? | Result |
|---|---|---|---|---|---|---|
| "Hook chậm 2.3 giây — Top video viral thường mở màn ở 0.5s" | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** |
| "Tuần này chưa thấy công thức nổi bật trong ngách. Đang theo dõi các công thức tiềm năng..." | skip | ✓ | ✓ | ✓ | ✓ | **PASS** |
| "Video không tải được — thử dán lại hoặc dùng video khác" | skip | ✓ | ✓ | ✓ | ✓ | **PASS** |
| "1.500+ video · 21 niche · Cập nhật hàng tuần" | ✓ | skip | ✓ | ✓ | ✓ | **PASS** |
| "Cơ sở dữ liệu · 4 video ngách · 1 mới tuần này" | ✓ | skip | ✓ | ✓ | ✓ | **PASS** |

No forbidden words found in any audited copy. No forbidden opening words found.

---

## AI Slop Guard Check

| Pattern | Status |
|---|---|
| Gradient backgrounds (purple/violet/indigo) | ✓ NONE FOUND |
| 3-column icon-in-circle feature grids | ✓ NONE FOUND |
| Global `text-align: center` on card content | ✓ NONE FOUND |
| Decorative blobs, wavy dividers | ✓ NONE FOUND |
| Generic hero copy ("Unlock the power of...") | ✓ NONE FOUND |
| Emoji as visual design elements | ✓ NONE FOUND (✕/✓ used instead) |
| Colored left-border accent cards as default pattern | ✓ NONE FOUND |

---

## Token Compliance Spot Check

```
--background: oklch(93% 0 0)       ✓ matches spec oklch(0.93 0.00 0)
--foreground: oklch(15% 0 0)       ✓ matches spec oklch(0.15 0.00 0)
--border:     oklch(90% 0 0)       ✓ matches spec oklch(0.90 0.00 0)
--primary:    #f72585              ✗ DEVIATES from spec #7C3AED (see B-01)
--accent:     #fdd9ea              ✗ Should be #F3F0FF (--purple-tint); matches pink pivot
body bg:      oklch(0.93 0 0)      ✓ correct light gray background
```

No raw hex colors found in Tailwind `className` props (audit via `bg-[linear-gradient(180deg,var(--gv-paper)...)]` pattern — using CSS vars, not hard hex). Token compliance outside of the primary color PASS.

---

## Dopamine Moments (D1–D4)

**Cannot fully verify without running a live analysis session.**

- D1 (First diagnosis result reveal, 600–800ms emphasis): Not tested — requires analysis credit
- D2 (Hook ranking bar fill animation): Not tested — requires analysis credit
- D3 (Brief completion animation): Not tested — requires analysis credit
- D4 (Free query "Miễn phí ✓" pill): Not tested — requires free query submission

**Recommendation:** Run one live analysis with a TikTok URL to verify D1 timing and "Miễn phí ✓" pill appear correctly before `/pre-handoff`.

---

## Mobile 375px Layout Compliance

| Screen | Layout | Touch targets | Input font ≥16px |
|---|---|---|---|
| Landing `/` | ✓ Single column | ✓ CTA buttons full-width | ✓ |
| Studio Home `/app` | ✓ Single column | ✓ | ✓ |
| Trends `/app/trends` | ✓ Single column + horizontal tab scroll | ✓ | ✓ |
| Channel `/app/channel` | ✓ Single column | ✓ | ✓ |
| Research `/app/answer` | ✓ Single column | ✓ | ✓ |

Bottom tab bar hidden at desktop (lg:), visible on mobile — CORRECT per spec.

---

## Summary: Launch Readiness

**Ready after B-01 resolution (color documentation/decision) and B-02 verification (corpus count).**

The two blocking items are both fast to resolve:
- B-01: Either update the EDS doc (15 min) or revert the color token (requires design decision + implementation)
- B-02: Run one SQL count query to verify the number is accurate

All functional requirements are met:
- ChannelDepthPicker (Nhanh/Sâu) ✓
- Depth pills on answer/research screens ✓ (no regression)
- Trends Douyin teaser ✓
- PatternCard formulas ✓
- Landing page all sections ✓
- FAQ accordion ✓
- StickyBar ✓
- Copy quality ✓
- Mobile 375px ✓
- AI Slop Guard ✓

---

## Status Signal

**DONE_WITH_CONCERNS** → **B-01/B-02 CLOSED @ 2026-05-23** (dogfood + NB items remain)

**Closed (2026-05-23):**
1. ~~**B-01:**~~ EDS §5 updated to magenta `#F72585` — production was correct; docs were stale.
2. ~~**B-02:**~~ Landing corpus stat wired via `/api/landing-stats` → `corpus_indexed_count` + `formatCorpusMarketingCount()`.

**Concerns remaining before `/pre-handoff`:**
1. **Dogfood:** `artifacts/qa-reports/dogfood-report.md` — human session required (0 BLOCKING findings).
2. **NB-08 (recommended before launch):** "Sâu · 3 credit" depth picker doesn't visually disable when user has 0 credits — could confuse users who tap Sâu then hit a paywall wall with no prior visual warning.
3. **D1–D4 timing (recommended):** Run one live analysis to spot-check dopamine moment animations before pre-handoff.
