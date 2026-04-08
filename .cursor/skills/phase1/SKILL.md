---
name: phase1-northstar-eds-writer
description: Reference template for Phase 1 artifacts — northstar onepager (HTML), emotional design system (.md), and copy rules (.mdc). Phase 1 is produced externally (Claude.ai, Gemini, or any collaborative tool) using this file as the specification. Share this template with the external tool to ensure all 12 required sections are covered. Cursor validates the result via /office-hours — it does not produce Phase 1 artifacts.
disable-model-invocation: true
---

# Phase 1 — Northstar + Emotional Design System

Phase 1 produces three artifacts in a single session. The EDS derives entirely from the northstar — there is no reason to context-switch between them.

**Session flow:**
1. Gather inputs → draft northstar → human reviews
2. Pressure-test the northstar → confirm HOLD mode
3. Without closing the session, generate both EDS outputs from the approved northstar
4. Human reviews EDS tone calibration — one revision round max
5. All three files committed before proceeding to Phase 2

| Output | Format | Committed? | Audience | Used in |
|---|---|---|---|---|
| Northstar onepager | HTML | Yes | Human — single source of truth for business concept | Every downstream phase |
| `emotional-design-system.md` | Markdown or branded HTML | Yes | Human writing Make prompt copy | Reference during Phase 2 screen planning + Make brief |
| `.cursor/rules/copy-rules.mdc` | .mdc | Yes | Cursor | Auto-loads on `src/**/*.tsx` during screen builds |

**Format flexibility rule:** Phase 1 is often produced outside this template — in Claude.ai, Gemini, or a separate creative process. The northstar and EDS may arrive as branded HTML files instead of plain markdown. This is acceptable and often preferable (branded presentation builds stakeholder confidence).

**However:** Regardless of EDS format (markdown or HTML), `.cursor/rules/copy-rules.mdc` **must always be produced as a separate file**. The .mdc is the machine-readable extract that Cursor auto-loads during screen builds. If the EDS is a self-contained HTML document that embeds copy formula, screen-context rules, forbidden patterns, and the quality test inline, those sections must be **duplicated** into the .mdc — the .mdc is not optional even when the EDS is comprehensive.

**Content overlap rule:** EDS sections covering copy formula, screen-context rules, forbidden patterns, and the copy quality test appear in **both** the EDS document (for human reference) **and** the .mdc file (for Cursor). The EDS is the authoritative source; the .mdc is the operational extract. When they diverge, update both — the .mdc must never drift from the EDS.

---

## Before You Write

Extract or ask for:
- **App name and domain** (if known)
- **The problem** — what specific daily friction does this solve?
- **The primary user** — who exactly? Not a demographic, a person with a name and a situation
- **The core action** — what is the single thing the user does in this app?
- **Revenue model** — how does money flow?
- **Moat** — what makes this defensible over time?
- **Auth approach** — how does the user sign in? Anonymous-first? Phone? Email? OAuth?
- **External dependencies** — any APIs, engines, or third-party services the app relies on?
- **Payment provider** — Stripe? PayOS? Regional provider? (affects webhook architecture)
- **Target market** — Tier 1 English-speaking? Vietnam B2C? (affects auth providers, payment, copy language)

If the user has a rough idea but hasn't fully thought through revenue or moat, work through it before writing. A northstar with a blank moat section produces a tech spec with no architectural constraints — which produces a generic app.

**Additional inputs for EDS** — ask only if not inferable from the northstar:
- **Brand colors** — any existing palette, or derive from product category and emotional register?
- **3 products in adjacent categories whose tone you admire** — calibrates the register
- **3 tone anti-patterns to explicitly avoid** — prevents drift
- **Is there an existing brand voice, or built from scratch?**
- **Dark mode required for v1?**

---

# Part A — Northstar Onepager

The northstar is the first artifact built and the last one changed. Every downstream artifact — design system, screen specs, tech spec — derives answers from it. Its job is to lock the business concept, target user, revenue model, and moat with enough precision that no downstream artifact needs to re-examine these questions.

## Required Sections

Every northstar must contain all twelve sections. Do not omit, combine, or rename them — downstream skills reference these sections by name. Sections 1–7 are the core business concept. Sections 8–12 are technical context that prevents downstream agents from hallucinating architecture decisions.

### 1. The Problem
A single, concrete paragraph describing the daily friction the product removes. Written from the user's perspective, not the product's. No solution language — only the problem.

**Extraction test:** Can the EDS section of this skill derive the core emotional thesis from this section alone? If yes, it's specific enough.

### 2. Primary User (Named Archetype)
A named, specific person. Not "working mothers aged 30–45" but a character: name, age, occupation, the specific moment in their day when the problem occurs, and the emotional state they're in when it occurs.

**Extraction test:** Can the EDS section derive the persona's psychological profile from this section? If yes, it's specific enough.

### 3. The Solution
One paragraph describing what the app does — the core loop only, no feature list. Written as the user experiences it, not as a technical description.

**Extraction test:** Can Phase 2 screen planning derive the full screen list from this section? If yes, it's specific enough.

### 4. Revenue Model
How money flows — pricing model, price point, payment trigger, and the revenue at scale. Must include:
- Pricing model (perpetual license / subscription / freemium / affiliate / etc.)
- Price point (specific number, not a range)
- Payment trigger (what action prompts the payment ask?)
- Revenue math at scale (e.g. 1,000 paying users × $X = $Y/month)

**Extraction test:** Can the tech spec writer derive the monetization screens from this section? If yes, it's specific enough.

### 5. Core Value Proposition
One sentence. The specific, quantifiable benefit delivered to the named user. Not a tagline — a precise statement of the exchange of value.

Formula: `[App name] helps [named archetype] [do specific thing] so that [specific outcome], without [the friction they currently experience].`

### 6. Competitive Moat
What makes this defensible 12–24 months after launch. Must be one of:
- Data moat (proprietary data that improves with usage)
- Network moat (more valuable as more users join)
- Switching cost moat (accumulated user data that's painful to leave)
- Distribution moat (owned channel with low CAC)
- Brand moat (category-defining positioning)

State which type, then describe specifically how the product builds it.

**Extraction test:** Can the tech spec writer identify architectural decisions that support the moat? If yes, it's specific enough.

### 7. Build Scope
A single table listing what ships in this build. Everything is in scope — no tiers, no phases. The table is organized by function, not by build order.

| Function | What ships | Business outcome |
|---|---|---|
| Core loop | [Primary user action end-to-end] | [What this proves] |
| Retention | [What brings users back] | [What this proves] |
| Monetization | [How money flows] | [What this proves] |
| Landing page | Single conversion page: hero → features → social proof → CTA → install PWA | Organic acquisition + viral share link destination + paid ad landing |

**The landing page is mandatory.** It serves three acquisition channels: organic SEO (Google search), viral share links (Zalo/Facebook → landing page → install), and paid ads (Facebook/TikTok → landing page → install). Without it, the PWA has no discoverability surface.

### 7b. Landing Page Content
Content for the landing page must be defined in the northstar — the screen planning agent needs it for the Figma Make brief.

- **Headline:** One sentence with a specific benefit and number
- **Subheadline:** Clarifies the audience in one line
- **Target keywords:** 3–5 keywords + non-diacritic variants for SEO
- **Trust signals to display:** User count, star rating, media/partner logos
- **CTA copy:** Primary button text + microcopy below CTA
- **FAQ items:** 4–6 questions the target user would ask. These become FAQ JSON-LD structured data for rich results.
- **Social proof quotes:** 2–3 real or realistic testimonials with name, age, profession, city

**Extraction test:** Can the Figma Make brief include every copy string on the landing page using only this section? If yes, it's specific enough.

### 8. Not Building
Features explicitly excluded from this version. Agents pattern-match against this list to reject scope creep — every entry must be a specific named feature, not a vague category.

- [Feature] — [one-line reason for exclusion]

**Known shortcuts** (deliberate trade-offs — not bugs):
- [Shortcut] — acceptable for v1

**Extraction test:** Can the tech spec writer copy this list directly into Section 17 (Not Building) without rewording? If yes, it's specific enough.

### 9. Auth Model
How users authenticate. This prevents the screen planning agent from guessing login screens and the backend agent from guessing the auth provider.

Must include:
- **Anonymous vs. authenticated:** Can the user do anything before signing up? What triggers account creation?
- **Auth method:** Phone OTP / email+password / magic link / OAuth (which providers?) / anonymous-first → upgrade
- **Why this method:** One sentence linking the auth choice to the primary user's context
- **Profile data stored:** What is saved on the profile beyond email/phone?
- **Session behavior:** Persistent / expires after X / refresh token

**Extraction test:** Can the screen planning agent build the complete auth flow (login, signup, forgot password, profile) without asking any questions? If yes, it's specific enough.

### 10. External Integrations
Every external API, SDK, or service the app depends on. This prevents the tech-spec agent and research agent from hallucinating API contracts.

For each integration:
- **Name and type:** Self-hosted API / third-party SaaS / open-source library
- **What the app uses it for:** Specific features, not "data processing"
- **Auth method:** API key / OAuth / JWT / public
- **Env vars needed:** Variable names and scope (server-only vs client-safe)
- **Latency/rate limit notes:** If known — affects architecture decisions

**Extraction test:** Can the research agent skip researching integrations that are fully documented here? If yes, it's specific enough.

### 11. Payment Integration
Which payment provider and method.

Must include:
- **Provider:** Stripe / PayOS / MoMo / manual bank transfer / other
- **Payment methods supported:** Credit card / bank transfer / e-wallet / QR code
- **Integration pattern:** Checkout redirect / embedded form / in-app purchase
- **Webhook events needed:** What events trigger credit/subscription updates
- **Env vars:** Variable names (server-only)
- **Test mode details:** How to test payments during development

**Extraction test:** Can the tech spec writer create the complete payment API contract without researching the provider? If yes, it's specific enough.

### 12. Feature Grouping (Build Waves)
How features group into build waves for the `/setup` build plan.

| Wave | Features | Depends on |
|---|---|---|
| Foundation | Auth + profile + payment infrastructure | — |
| Wave 1 | [Core loop features — what must work first] | Foundation |
| Wave 2 | [Features that depend on Wave 1 data] | Wave 1 |
| Wave 3 | [Retention, social, specialty features] | Wave 2 |

Optional but recommended:
- **Scale target (v1):** DAU month 3, concurrent peak, estimated DB rows year 1
- **Push notifications:** Provider (FCM / Web Push / none), trigger list, opt-in timing
- **Share/distribution mechanics:** How results are shared (if viral loop exists)

**Extraction test:** Can the `/setup` command generate `build-plan.md` wave structure directly from this section? If yes, it's specific enough.

### 13. User Scenarios (recommended for B2C products)
3–8 concrete walkthroughs of the named archetype using the app over time. Each scenario is a specific life moment — not an abstract user journey.

For each scenario:
- **Trigger moment:** What real-life event causes the user to open the app?
- **Steps with feature/endpoint tags:** Exact sequence of screens and actions
- **Credit/cost balance:** Track running credit balance across scenarios
- **Outcome:** What the user gained (emotional + practical)
- **Viral loop (if applicable):** How this scenario leads to new user acquisition

**Extraction test:** Can the screen planning agent trace the complete navigation path for each scenario? Can the tech-spec writer verify that every endpoint tagged in the scenarios exists in the API contract? If yes, the scenarios are specific enough.

## Northstar Output Format

Output as a single `.html` file. Clean, minimal, readable in any browser with no dependencies.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[App Name] — Northstar</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #1a1a1a; }
    h1 { font-size: 1.75rem; font-weight: 700; margin-bottom: 0.25rem; }
    h2 { font-size: 1.125rem; font-weight: 600; margin-top: 2rem; color: #444; text-transform: uppercase; letter-spacing: 0.05em; }
    p { margin: 0.5rem 0 1rem; }
    table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
    th, td { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid #e5e5e5; }
    th { font-weight: 600; background: #f9f9f9; }
    .meta { color: #666; font-size: 0.875rem; margin-bottom: 2rem; }
    .value-prop { font-size: 1.125rem; font-style: italic; padding: 1rem; background: #f5f5f5; border-left: 3px solid #333; }
  </style>
</head>
<body>
  <h1>[App Name]</h1>
  <p class="meta">Northstar v[version] — [date]</p>

  <h2>The Problem</h2>
  <p>[Content]</p>

  <h2>Primary User</h2>
  <p>[Content — named archetype with full context]</p>

  <h2>The Solution</h2>
  <p>[Content]</p>

  <h2>Revenue Model</h2>
  <p>[Pricing model, price point, payment trigger]</p>
  <p><strong>Revenue math:</strong> [X users × $Y = $Z/month at scale]</p>

  <h2>Core Value Proposition</h2>
  <p class="value-prop">[Single sentence using the formula]</p>

  <h2>Competitive Moat</h2>
  <p><strong>Moat type:</strong> [Type]</p>
  <p>[How the product builds it specifically]</p>

  <h2>Build Scope</h2>
  <!-- Build Scope table + Landing Page Content + Not Building + Auth + Integrations + Payment + Feature Grouping + Scenarios -->
</body>
</html>
```

## Northstar Quality Check

Before proceeding to pressure-test:
- All twelve required sections present — no section omitted or merged
- Section 13 (User Scenarios) present if B2C product — recommended, not mandatory
- Primary user has a name, age, occupation, and a specific moment of friction — not a demographic
- Revenue model has a specific price point — not a range or "TBD"
- Moat type is named explicitly — not described without being categorised
- Core value proposition follows the formula — not a tagline
- Build Scope table covers core loop, retention, monetization, AND landing page — nothing deferred
- Landing page content section has headline, keywords, trust signals, CTA copy, FAQ items, and social proof
- Not Building is a standalone section with specific feature names — not "advanced features" or vague categories
- Auth model specifies exact method — not "TBD" or "standard auth"
- External integrations table has env var names for every service — no unnamed dependencies
- Payment provider named with webhook events listed — not just "payments"
- Feature grouping maps to build waves — setup agent can generate build-plan.md directly
- If scenarios present: every scenario tracks credit balance, tags features/endpoints, and navigation path is traceable by screen planning agent

---

## Northstar Pressure-Test

Run this challenge pass before generating the EDS. It takes 5–10 minutes and catches scope-of-ambition errors before they propagate through every downstream artifact.

**Premise challenge**
- Is this the right problem to solve? Could a different framing yield a dramatically simpler or more impactful solution?
- What is the actual user outcome? Is the northstar describing the most direct path to that outcome, or is it solving a proxy problem?
- What happens if we ship nothing? Is this a genuine daily pain point or a hypothetical one?

**10x check**
- What version of this product is 10x more valuable for 2x the build effort? Describe it in one paragraph.
- Does the current northstar describe the obvious implementation, or the best product?
- What adjacent capability — added in under a day — would make users say "they thought of everything"?

**Dream state mapping**
```
CURRENT STATE          →    THIS PRODUCT           →    12-MONTH IDEAL
[user's friction now]       [what ships in v1]          [what the product becomes]
```
Does v1 move toward the 12-month ideal, or does it create path dependencies that make the ideal harder to reach?

**Temporal interrogation** — what decisions will the builder hit during construction?
- Hour 1 (foundations): What schema or auth decisions need to be locked now?
- Hours 2–4 (core loop): What ambiguities in the solution section will surface during build?
- Hours 5–7 (retention + monetization): What assumptions about user behaviour need to be true for these to work?
- Post-launch: What is the first thing users will ask for that isn't in scope?

**Mode selection** — before proceeding to EDS generation, confirm which mode applies:
- **EXPANSION** — the core idea is right but the scope is too conservative. Push the northstar to describe the more ambitious version before proceeding.
- **HOLD** — scope and ambition are correct. Proceed to EDS generation.
- **REDUCTION** — the northstar is overbuilt. Cut to the minimum version that proves the core thesis.

If EXPANSION: revise the Build Scope table before proceeding. If REDUCTION: move cut items to Not Building. If HOLD: proceed to EDS generation immediately — do not close the session.

---

# Part B — Emotional Design System

Once the northstar is approved and pressure-tested, generate both EDS outputs in the same session. Extract everything from the northstar — do not ask for information already there.

## Output 1 — `emotional-design-system.md`

Eight sections. Strategic reference only — does not feed Cursor directly. Specific enough that any human can write on-brand screen copy without interpretation, and any agent can implement the visual identity without asking design questions.

### Section structure:

1. **Core Emotional Thesis** — one paragraph: the emotional transformation the product creates, using the formula: "[App name] exists to transform [named user] from [before state] to [after state]. The primary feeling we create is [emotion], delivered through [mechanism]."

2. **Emotional Layers (Priority Order)** — numbered 1–3, highest priority wins when layers conflict in a design decision.

3. **Primary User Persona** — name, core identity, daily context, what they notice, what they share, what breaks trust.

4. **Design Principles** — 6 or fewer, each an actionable imperative (not a value statement), applicable as a binary yes/no test to any design decision.

5. **Visual Direction** — brand palette with OKLCH values, semantic colors, visual register, typography direction, iconography, dark mode decision.

6. **Dopamine Moments** — 3–5 specific peak emotional moments with screen, trigger, emotion target, mechanism (loading/reveal/highlight), duration, and post-moment rules. Plus No-Dopamine Zones.

7. **Copy Slot Inventory** — pre-defined copy strings for recurring patterns (decision, confirmation, empty, error, paywall, ambient).

8. **Forbidden Patterns** — forbidden words, forbidden openings, forbidden design patterns, forbidden behaviors.

## Output 2 — `.cursor/rules/copy-rules.mdc`

Operational rules. Auto-loads on every `src/**/*.tsx` file during screen builds. Every section filled with specific, project-specific content — no placeholders.

Sections: Copy Formula, Forbidden Opening Words, Forbidden Words, Screen-Context Copy Rules (7 contexts: decision, confirmation, empty, error, onboarding, ambient, paywall), Copy Quality Test (5 binary questions), Hard Rules.

---

## Phase 1 Quality Check

### Northstar
- All twelve required sections present
- Section 13 present if B2C
- Primary user has a name, age, occupation, specific friction moment
- Revenue model has specific price point
- Moat type named explicitly
- Core value proposition follows the formula
- Build Scope covers core loop, retention, monetization, AND landing page
- Landing page content has all required fields
- Not Building has specific feature names
- Auth model specifies exact method
- External integrations have env var names
- Payment provider named with webhook events
- Feature grouping maps to build waves

### EDS
- Core emotional thesis follows the structure formula
- Emotional layers numbered in strict priority order
- Design principles use imperative verbs
- Visual Direction includes OKLCH brand palette
- Dopamine Moments have specific animation timings
- Copy Slot Inventory covers all recurring patterns
- Forbidden Patterns in discrete lists

### copy-rules.mdc
- No placeholders — all sections filled with real content
- Copy formula is a template with named elements
- Forbidden words in discrete comma-separated list
- Screen-context examples use real variable names
- Copy quality test has exactly five binary questions
- Language and market specified in Hard Rules

### Extraction-Readiness
- Visual Direction → Figma Make brief + Foundation CSS tokens
- Copy formula + screen-context → Phase 2 screen planning
- Revenue model → Phase 4 payment schema
- Moat → Phase 4 architectural decisions
- Not Building → Phase 4 Section 17 (copy directly)
- Auth Model → Phase 4 Section 11 (extract directly)
- Feature Grouping → `/setup` build waves
- copy-rules.mdc → auto-loads during screen builds
