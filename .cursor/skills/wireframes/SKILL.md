---
name: wireframes
description: Complete Phase 2 instructions — scope planning, anti-bloat rules, screen metadata format, Make TC-EBC prompt framework, Guidelines.md structure, and quality checks. Read this when running /phase2.
disable-model-invocation: true
---

# Phase 2 — Screen Planning + Make brief (appendix)

Two jobs, **one committed doc** (`artifacts/docs/screen-specs-[app]-v1.md`):
1. **Screen specs** — scope planning, screen metadata with interaction flows, copy slots, states
2. **`## Make build brief` appendix** — structured input for the human to use in Make to generate visual designs (same file — no separate `figma-*.md`)

Visual design is human-driven via Make. This phase produces the structured input for that process, not wireframe visuals.

---

## Part A — Scope Planning

Scope planning happens before any screen is specced. Define the complete product now — no additions mid-build.

### Before You Plan

Extract from `artifacts/docs/northstar-[app].html` and `artifacts/docs/emotional-design-system.md`:
- App name and one-line description
- Primary user — who is completing the core action?
- Core loop — what is the single most important thing the user does?
- All features — from Build Scope table (§7). Sort into Build vs Not Building.
- Landing page content — from §7b. Headline, keywords, trust signals, CTA copy, FAQ items, social proof. This is the only source for landing page copy — do not invent.
- Revenue model — matters for monetization screen scoping
- Retention mechanic — what brings users back?
- Not Building list — from §8. Use as starting point; add any features cut during scoping.
- Auth model — from §9. Determines auth screen set: anonymous-first? Phone OTP? OAuth? What triggers account creation? What profile data is collected?
- Payment provider and methods — from §11. Determines monetization screen pattern: checkout redirect? QR code? In-app credit purchase? Do not assume Stripe — use the provider specified in the northstar.
- Feature grouping / build waves — from §12. Use as input for recommended build order.
- User scenarios — from §13 (if present). The richest source for navigation flows — each scenario traces an exact path through the app with feature/endpoint tags. Use these to validate every screen is reachable and every navigation path is accounted for.

**Copy direction** — from `artifacts/docs/emotional-design-system.md` and `.cursor/rules/copy-rules.mdc`:
- Copy Slot Inventory — from EDS §7. Use pre-defined copy templates for common UI patterns (empty states, error messages, paywall copy, nav labels).
- Dopamine Moments — from EDS §6. Flag screens that have a designed dopamine moment in the metadata block.
- Copy formula + quality test — from copy-rules.mdc. All screen spec copy must be production-ready and pass the 5-question quality test.

### Scoping Decision Tree

**Two-pass methodology:** Enumerate all screens first (Pass 1), then cut using anti-bloat rules (Pass 2). Never skip Pass 1 — cutting without complete enumeration is how apps ship incomplete.

**Pass 1 — Enumerate screens per feature using decomposition patterns:**

For EVERY feature in the Build Scope table (§7), enumerate screens using these patterns:

| Feature type | Screens it typically needs | Count |
|---|---|---|
| **View a list of items** | List screen + Detail screen (+ Filter/Sort if >10 items) | 2-3 |
| **Create/submit something** | Input form + Confirmation/Preview + Success/Result | 2-3 |
| **Compare/choose between options** | Options list/grid + Comparison view + Selection confirmation | 2-3 |
| **View a single result** | Result screen + Share preview (if shareable) | 1-2 |
| **User profile/settings** | Profile view + Edit profile + Settings (sections, not screens) | 2-3 |
| **Onboarding/data collection** | One screen per 3-4 fields max. 6 fields = 2 screens. | 1-3 |
| **Payment/monetization** | Credit balance + Purchase/checkout + Purchase success | 2-3 |
| **Search** | Search input + Results list + (uses existing Detail screen) | 1-2 |
| **History/saved items** | History list + (uses existing Detail screen) | 1 |
| **Share flow** | Share card preview + (native share sheet is not a screen) | 0-1 |

**For each feature, ask:** "What does the user see at EVERY step from entry to completion?" Walk through: Tap → Loading → Result → Action → Confirm → Done. Each visual state that fills the viewport is a screen.

**Pass 2 — Cut using anti-bloat rules (below).**

Only cut AFTER Pass 1 enumeration is complete. Annotate every cut with what it merged into.

### Screen Decomposition — Commonly Forgotten Screens

Agents systematically miss these. Check each one against the northstar before marking "N/A":

| Screen | Why it's forgotten | When to include | When to skip |
|---|---|---|---|
| **Result Detail** | Agent puts all info on the list card | Any feature where the list card can't fit all meaningful content | List card IS the complete view (e.g., simple checklist items) |
| **Empty state as first-use guide** | Agent adds empty state text but not a guided first action | Core loop screens on first visit before user has data | App pre-populates data (e.g., daily horoscope — no user input needed) |
| **Paywall gate screen** | Agent adds paywall as a modal, not a screen | Credit-gated features where the free preview + upsell needs full-screen treatment | Simple inline "costs N credits" button is sufficient |
| **Success/confirmation screen** | Agent skips straight to the result | Any action where the user expects acknowledgment: payment, profile save, first submission | Background actions the user doesn't wait for |
| **Edit screen (vs. create screen)** | Agent reuses create screen for edit | Any entity the user creates and later modifies — different context, different copy, sometimes different fields | Read-only data or data that's set once |
| **Search/filter results** | Agent puts search in the header of an existing screen | Any list with >10 items where users need to find specific items | Short lists where scanning is faster than searching |
| **Notification/activity feed** | Agent skips unless "notifications" is in the northstar | Any app with async events the user needs to see (results ready, credits low, new content) | No async events |
| **Share preview** | Agent generates share link without showing what gets shared | Any feature with social sharing or viral mechanics | No sharing |
| **Error recovery screen** | Agent adds error toast, not a recovery path | Payment failure, network timeout on critical action, expired session | Transient errors where retry is the only action |
| **Comparison/selection screen** | Agent puts radio buttons on a single screen | Any choice between 3+ complex options where each has multiple attributes | Binary yes/no or simple A/B choice |

### Scoping Decision Tree (after enumeration)

Apply to every enumerated screen from Pass 1:

```
Is this screen required to complete any user scenario from §13?
  YES → Build

Is this the ONLY way to access a core function?
  YES → Build

Can this screen be merged into another screen WITHOUT overloading it?
  (Overloaded = >3 primary actions, >5 scrollable sections, or mixed purposes)
  YES → Merge (annotate where it merged to)
  NO  → Build as standalone

Would removing this screen break a navigation flow or leave a dead end?
  YES → Build
  NO  → Not Building (but document what user scenario it would serve in v2)
```

### Category Budgets

| Category | Typical range | Baseline for B2C app | Rule |
|---|---|---|---|
| Core loop | 8–18 screens | ~12 | Must be ≥50% of product screens (excluding infrastructure) |
| Retention | 3–8 screens | ~5 | Each screen must tie to a named retention mechanic |
| Monetization | 2–5 screens | ~3 | Use hosted checkout to stay at low end |
| Infrastructure | 5–8 screens | ~6 | Auth + onboarding + settings + profile |
| Landing page | 1 | 1 | Always |
| **Total** | **19–40 screens** | **~27** | **30 screens is normal for a complete B2C app** |

**Build-time reality check:** Every screen costs 15–45 minutes during the feature build (faster than before — Make provides the visual layer, agents integrate). At 30 screens × 30 min avg = ~15 hours. This fits a 2-3 day RAD sprint with a 2-person team.

**If the total exceeds 35 screens:** Review for genuine anti-bloat violations (below). If none found, the product is correctly scoped — extend the sprint estimate.

**If the total is under 20 screens:** The app is almost certainly under-scoped. Re-run Pass 1 decomposition. Check: is every Detail screen present? Every confirmation? Every empty-state guide? Every paywall gate?

### Anti-Bloat Rules — Cut After Enumeration (Pass 2)

**Only apply these AFTER completing Pass 1 enumeration.** Cutting before complete enumeration is how apps ship broken flows.

1. **"Second dashboard"** — more than one screen whose primary action is "view a summary." Pick one.
2. **"Settings sprawl"** — more than one settings screen. Consolidate into sections on one screen.
3. **"Onboarding creep"** — more than 3 onboarding screens (excluding auth). Simplify the product.
4. **"Overloaded merge"** — merging IS appropriate when a screen has <3 primary actions and fits in one scroll. Merging is WRONG when it creates >3 primary actions, >5 scroll sections, or mixed purposes (viewing + editing + navigating). When in doubt, keep screens separate — an extra screen costs 30 min, a broken merge costs 2 hours to redesign.
5. **"Admin screen"** — any screen that serves the builder, not the user. Use Supabase Dashboard instead.
6. **"Notification management"** — skip notification preference screens unless notifications are the core retention mechanic.
7. **"50% rule"** — infrastructure + monetization outnumber core loop + retention. Cut plumbing, not product.

### Completeness Gate (must pass before proceeding to metadata)

After Pass 1 + Pass 2, validate completeness:

```
For EACH user scenario in northstar §13:
  Walk through every step. Does each step have a screen?
  Does each screen-to-screen transition exist in the navigation plan?
  Are there any steps where the user is "teleported" without a clear path?

For EACH core loop feature:
  Can the user LIST items? → List screen exists?
  Can the user VIEW details? → Detail screen exists?
  Can the user CREATE/EDIT? → Input screen exists?
  Is there a SUCCESS state? → Confirmation screen or in-screen confirmation exists?
  Is there an EMPTY state on first use? → Empty state defined (screen or component)?
  Is there a PAYWALL gate? → Gate screen or inline gate defined?

For the FULL app:
  Can the user reach every screen from the home/dashboard?
  Can the user return to home from every screen?
  Does the auth flow cover: login → app, signup → onboarding → app, logout → login?
  Does the payment flow cover: see price → pay → confirmation → access unlocked?
```

**If any check fails:** add the missing screen. Do not proceed to metadata with an incomplete flow.

### Mandatory Infrastructure Screens

Auth screens are determined by the northstar §9 (Auth Model). Do not guess the auth method — read it from the northstar.

| Screen | When to include | Notes |
|---|---|---|
| Login | Always | Method from northstar §9: Phone OTP / email+password / magic link / OAuth |
| Signup | Always (unless anonymous-first) | If §9 says anonymous-first: skip signup, add account-upgrade screen at the trigger point instead |
| Forgot Password | Only if email+password auth | Skip for magic link, OAuth, or Phone OTP |
| Account Upgrade | Only if anonymous-first → upgrade | Shown when the §9 "Account trigger" fires |
| Profile / Onboarding | If §9 lists profile data beyond email/phone | Collect birth date, birth time, gender, etc. — only what §9 specifies |
| **Landing Page** | **Always** | **Single conversion page at `/`. Content from northstar §7b.** |

Default to custom auth screens for consumer products (maintains design system consistency). Use Supabase Auth UI only for internal tools.

### Mandatory Landing Page — Section Stack

The landing page is mandatory infrastructure — not a "nice to have." It is the destination for organic search, viral share links, and paid ad traffic. Without it, the PWA has no acquisition surface.

**Route:** `/` (pre-rendered at build time for SEO — authenticated app screens live at `/app/*`)

**Content source:** All copy comes from northstar §7b (Landing Page Content). The screen spec agent does not invent landing page copy — it uses the production-ready content defined in the northstar.

**Section stack (mobile-first, top to bottom):**

1. **Hero (above the fold)** — Headline from §7b, subheadline, phone mockup showing the PWA, primary CTA button (from §7b), microcopy below CTA
2. **Trust bar** — Compact row: user count, star rating, 3–4 media/partner logos. All from §7b trust signals.
3. **Benefits (3–4 items)** — Icon + outcome-focused copy per item. Each benefit ≤ one scroll height.
4. **How it works (3 steps)** — Visual: 1. Tap install → 2. Add to home screen → 3. Start using. Repeat CTA after this section.
5. **Social proof** — Testimonials from §7b with name, age, profession, city. Optional: real-time activity counter.
6. **FAQ (accordion, 4–6 items)** — Questions from §7b. These also feed FAQ JSON-LD structured data (built in tech spec §18).
7. **Final CTA** — Repeat hero CTA with social proof line.
8. **Sticky bottom bar** — Appears after scrolling past hero. Compact: `[App icon] CTA text`. One risk reducer.

**Metadata block must include:**
- Dopamine moment: `none` (landing page is calm/professional, not celebratory)
- Credit cost: `N/A` (no paywall)
- Copy slots: All production-ready from §7b
- Interaction flow: hero load → scroll → CTA tap → install prompt (Android) or manual instructions (iOS)
- Edge case: Already installed → hide install CTA, show deep link into app instead

### Scope Plan Output Format

```markdown
# Screen Scope Plan — [App Name]

## Build Scope
*All screens that ship in this build. Target: [X] screens.*

### Core Loop
| # | Screen Name | Primary User Action | Notes |
|---|---|---|---|
| 1 | [Screen] | [What user does] | [constraint or dependency] |

### Retention
| # | Screen Name | Retention Mechanic | Notes |
|---|---|---|---|

### Monetization
| # | Screen Name | Revenue Mechanic | Notes |
|---|---|---|---|

### Infrastructure
| # | Screen Name | Purpose | Notes |
|---|---|---|---|

### Landing Page
| # | Screen Name | Purpose | Notes |
|---|---|---|---|
| 1 | LandingPage | Single conversion page at `/` — hero, trust, benefits, how-it-works, social proof, FAQ, CTA | Content from northstar §7b |

**Total: [X] screens** ([A] core loop + [B] retention + [C] monetization + [D] infrastructure + [E] landing page)
**Core loop ratio:** [A/(A+B+C)]% of product screens (must be ≥50% — infrastructure and landing page excluded from ratio)
**Completeness check:** ≥20 screens? [YES/NO — if NO, re-run Pass 1 decomposition]
**Build-time estimate:** [X] screens × 30 min avg = ~[Y]h

**Core loop summary:** [One sentence: complete product flow from first screen to completion]

---

## Not Building
*Excluded from this version. Do not design, do not spec, do not build.*

Copy this block directly into `project.mdc` and the tech spec Not Building section:

- [Feature] — [one line reason for exclusion]
```

### Common Scoping Mistakes

**Under-scoping (more common — agents default to fewer screens):**

| Pattern | Problem | Fix |
|---|---|---|
| Feature = 1 screen | "View results" mapped to one screen, missing Detail + Share + Paywall | Run Pass 1 decomposition: List → Detail → Action → Confirm for each feature |
| Missing Detail screens | All content crammed onto list cards | If a card has >3 data points, it needs a Detail screen |
| Missing confirmation screens | User completes action, nothing acknowledges it | Every payment, save, or first-time action gets a confirmation |
| Missing empty states as screens | Empty state is a single line of text | First-use experience needs a guided screen, not just "No data yet" |
| Missing edit-vs-create distinction | Same form for create and edit | Edit needs pre-populated fields, different CTA copy, cancel/discard flow |
| Missing paywall screens | Paywall is an alert dialog, not a screen | Credit-gated features with preview + upsell need full-screen treatment |
| Under-counting at 15-18 screens | Agent targets low end of budget | 27-30 is the baseline for complete B2C apps. Under 20 = almost certainly incomplete |

**Over-scoping (less common — catch with anti-bloat rules):**

| Pattern | Problem | Fix |
|---|---|---|
| Auth screens missing from count | Built ad-hoc, eats unplanned time | Include Login + Signup in count from the start |
| Settings screen bloat | 3+ settings screens | One settings screen, max |
| Onboarding beyond minimum required fields | Friction, not value | Cut to bare minimum |
| More than one "home" or dashboard | Split attention | Pick one, cut the other |
| Features added "since we're already building" | Scope creep kills speed | Not in scope plan = Not Building |

---

## Part B — Screen Metadata + Make brief appendix

Once the scope plan is confirmed, produce `artifacts/docs/screen-specs-[app]-v1.md` with screen metadata and the Make brief sections below:

### Output 1 — `artifacts/docs/screen-specs-[app]-v1.md`

Screen metadata for every screen. This is the build brief for feature agents. Each screen has a structured metadata block — the direct input for backend and frontend agents.

**Copy in screen specs must be production-ready — not directional.**

All copy must be validated against `copy-rules.mdc` and the EDS copy formula before delivery. The frontend agent copies these strings verbatim into components.

**Read before writing any copy:** `artifacts/docs/emotional-design-system.md` (§5 Copy Formula, §6 Screen-Context Rules, §7 Copy Slot Inventory, §8 Forbidden Patterns) and `.cursor/rules/copy-rules.mdc`.

| Element | Wrong | Right (production-ready) | Dynamic (token) |
|---|---|---|---|
| CTA | `[Primary CTA]` | `Xem chi tiết` | — |
| Empty state | `[Empty state message]` | `Cho biết ngày giờ sinh để kết quả dành riêng cho bạn.` | — |
| Error | `[Error message]` | `Không tải được kết quả lúc này. Thử lại sau vài giây.` | — |
| Headline | `[Screen headline]` | `Ngày tốt tuần này` | — |
| Personalized | `[Greeting]` | — | `Nhật Chủ {{user.nhat_chu}} — hành {{user.hanh}}` |
| Paywall | `[Upgrade CTA]` | `Xem lý do và giờ tốt — cần {{cost}} tín dụng` | `{{cost}}` |

**`{{COPY:context}}` is the exception, not the norm.** Only use when the copy genuinely depends on runtime data that can't be templated.

#### Screen Metadata Block Format

```markdown
## [Screen Name]

**Route:** `/app/[path]`

**Components:**
- [ComponentName] — purpose/usage note
- [ComponentName] — purpose/usage note

**Data:**
| Variable | Source | Default if null |
|---|---|---|
| profiles.display_name | profiles table | "User" |
| items.title | items table | — (required, never null) |

**States:**
- Loading: [exact behavior — e.g. "show skeleton cards in place of each card component"]
- Error: [exact behavior — e.g. "show error banner with retry action, hide main content"]
- Empty: [exact behavior — e.g. "show empty state component with CTA to add first item"]

**Interaction flow:**
1. [Initial state — what user sees on screen load]
2. [User action → result]
3. [Branch condition — e.g. "IF user has saved profile → auto-fill, skip to step 5. ELSE → show input fields."]
4. [User action]
5. [System response — e.g. "IF credits ≥ cost → loading state (D1 dopamine). ELSE → inline paywall."]
6. [Result state — e.g. "Top 3 results slide in. CTA fade in after 2s."]
7. [Exit — e.g. "Tap result → DetailScreen. Tap share → ShareFlow."]

**Navigation:**
- Enters from: [ScreenName] via [exact trigger]
- Exits to: [ScreenName] via [exact trigger]
- Back: [Hardware back / swipe back / disabled]

**Dopamine moment:** [none | D1/D2/D3/D4 — reference EDS §6 by ID]

**Copy slots (production-ready):**
- page_title: "Chọn ngày theo tuổi" — Ambient
- result_primary: "{{result.date}} — {{result.reason_short}}, hợp mệnh {{user.menh}} của bạn" — Decision
- paywall_ask: "Xem kết quả — cần {{cost}} tín dụng. Số dư: {{user.credits}} tín dụng." — Paywall
- error_generic: "Không tải được kết quả lúc này. Thử lại sau vài giây." — Error

**Edge cases:**
- [Specific condition and how the screen handles it]

**Credit cost:** [N credits | free | N/A] — from northstar §5 pricing table

**Mobile Navigation (mode ≠ pwa only):**
- **Tab:** [which tab this screen lives under, or "none" for modals/auth]
- **Depth:** [root tab screen | pushed detail | pushed form]
- **Presentation:** [stack (default) | modal | formSheet]
- **Header:** [default | large-title | transparent | hidden | custom]
- **Gestures:** [swipe-back (default) | pull-to-refresh | swipe-to-delete | none]
- **Transition:** [default | zoom (SDK 55 shared element) | fade]
```

### What Goes Where

| Information | In Make brief appendix | In screen metadata |
|---|---|---|
| Layout and visual hierarchy | ✓ (described for Make) | — |
| Copy text and labels (production-ready) | ✓ (content hierarchy) | ✓ (copy slots with context types) |
| Which shared components are used | — | ✓ |
| Database table.column → variable mappings | — | ✓ |
| Default values for nullable data | — | ✓ |
| Loading/error/empty state behavior | — | ✓ |
| Interaction flow (step-by-step within screen) | — | ✓ |
| Branch conditions (credit check, profile exists) | — | ✓ |
| Navigation enter/exit with exact triggers | — | ✓ |
| Edge cases and constraints | — | ✓ |
| Dopamine moment flag (D1–D4 or none) | — | ✓ |
| Credit cost (paywall gate) | — | ✓ |

### Metadata Quality Rules

**Component references**
- Every component name exactly matches its exported name in `design-system-spec.md` — no paraphrasing
- No component referenced that doesn't exist in the design system spec — flag if missing

**Data variables**
- Every variable maps to an exact `table.column` from the tech spec schema — not a concept
- Source is the actual Supabase table, not "from the database"
- Default value defined for every nullable variable

**Navigation**
- Screen names in "Enters from" and "Exits to" exactly match names used in other screens
- Trigger is the exact UI element — "Tap 'Save' button", not "tap the CTA"

**States**
- Loading state specifies exact component behavior — "show skeleton card", not "show a loading indicator"
- Error state specifies exact recovery action — "show error banner with retry tap target", not "show error"

---

### Output 2 — `## Make build brief` (inside screen specs)

Structured input for the human to use in Make. **Write it as a `## Make build brief` appendix in `artifacts/docs/screen-specs-[app]-v1.md`** — do not create a separate tracked `figma-*.md` file. This is NOT an agent-executable step — the human takes this brief into Make and generates a complete working React app with mock data.

**What Make produces:** A full React + Tailwind app where every button works, every form submits, every list renders — with hardcoded mock data. The frontend agent later swaps these mocks for real Supabase queries.

**After Make:** Human copies ALL files from Make's Code tab into `src/make-import/`.

**Output quality depends entirely on prompt + Guidelines.md quality.** Bad prompt = flat divs. Good prompt + guidelines = production-quality component architecture with Radix UI primitives, typed mock data, proper routing, and animations.

---

#### Section 1 — Guidelines.md (paste into Make custom rules)

Guidelines.md is a persistent instruction file Make reads before EVERY generation. Set this up ONCE at the start of the Make project — it governs all subsequent prompts.

Structure as a routing file pointing to sub-files. Many short files outperform one long file for LLM context.

```markdown
# Guidelines.md

## Design System
Read: @styles.md

## Component Rules
Read: @components.md

## Copy Rules
Read: @copy.md

## Anti-patterns
Read: @anti-patterns.md
```

**styles.md** — from EDS §5:
```markdown
# Styles

## Colors
- Primary/Accent: [hex] — CTAs, active states, links
- Background: [hex] — page background
- Foreground: [hex] — primary text
- Surface: [hex] — cards, panels
- Muted: [hex] — secondary text, borders
- Success: [hex], Danger: [hex], Warning: [hex]

IMPORTANT: Use semantic CSS custom properties (var(--primary), var(--background)) in @theme inline block. Never use raw hex in components.

## Typography
- Headings: [Font family] — [Serif/Sans-serif]
- Body: [Font family] — [Sans-serif for mobile readability]
- Use font-display: swap for all @font-face declarations

## Spacing
- Base unit: 4px. Use multiples: 4, 8, 12, 16, 24, 32, 48, 64
- IMPORTANT: Do not use arbitrary spacing values. Stick to the scale.

## Border Radius
- Cards: [Npx]. Buttons: [Npx]. Inputs: [Npx]. Badges: [Npx].
- IMPORTANT: Do not use uniform border-radius across all elements.

## Dark Mode
- [Yes — generate both light and dark tokens / No — light only]
```

**components.md** — from EDS §4 + §6:
```markdown
# Component Rules

## Structure
- Create separate code folders: screens/, components/ui/, components/, lib/
- IMPORTANT: Never dump everything into App.tsx. Each screen is a separate file.
- Shared components go in components/ui/ (buttons, cards, inputs, badges)
- Screen-specific components stay colocated with their screen file

## Interaction
- All buttons must have visible hover and active states
- All form inputs must have focus ring, error state, and label
- Modals: use Radix Dialog. Dropdowns: use Radix Select. Toast: use Sonner.
- IMPORTANT: Use Radix UI primitives for all interactive components — not raw divs.

## Animation
- Use tw-animate-css for Radix transitions (enter/exit)
- Use motion (Framer Motion) ONLY for dopamine moments — not for every element
- Prefer transform + opacity animations. Never animate width/height.

## States
- Every data-dependent screen must show: loading skeleton, error banner, empty state
```

**copy.md** — from EDS copy formula + copy-rules.mdc:
```markdown
# Copy Rules

## Formula
[Paste copy formula from copy-rules.mdc]

## Language
- All copy in [Vietnamese/English] for [market]
- Address user as "[bạn]". Never "[bạn ấy]" or "[người dùng]".

## Forbidden Words
Never use: [comma-separated list from copy-rules.mdc]

## Forbidden Openings
Never start copy with: [comma-separated list from copy-rules.mdc]
```

**anti-patterns.md** — from EDS §8 + design-system.mdc Slop Guard:
```markdown
# Anti-patterns — NEVER generate these

## Visual
- No gradient backgrounds using purple, violet, or indigo
- No 3-column icon-in-circle feature grids
- No global text-align: center on headings or card content
- No decorative blobs, wavy dividers, or floating shapes
- No emoji as visual design elements
- No colored left-border accent cards as default pattern

## Copy
- No "Unlock the power of...", "Your all-in-one solution for..."
- No urgency language in paywall: "Limited time!", "Act now!"
- No false certainty: "guaranteed", "100% accurate"

## Code
- No inline styles for values that should be tokens
- No unnamed div nesting — every wrapper must have semantic purpose
```

**Native-friendly additions (mode ≠ pwa only):** When the northstar §7c deployment mode is `native` or `pwa-then-native`, append these rules to `components.md`. They don't make Make's output React Native-compatible, but they reduce the hybrid translation rebuild surface:

```markdown
## Native-Friendly Layout Rules
- Prefer flex layouts over CSS Grid for all card arrangements
- Avoid hover-dependent interactions — use click/tap as primary
- Keep component files under 80 lines — extract sub-components
- Use single-column vertical scroll as default page layout
- Design list items as self-contained cards (they become FlashList cells)
- Bottom nav with tabs (maps directly to Expo Router tabs)
- Modals as full-height bottom sheets (maps to presentation: "formSheet")
```

---

#### Section 2 — First Prompt (TC-EBC Framework)

The first prompt is the highest-leverage prompt. Front-load detail here — fixing with follow-ups costs 3-5x more prompts.

**TC-EBC structure:**

```
TASK: Build a [app type] called [name] with [N] screens: [list screen names]

CONTEXT: [One paragraph — who uses this, why, and the core action]
Target audience: [from northstar §2 — named archetype]
Platform: Mobile-first PWA, 375px baseline width
Visual register: [from EDS §5 — e.g. "Premium-warm, calm, not corporate"]

ELEMENTS (per screen):
[Screen 1 — Name]:
- [Element 1: e.g. "Header with back arrow + title + credit balance badge"]
- [Element 2: e.g. "7-day horizontal date selector, today highlighted"]
- [Element 3: e.g. "Result card: score circle (animated), date, one-line reason"]
- [Element 4: e.g. "CTA button: 'Xem chi tiết — 5 tín dụng'"]

[Screen 2 — Name]:
- [Elements...]

[Repeat for all screens]

BEHAVIOR:
- Bottom navigation bar with [N] tabs: [Tab1], [Tab2], [Tab3]
- All screens scroll vertically, no horizontal scroll
- Back navigation via header back arrow
- Forms validate on blur + submit
- [Specific interactions: e.g. "Date selector scrolls horizontally, tapping a date updates result cards below"]

CONSTRAINTS:
- Vietnamese language for all UI copy — use realistic mock data, not lorem ipsum
- Mock data must use property names matching database columns: displayName, creditBalance, createdAt
- Include 3-5 items in every list to test visual density
- Credit prices from northstar: [list feature → price mappings]
- Use Radix UI for all interactive components (Dialog, Select, Tabs, etc.)
- Generate separate files per screen — do NOT put everything in App.tsx
```

---

#### Section 3 — Revision Prompts (Target / Change / Maintain)

Every follow-up prompt must signal what should and shouldn't change. Without this, Make rewrites large portions unnecessarily.

**Template:**
```
TARGET: [Screen name] — [specific element]
CHANGE: [What to change — e.g. "Replace the horizontal card layout with vertical stacked cards"]
MAINTAIN: [What must NOT change — e.g. "Keep the color scheme, header, bottom nav, and all other screens exactly as they are"]
```

**Examples:**
```
TARGET: HomeScreen — result cards section
CHANGE: Add a loading skeleton state that shows 3 gray placeholder cards while data loads
MAINTAIN: All existing card designs, colors, spacing, and other sections untouched

TARGET: PaywallModal — CTA button
CHANGE: Add microcopy below the button: "Không cam kết • Huỷ bất cứ lúc nào"
MAINTAIN: Button style, modal layout, blur overlay, all other copy
```

**Point and Edit** — for visual tweaks (color, spacing, typography, border radius), use Make's Point and Edit tool instead of re-prompting. Select the element in preview → adjust visually. Saves prompts for structural changes.

---

#### Section 4 — Make brief output template (paste under `## Make build brief` in screen specs)

```markdown
# Visual build brief (Make) — [App Name]

## Guidelines.md Setup

Before the first prompt, create these files in Make's guidelines folder:
- guidelines/Guidelines.md (routing file — see Section 1 above)
- guidelines/styles.md
- guidelines/components.md
- guidelines/copy.md
- guidelines/anti-patterns.md

Content for each file is specified below.

### styles.md content:
[Generated from EDS §5 — brand colors, typography, spacing, border radius, dark mode]

### components.md content:
[Generated from EDS §4 + §6 — structure rules, interaction rules, animation rules]

### copy.md content:
[Generated from copy-rules.mdc — formula, language, forbidden words]

### anti-patterns.md content:
[Generated from EDS §8 + design-system.mdc — visual, copy, and code anti-patterns]

## First Prompt (copy-paste into Make)

[TC-EBC formatted prompt with all screens, elements, behaviors, and constraints]

## Revision Prompts (use after first generation)

After reviewing Make's first output:
1. [TARGET/CHANGE/MAINTAIN for first fix]
2. [TARGET/CHANGE/MAINTAIN for second fix]
[Add as needed — budget 10-15 revision prompts max per project]

## Mock Data Guidance

Make will generate mock data for all screens. Structure this mock data to match the real schema shape:
- Use realistic Vietnamese names, dates, and values (not "Lorem ipsum")
- Use property names that map naturally to database columns (e.g. `displayName`, `creditBalance`, `createdAt`)
- Include 3–5 items in lists to test visual density
- Include realistic prices and credit costs matching northstar §4

The tech spec agent reads these mock structures to derive the database schema. Better mocks = smoother integration.

## Prompt Budget

Professional plan: ~50-70 prompts/month. Budget per RAD project:
- First prompt (structural): 1 prompt — get this right
- Screen iterations: 5-10 prompts — use TARGET/CHANGE/MAINTAIN
- Visual polish: use Point and Edit tool — free, no prompt cost
- Total target: 10-15 prompts per project, saving credits for iterations
```

---

## Recommended Build Order

After scoping, recommend the build order for feature workstreams. If the northstar §12 (Feature Grouping) defines waves, use that structure directly. Otherwise, group by dependency:

```
Wave 1 — Foundation + Auth + Landing Page:
  Auth screens, profile/onboarding, payment infrastructure, landing page
  (Landing page is built first in Frontend Foundation — validates theme + components immediately)
  (Must complete before any feature requiring an authenticated user)

Wave 2 — Core Loop:
  Primary user action screens — the screens that deliver the core value proposition
  (Must be ≥50% of product screens)

Wave 3 — Personalization + Retention:
  Screens that deepen engagement, require core loop data to exist

Wave 4 — Social + Specialty:
  Sharing, viral mechanics, secondary features
```

If northstar §13 (User Scenarios) is present, validate: does the wave order allow each scenario to be completed end-to-end within its wave, or does a scenario cross wave boundaries? Cross-boundary scenarios indicate a missed dependency.

---

## Quality Check

### Scope plan
- **Pass 1 completed** — every feature decomposed into screens using the decomposition patterns table
- **Commonly Forgotten Screens** checklist reviewed — every row marked "include" or "N/A" with reason
- **Completeness Gate passed** — every user scenario walkable, every CRUD path has screens, every nav path exists
- **Pass 2 applied** — anti-bloat rules checked AFTER enumeration, not before
- Category budgets respected — core loop ≥50% of product screens (excluding infrastructure)
- **Total screen count ≥20** — under 20 triggers re-review of Pass 1 decomposition
- Not Building section populated with specific feature names
- Landing page included in scope plan with all 8 sections from the section stack spec
- Landing page copy is production-ready from northstar §7b — not placeholder

### Screen metadata
- Every screen in the scope plan has a metadata block — no missing screens
- Every metadata block has **production-ready copy** — no `[label]` placeholders
- All copy strings pass the 5-question Copy Quality Test from the EDS
- Dynamic values use `{{variable}}` tokens, not hardcoded sample data
- `{{COPY:context}}` tokens used only for genuinely runtime-dependent copy
- Routes defined for every screen — using `/app/[path]` convention
- **Interaction flow defined** — step-by-step within-screen sequence including branch conditions
- Copy slots are production-ready strings tagged with context type (Decision / Confirmation / Empty / Error / Paywall / Ambient)
- All navigation paths explicit — no "goes to next screen"
- Empty state defined for every data-dependent component
- All data variables map to exact `table.column` names
- Default values defined for every nullable variable
- Dopamine moment field set on every screen — `none` or specific D[N] ID from EDS §6
- Credit cost field set on paywall-gated screens — matches northstar §5 pricing table

### Make build brief (appendix in screen specs)
- Guidelines.md structure defined — styles.md, components.md, copy.md, anti-patterns.md all populated
- styles.md includes OKLCH/hex brand colors, typography, spacing scale, border radius, dark mode from EDS §5
- anti-patterns.md includes both EDS §8 and design-system.mdc Slop Guard rules
- First prompt follows TC-EBC structure: Task, Context, Elements (per screen), Behavior, Constraints
- First prompt includes ALL screens with element-level content hierarchy — not vague descriptions
- Constraints include: Vietnamese copy, realistic mock data property names, credit prices, Radix UI, separate files
- Revision prompts use TARGET/CHANGE/MAINTAIN pattern — not open-ended "fix this"
- Prompt budget planned: ≤15 prompts per project
- Every screen in the scope plan has a brief entry with content hierarchy
- Content hierarchy matches the metadata block's component and data structure
- Build order matches feature grouping from northstar §12

### Cross-screen consistency
- Screen names consistent across all metadata blocks
- Navigation graph complete — every "Exits to" has a corresponding "Enters from"
- No orphaned screens — every screen reachable from at least one other

### Cursor-readiness
- Every screen has a unique, exact functional name ("DashboardScreen", not "Home Screen 2")
- Every navigation path names both the trigger and destination by exact name
- All data placeholders are realistic — "3 items" not "N items"
- Every screen with multiple user actions has an interaction flow with explicit branch conditions
- Paywall gates specify: what partial result is shown free, what is behind the gate, exact credit cost
- Copy slots tagged with context type — frontend agent knows which copy-rules.mdc context applies
