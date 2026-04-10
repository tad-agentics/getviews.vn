# Visual Fidelity Audit — GetViews.vn
**Date:** 2026-04-10  
**Staging URL:** https://getviews-vn.vercel.app/  
**Auditor:** Product Designer (subagent)  
**Scope:** Landing page, Login screen, App screens (code audit), AI Slop Guard, Copy quality

---

## BLOCKING Findings

### BLOCK-001 — React Hydration Error #418 (Landing + Login pages)

| Field | Detail |
|---|---|
| **Screen** | Landing page (`/`) and Login page (`/login`) |
| **Issue** | Console throws `Minified React error #418` on both pages. This is a hydration mismatch — server-rendered HTML doesn't match client-rendered HTML, causing React to discard the entire SSR output and switch to full client rendering. |
| **Evidence** | Browser console: `"Uncaught Error: Minified React error #418; visit https://react.dev/errors/418?args[]=HTML&args[]= ..."` observed on both `entry.client-CtsBp3fy.js:8` for both pages. |
| **Root cause** | `LandingPage.tsx` line 172: `useState(() => typeof navigator !== "undefined" && navigator.onLine)`. During SSR pre-render, `navigator` is undefined → initial state is `false`. On the client, `navigator.onLine` is `true` → state mismatch → React error #418. Login page is also affected (likely same pattern via shared root hydration). |
| **Impact** | SSR/pre-rendering benefit of landing page is **completely lost** — SEO sees client-rendered HTML, not pre-rendered. CLS risk on initial paint. Entire root degrades to client SPA. |
| **Fix** | Change `LandingPage.tsx` line 171–173 from: `useState(() => typeof navigator !== "undefined" && navigator.onLine)` to: `useState(true)`. The existing `useEffect` at lines 185–194 will correct it post-mount if actually offline. This initializes as "online" (true for 99.9% of page loads) and avoids the SSR/client mismatch. |

---

## NON-BLOCKING Findings

### NB-001 — English string "Updated 4h ago" in landing page live demo

| Field | Detail |
|---|---|
| **Screen** | Landing page — Live Demo section (static mockup) |
| **Issue** | `LandingPage.tsx` line 157: `412 video review đồ gia dụng · 7 ngày · Updated 4h ago` — "Updated 4h ago" is English. Should be Vietnamese. |
| **Severity** | MINOR |
| **Fix** | Change to `Cập nhật 4h trước` |

### NB-002 — CreditBar missing "browse is free" reinforcement copy

| Field | Detail |
|---|---|
| **Screen** | All app screens — CreditBar sidebar widget |
| **Issue** | Screen spec says normal state should show: `"{{count}} deep credits còn lại · Lướt xu hướng & tìm KOL không giới hạn"`. The current `CreditBar.tsx` shows only the count/cap progress bar without the "còn lại · Lướt xu hướng & tìm KOL không giới hạn" benefit text. This misses the "Transparency" emotional objective (spec: copy-rules.mdc Credit Display). |
| **Severity** | IMPROVE |
| **Fix** | Add a text line below the progress bar: `<p className="text-[10px] text-[var(--faint)] mt-1">Lướt xu hướng & tìm KOL không giới hạn</p>` (only when credits > 5). |

### NB-003 — ExploreScreen placeholder.svg fallback

| Field | Detail |
|---|---|
| **Screen** | ExploreScreen (`/app/trends`) |
| **Issue** | `ExploreScreen.tsx` line 50: `const PLACEHOLDER_THUMB = "/placeholder.svg"` — this file likely doesn't exist in `public/`, which would show a broken image when video thumbnails fail to load. |
| **Severity** | MINOR |
| **Fix** | Either add `public/placeholder.svg` (a neutral grey rectangle) or replace with an inline SVG data URI, or remove the fallback and use CSS `bg-[var(--surface-alt)]` empty state. |

### NB-004 — PricingScreen purple gradient background (AI Slop Guard)

| Field | Detail |
|---|---|
| **Screen** | PricingScreen (`/app/pricing`) |
| **Issue** | Line 317: `style={{ background: "var(--gradient-purple-wash)" }}`. The design-system.mdc AI Slop Guard rule says "No gradient backgrounds using purple, violet, or indigo." `--gradient-purple-wash` is `linear-gradient(34deg, rgba(176,95,217,0.12)...)` — a purple gradient. This is defined as a Make design token in `app.css` line 81, so it may be intentional from Make's design output. |
| **Severity** | IMPROVE (acceptable if from Make design token — confirm with Make source) |
| **Fix** | If not in original Make output: replace with `bg-[var(--surface-alt)]` or a non-purple gradient. If from Make design intent: acceptable — document as intentional deviation from AI Slop Guard rule. |

### NB-005 — LoginScreen: Google listed as primary (vs spec says Facebook primary)

| Field | Detail |
|---|---|
| **Screen** | Login (`/login`) |
| **Issue** | Code comment says `/* Google — primary */` and Google is rendered first. Screen spec (`screen-specs-getviews-vn-v1.md` line 51) says "Facebook OAuth (primary) + Google OAuth (secondary)". The audit task brief however says "ordered correctly (Google first)" — suggesting this is an intentional product decision. |
| **Severity** | MINOR — if intentional, update the spec. If not, swap order. |
| **Fix** | Confirm with product owner. If Google-first is the intended order (which the audit task suggests), update `screen-specs-getviews-vn-v1.md` line 51 to reflect the actual order. |

---

## PASS

### Landing Page (`/`)
- ✅ All 8 sections present and visible in browser snapshot: Hero, Pain Points (3), Solutions (3), Live Demo, Social Proof (before/after stats), Pricing (4 tiers), FAQ (6 items), Final CTA
- ✅ Page loads with HTTP 200, assets load cleanly (no 404 errors in network log)
- ✅ Billing toggle: Tháng / 6 tháng / Năm — all 3 options present and interactive
- ✅ Pricing section: All 4 tiers visible (Dùng thử, Starter, Pro, Agency)
- ✅ FAQ accordion: 6 items, all collapsed by default, Radix Accordion implemented
- ✅ StickyBar: Implemented with scroll threshold at 480px (code-verified)
- ✅ Final CTA section: Separate "Thử dán 1 link video vào" section present
- ✅ Schema.org JSON-LD: Organization + FAQPage structured data injected
- ✅ Self-hosted fonts: TikTok Sans (Variable, Regular, Medium, Bold) all returning 200
- ✅ CTA behavior: `handlePrimaryCta` routes correctly (session → `/app`, install-ready → PWA prompt, iOS → sheet, else → `/login`)
- ✅ Vietnamese copy throughout — no English strings in user-facing copy (except NB-001)
- ✅ No lorem ipsum or placeholder copy anywhere on landing page
- ✅ No generic hero copy ("Unlock the power of..." etc.)

### Login Screen (`/login`)
- ✅ Google button present ("Đăng nhập với Google")
- ✅ Facebook button present ("Đăng nhập với Facebook")
- ✅ Email toggle button present ("Đăng nhập bằng Email") — per user request
- ✅ Legal links present ("Điều khoản dịch vụ", "Chính sách bảo mật")
- ✅ Vietnamese copy throughout — no forbidden opening words (Chào bạn, Xin chào, etc.)
- ✅ No forbidden words (tuyệt vời, đột phá, bùng nổ, etc.)
- ✅ Loading state: Facebook-specific blocked-popup error copy implemented
- ✅ Double-tap guard: `anyLoading` disables all buttons while any OAuth in progress

### Auth Guard
- ✅ Unauthenticated navigation to `/app` correctly redirects to `/login`

### ChatScreen (code audit)
- ✅ Message bubbles implemented (user: purple-light bg, assistant: bordered card)
- ✅ Intent pill system: `QUICK_ACTIONS` with Vietnamese labels (Tư vấn chiến lược, Phân tích trang TikTok, Tìm xu hướng, Chẩn đoán video)
- ✅ URLChip: TikTok URL detection → chip above input with `AnimatePresence`
- ✅ StreamingStatusText component wired
- ✅ FreeQueryPill component wired on free messages
- ✅ NicheSelector: shown when `needsNiche` is true
- ✅ Paywall inline copy: "Hết deep credit tháng này. Mua thêm 10 credit = 130.000 VND." ✓ matches spec
- ✅ Stream interruption copy: "— Bị gián đoạn. Gõ 'tiếp' để tiếp tục." ✓ matches spec
- ✅ Mobile input font-size 16px — prevents iOS auto-zoom
- ✅ DesktopInput + MobileInput responsive layouts

### HistoryScreen (code audit)
- ✅ Header copy: "Lịch sử phân tích" — matches spec
- ✅ Search bar present (Input component)
- ✅ Intent badges with Vietnamese labels (Soi Video, Đối thủ, Soi Kênh, Brief, Xu hướng, Tìm KOL)
- ✅ Skeleton loader implemented (`HistoryListSkeleton`)
- ✅ Date formatting in Vietnamese (Hôm nay, Hôm qua, DD/MM)
- ✅ Delete confirmation dialog with Vietnamese copy

### PricingScreen (code audit)
- ✅ All 4 tiers: Free, Starter, Pro, Agency — with correct pricing (249K, 499K, 1.490K monthly)
- ✅ Billing toggle: monthly / biannual / annual — all 3 periods implemented with savings data
- ✅ Vietnamese copy throughout all plan cards
- ✅ Features list per tier in Vietnamese

### SettingsScreen (code audit)
- ✅ Profile section with user avatar/name
- ✅ Niche picker (`useNicheTaxonomy` hook wired)
- ✅ Subscription info section
- ✅ Credit transaction history section
- ✅ Logout implemented
- ✅ Link to LearnMoreScreen present

### LearnMoreScreen (code audit)
- ✅ Sections: GetViews.vn, Tài nguyên từ TikTok, Pháp lý
- ✅ Vietnamese copy throughout

### AI Slop Guard
- ✅ No `text-gray-*` Tailwind classes anywhere in route files
- ✅ No arbitrary padding/margin like `p-[17px]` or `gap-[23px]` — only layout-intentional pixel sizes (`w-[220px]` sidebar etc.)
- ✅ No 3-column icon-in-circle feature grids
- ✅ No decorative blobs or wavy dividers
- ✅ No generic hero copy patterns
- ✅ No emoji used as visual design elements (uses ✕/✓ markers per spec)
- ✅ No raw hex colors in Tailwind classes (uses CSS vars throughout)

### Copy Quality (5-question test)
1. **Data-backed?** ✅ Landing page cites "412 video", "92%", "3.2x views", "46.000+ video" — all specific
2. **Actionable?** ✅ Diagnosis copy gives specific fix steps in both demo and ChatScreen
3. **Forbidden words?** ✅ None found in any screen (automated grep: 0 matches)
4. **Peer expert tone?** ✅ Direct, non-guru, no apologetic language
5. **Natural in Vietnamese Zalo group?** ✅ Loanwords (hook, brief, niche, credit) used correctly

---

## Summary

**BLOCKING: 1 | NON-BLOCKING: 5 (2 MINOR, 2 IMPROVE, 1 MINOR/spec-alignment)**

The core app structure, copy, and visual design are solid. The single BLOCKING issue (React hydration error #418) is a one-line fix in `LandingPage.tsx` that restores SSR pre-rendering for SEO. All other findings are MINOR improvements.

### Priority order for fixes
1. **BLOCK-001** — Fix `navigator.onLine` hydration mismatch (`LandingPage.tsx` line 171)
2. **NB-001** — "Updated 4h ago" → "Cập nhật 4h trước" (1-line fix)
3. **NB-003** — Add `public/placeholder.svg` or replace fallback in ExploreScreen
4. **NB-002** — Add "Lướt xu hướng & tìm KOL không giới hạn" to CreditBar
5. **NB-004** — Confirm PricingScreen gradient-purple-wash is Make design intent
6. **NB-005** — Update screen-specs to reflect confirmed Google-first login order
