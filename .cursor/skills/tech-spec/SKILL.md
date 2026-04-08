---
name: tech-spec
description: Complete Phase 4 instructions — tech spec output format covering functional/non-functional requirements, shared types, external integrations, data model, data access layer, API contracts, auth, env vars, LLM usage, AI module inventory, cron jobs, email flows, and quality checks. Read this when running /phase4.
disable-model-invocation: true
---

# Phase 4 — Tech Spec Writer

The tech spec is the single source of truth for technical decisions. Two jobs: give the build agents enough context to build without guessing, and make the Not Building section explicit enough that agents never build excluded features.

**Output:** `artifacts/docs/tech-spec.md`

---

## Before You Write

### Step 0 — Complexity scan + selective research

Read `.cursor/skills/architecture/SKILL.md` and scan the northstar features against the **Technical Complexity Signals** (Section 1). For each feature, check:

| Signal category | Triggered? | Feature |
|---|---|---|
| Money / Credits | | |
| Real-Time | | |
| File Processing | | |
| Complex Authorization | | |
| Search / Filtering | | |
| State Machines | | |

**For each triggered signal:** Dispatch the Research Agent in Mode 2 (technical pattern research):

```
Task: Technical Pattern Research — [Feature Name]

Research the correct implementation pattern for [feature description] on the RAD stack
(Supabase Postgres + Edge Functions + React Router v7 SPA).

Complexity signal: [signal from architecture skill]
Specific question: [e.g., "How should concurrent credit deductions be handled?"]
Northstar context: [relevant sections from northstar]

Read .cursor/skills/architecture/SKILL.md Section 3 for reference patterns.
Output to: artifacts/integrations/pattern-[feature-name].md
```

**For features with no triggered signals:** Skip research. Standard CRUD on Supabase doesn't need investigation — the Tech Lead's training data is sufficient.

**Read research outputs before writing the tech spec.** Every `artifacts/integrations/pattern-*.md` file feeds directly into the schema design (Section 8), Edge Function contracts (Section 10), and technical decisions.

Also check `.cursor/skills/architecture/SKILL.md` Section 3 (Domain Reference Patterns) — if the domain matches a reference pattern (credit billing, subscriptions, multi-tenant, social feed), compare the proposed approach against the reference before writing.

### Step 1 — Data invariants

Before designing the schema, enumerate the data invariants the system must enforce. These come from the northstar and domain knowledge — not from mock data shapes.

**Extract invariants from the northstar and domain:**

For each core entity, state what must always be true:

```markdown
## Data Invariants

### Credits / Billing
- A user's credit balance must never go negative
- Every credit change must have a corresponding transaction record
- A purchase must be idempotent (webhook retries must not double-charge)

### User Data
- A user can have exactly one active profile
- Profile birth_date is immutable after first set
- [domain-specific invariants from northstar]

### Core Entity
- [entity] must always have a valid [foreign key]
- [entity] status transitions: draft → active → completed (no backward transitions)
- [business rule from northstar]
```

**Why invariants first:** Invariants drive schema design decisions — CHECK constraints, unique indexes, trigger functions, RLS policies. If you design the schema from mock data shapes alone, you get structurally correct tables that don't enforce business rules.

### Step 2 — Extract from context

The tech spec must not re-derive what the northstar already defines:

**From `artifacts/docs/northstar-[app].html`:**
- App name, one-line description, primary user — §1–2
- Revenue model with specific pricing — §4 (drives payment schema and API contracts)
- Landing page content — §7b (headline, keywords, FAQ items → Section 18 metadata, JSON-LD, SEO keywords)
- Not Building list — §8 (copy directly into Section 17 — do not rewrite or soften)
- Auth model — §9 (exact method, anonymous-first behavior, account trigger, profile data, session rules → Section 11)
- External integrations — §10 (integration names, auth methods, env vars, endpoint names → Section 5 and 12)
- Payment provider — §11 (provider name, payment methods, webhook events, env vars → Sections 5, 8, 10, 12)
- Feature grouping / build waves — §12 (scale targets if present → Section 3 NFRs; push notification spec if present → Section 15)
- User scenarios — §13 (if present: cross-check every endpoint tagged in scenarios against Section 10 API contracts; verify every data variable against Section 8 schema)

**From `artifacts/docs/screen-specs-[app]-v1.md`:**
- Every screen's data variables and states — from metadata blocks
- Interaction flows with branch conditions — from metadata blocks (credit checks, profile-exists gates, paywall triggers → validate against API contracts)
- Component inventory — determines if animation libraries are needed
- Copy slots with context types — confirms which screens have paywall gates (drives payment API contracts)
- Credit cost per screen — from metadata blocks (confirms pricing table alignment)

**From `src/make-import/` (Figma Make code output):**
- Mock data structures — Make's hardcoded arrays and objects define the exact data shapes the frontend expects. Read these before designing the schema.
- Schema MUST produce query results matching Make's mock data shapes. Column names should match mock object property names where possible.
- If a mock shape requires transformation (denormalized, computed fields), document the transformation in the API contract or as a database view.
- Mock auth patterns — reveal which screens assume authentication and what user data they expect.

**When Make's mock data conflicts with the northstar:** The northstar is authoritative for _what data exists_ (columns, relationships, entities). Make is authoritative for _what the frontend renders_ (which fields are displayed, their names in the UI). If the northstar defines fields Make doesn't display, add them to the schema anyway — they may be used by Edge Functions, cron, or future features. If Make displays fields the northstar doesn't mention, flag for Tech Lead review before adding to the schema.

**From `artifacts/docs/emotional-design-system.md`:**
- Brand context and copy register — for writing user-visible error messages and copy in API responses
- Dopamine Moments from EDS §6 — if animations require motion or react-countup, list in Tech Stack §6

**From `artifacts/integrations/`:**
- Integration research docs (one per external service) — for services NOT fully documented in northstar §10. If the northstar §10 already provides endpoint names, auth method, and env vars, the research doc supplements but does not override.

**Standard stack (unless northstar overrides):**
- React Router v7 (Vite) · Tailwind CSS · Supabase (DB + Auth + RLS + Edge Functions) · TanStack React Query (caching + state) · Vercel
- LLM via OpenRouter (all RAD apps use LLM for data interpretation/reasoning — specify model e.g. anthropic/claude-sonnet-4)
- Monthly LLM cost ceiling

---

## Output Format

````markdown
# Tech Spec — [App Name]
**Version:** 1.0
**Last updated:** [date]

---

## 1. Overview
One paragraph: what the app does, primary user, core value proposition.
Pull directly from the northstar if available.

## FE-BE Connection — Quick Reference
*Pointers to where each concern is defined.*

| Concern | Where to look |
|---|---|
| Functional requirements (what the app does) | Section 2 — Functional Requirements |
| Non-functional requirements (performance, scale) | Section 3 — Non-Functional Requirements |
| Shared TypeScript types | Section 4 — Shared TypeScript Interfaces → `src/lib/api-types.ts` |
| External integration patterns and SDK usage | Section 5 — External Integrations |
| Client-side data hooks and query functions | Section 9 — Data Access Layer → `src/hooks/` and `src/lib/data/` |
| Edge Function contracts (webhooks, cron, email) | Section 10 — API Contracts |
| Standard error handling shape | Section 10 — Standard Error Response Shape |
| Auth flow | Section 11 — Auth & Security Model |
| Per-screen data mappings | Screen spec metadata in `screen-specs-[app]-v1.md` |
| Env vars frontend can access vs Edge Function secrets | Section 12 — Environment Variables (`VITE_` = client-safe) |
| Shared hooks (useAuth, useProfile, etc.) | Built in Foundation — see `src/hooks/` |
| SEO metadata, OG images, PWA manifest, service worker | Section 18 — SEO & PWA Infrastructure |
| Install prompt hook (useInstallPrompt) | Section 18 → `src/hooks/useInstallPrompt.ts` |

## 2. Functional Requirements

What the app does, organized by feature area. Written as user-observable capabilities — not implementation details.

| # | As a [user] | I can... | Acceptance signal |
|---|---|---|---|
| FR-01 | [user type] | [capability] | [what done looks like] |
| FR-02 | | | |

**Grouping:** Organize rows by feature area (e.g., Auth, Core Loop, Billing). Feature areas must map directly to workstreams in the build plan.

**Scope rule:** Every row in this table must be in scope. If a capability was explicitly excluded in the northstar §8 (Not Building), it belongs in Section 17, not here.

**Scenario validation (if northstar §13 present):** Every step tagged with a feature/endpoint in the user scenarios must have a corresponding FR row. If a scenario step has no matching FR, either the FR is missing or the scenario describes an out-of-scope action — resolve before proceeding.

## 3. Non-Functional Requirements

| Category | Requirement | Target |
|---|---|---|
| Performance | Initial page load (LCP) | < 2.5s on 4G |
| Performance | Time to interactive (TTI) | < 3.5s on 4G |
| Scale | Concurrent users (v1) | [from northstar §12 if specified, else estimate from user scenarios] |
| Scale | Database rows per core table (v1) | [from northstar §12 if specified, else estimate from revenue model] |
| Availability | Uptime target | 99.9% (Vercel SLA) |
| Error handling | Unhandled server errors | Logged to console; user sees generic error banner |
| Accessibility | WCAG compliance | AA |
| Security | Auth required on all user data routes | Enforced via Supabase RLS |
| Security | Secrets | Never in client bundle; never in version control |

*Add rows relevant to this app; omit rows that don't apply.*

## 4. Shared TypeScript Interfaces

All shared types live in `src/lib/api-types.ts`. Define the canonical shape for every database entity and API response.

```typescript
// src/lib/api-types.ts

// ─── Database entities ───────────────────────────────────────────────────────

export interface [EntityName] {
  id: string
  created_at: string
  user_id: string
  // [fields matching the database schema exactly — same names, compatible types]
}

// ─── API request / response shapes ──────────────────────────────────────────

export interface [ActionName]Request {
  [field]: [type]
}

export interface [ActionName]Response {
  [field]: [type]
}

// ─── Client-safe view types (subset of entity, safe to pass to client components) ──

export interface [EntityName]Summary {
  id: string
  [only the fields the client component needs — not the full DB row]
}
```

**Rules:**
- One interface per database entity — names match the table (pascal-case singular: `Goal` for `goals` table)
- Never expose fields that should be server-only (e.g., internal scoring columns) in client-safe view types
- API route request/response types must exactly match the JSON shapes defined in Section 10

## 5. External Integrations

*Include this section if the app uses services beyond Supabase and Vercel.*

**Primary source:** Northstar §10 (External Integrations) and §11 (Payment). If the northstar provides integration name, auth method, env vars, and endpoint names, extract them directly — do not re-research what is already documented. Use `artifacts/integrations/` research docs only for details the northstar doesn't cover.

For each integration, summarize the patterns and reference the source:

| Service | Purpose | SDK / Method | Source |
|---|---|---|---|
| [from northstar §10] | [purpose] | [SDK] | northstar §10 / `artifacts/integrations/[service].md` |
| [from northstar §11] | [payment] | [SDK] | northstar §11 / `artifacts/integrations/[service].md` |

### [Service Name]
**SDK:** `[package-name]`
**Initialized in:** `src/lib/[service].ts` (client-safe) or `supabase/functions/[service]/` (server-only) — never imported directly in components or routes
**Key operations used:**
- `[operation]` — [what it does, which feature uses it]

**Webhook events handled** (if applicable):
| Event | Handler | What it does |
|---|---|---|
| `[event.name]` | `supabase/functions/[service]-webhook` | [action taken] |

*Repeat block for each integration.*

## 6. Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Framework | React Router v7 (Vite) | SPA mode, pre-rendered landing page |
| Styling | Tailwind CSS | |
| Data Fetching | TanStack React Query | Caching, dedup, stale-while-revalidate, mutation invalidation |
| Backend / DB | Supabase (DB + Auth + RLS + Edge Functions + Storage) | Sole backend — no server runtime in frontend |
| Auth | Supabase Auth | Client-side, JWT-based, RLS enforced |
| Server logic | Supabase Edge Functions | Webhooks, cron, email, service_role operations |
| Deployment | Vercel (static SPA) | Pre-rendered `/`, SPA fallback for `/app/*` |
| Email | Resend (via Edge Function) | [include if email in scope; omit otherwise] |
| LLM | OpenRouter (via Edge Function) | All RAD apps use LLM for data interpretation/reasoning. Server-only API key. |
| Payments | [from northstar §11 — Stripe / PayOS / other. Do not default to Stripe.] | |
| Animation | [motion — include only if EDS §6 Dopamine Moments require it] | |

*Omit rows not applicable to this project.*

## 7. Architecture Overview
High-level data flow: React SPA → Supabase (via publishable key + JWT) → Postgres (RLS-enforced).
Server-side logic: Edge Functions only (webhooks, cron, email, service_role).

**SDK rule:** Every external SDK (Supabase, payment provider, email provider, LLM) is initialized and accessed through a single wrapper file in `src/lib/`. No component or hook imports a third-party SDK directly. For server-only SDKs (payment, email, LLM), the wrapper calls a Supabase Edge Function via `supabase.functions.invoke()`.

## 7b. Technical Decisions

Document every non-trivial technical decision made during this spec. Each decision references the research that informed it.

### TD-[N]: [Decision Title]

**Context:** [What feature requires this decision. 1-2 sentences.]
**Complexity signal:** [From architecture skill — e.g., "Credit balance that can be spent"]
**Options considered:**
- A) [Option] — [trade-off]
- B) [Option] — [trade-off]

**Decision:** [Which option and why]
**Research basis:** [artifacts/integrations/pattern-[name].md / architecture skill reference pattern / training data]
**Risks:** [What could go wrong]
**Revisit trigger:** [What condition would make us reconsider]

*If the research basis is "training data" for a decision with a complexity signal, dispatch the Research Agent before finalizing.*

*Omit this section if no complexity signals were triggered.*

## 8a. Data Invariants

Business rules the system must enforce. Derived from the northstar and domain research — not from mock data. These drive schema constraints, RLS policies, and Edge Function validation.

| Entity | Invariant | Enforcement |
|---|---|---|
| [entity] | [what must always be true] | [CHECK constraint / RLS policy / Edge Function validation / application logic] |

*Every invariant must map to a concrete enforcement mechanism. An invariant without enforcement is a wish, not a rule.*

## 8b. Database Schema

**Derive tables from invariants + northstar + Make mock shapes:**
- **Profiles table:** Northstar §9 (Auth Model) specifies what profile data is stored — birth date, birth time, gender, family members, etc. Every field listed in §9 must appear as a column.
- **Credit/payment tables:** Northstar §11 (Payment) and §4 (Revenue Model) define the payment model. If credit-based: need `credit_balances` and `credit_transactions` tables. If subscription: need `subscriptions` table.
- **Core entity tables:** Northstar §7 (Build Scope) and §13 (User Scenarios) reveal which entities the app manages. Every data variable in the wireframe metadata blocks must map to a column in these tables.

For each table:

### table_name
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK, default gen_random_uuid() | |
| created_at | timestamptz | default now() | |
| user_id | uuid | FK → auth.users(id) | |
| ... | | | |

RLS policy for this table:
- SELECT: [who can read — e.g. "authenticated users where user_id = auth.uid()"]
- INSERT: [who can insert]
- UPDATE: [who can update]
- DELETE: [who can delete]

Indexes:
- `CREATE INDEX idx_[table]_user_id ON [table](user_id);`
- [one CREATE INDEX per FK column and per column used in WHERE clauses]

**All tables defined upfront — nothing stubbed or deferred.**

**Storage (if applicable):**
- Bucket name and access level (public or private)
- RLS policy for the bucket
- Max file size and allowed MIME types

**Seed data:** After defining all tables, create `supabase/seed.sql` with 5–10 realistic rows per table. Build agents reference seed data when building screens — realistic values prevent placeholder copy leaking into the build.

## 9. Data Access Layer

Data is fetched client-side via `@supabase/supabase-js`. Typed query functions live in `src/lib/data/` or as hooks in `src/hooks/`. Every screen data variable in the screen specs must have a corresponding function or hook.

| Function / Hook | File | Returns | Used by screen(s) |
|---|---|---|---|
| `useXxx()` | `src/hooks/useXxx.ts` | `{ data: Xxx[], loading, error }` | ScreenName |
| `getXxxById(id)` | `src/lib/data/xxx.ts` | `Promise<Xxx \| null>` | ScreenName |

**Coverage rule:** Every piece of data a screen needs to render must have a corresponding query function or hook. Cross-check against screen spec metadata — if a screen displays `goals.title`, there must be a function returning a `Goal` with a `title` field.

**Not here:** Inline mutations via `supabase.from().insert()` — built during the feature screen build, not Foundation.

## 10. API Contracts

**API routes are replaced by Supabase Edge Functions** for operations that cannot be a direct client→RLS query: webhook handlers, cron jobs, email sending, and operations requiring the service_role key.

**Most mutations do not need an Edge Function.** Client-side code writes directly to Supabase via the publishable key, with RLS enforcing authorization. Only use Edge Functions when:
- The operation requires `SUPABASE_SERVICE_ROLE_KEY` (webhooks, admin operations)
- The operation requires a server-only secret (payment signature verification, email API key)
- The operation is triggered externally (webhooks, cron)

**Cross-check sources before writing contracts:**
- **Northstar §10** (External Integrations) — if the northstar names specific endpoints, every endpoint must appear here with a contract.
- **Screen spec interaction flows** — every branch condition that calls an Edge Function must have a corresponding contract.
- **Northstar §13 scenarios** (if present) — every endpoint tagged in a scenario step must have a contract.

**Routing decision for each operation:**
- **Direct client → Supabase (RLS)**: reads and user-owned writes — no Edge Function needed
- **Edge Function** (`supabase/functions/`): webhooks, cron, email, service_role operations

| Operation | Type | Consumer | Built in |
|---|---|---|---|
| Read user's goals | Direct query (RLS) | HomeScreen | Feature — inline supabase.from() |
| `POST supabase/functions/v1/payment-webhook` | Edge Function | Payment provider | Foundation |
| `POST supabase/functions/v1/send-email` | Edge Function | Cron / webhook | Foundation |

For each **Edge Function**:

### supabase/functions/[function-name]
**Trigger:** [webhook / cron / client call via supabase.functions.invoke()]
**Auth:** Service role / publishable key + JWT
**Validation:** `{ field: z.string(), ... }`
**Request body:**
```json
{ "field": "type — description" }
```
**Response (200):**
```json
{ "field": "type — description" }
```
**Error cases:** [list status codes and conditions]

### Standard Error Response Shape

All API error responses use this shape:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message displayed in ErrorBanner"
  }
}
```

Common codes: `UNAUTHORIZED`, `NOT_FOUND`, `VALIDATION_ERROR`, `RATE_LIMITED`, `SERVER_ERROR`. The `message` field is user-visible copy — write it as copy, not a developer log.

## 11. Auth & Security Model

**Extract from northstar §9 (Auth Model) — do not guess.** The northstar specifies the exact auth method, anonymous-first behavior, account creation trigger, profile data, and session rules.

- **Auth provider:** Supabase Auth
- **Auth method:** [from §9 — Phone OTP / email+password / magic link / OAuth providers / anonymous-first → upgrade]
- **Why this method:** [from §9 — one sentence linking auth choice to primary user context]
- **Anonymous access:** [from §9 — what user can do before signing up, or "N/A" if auth required immediately]
- **Account creation trigger:** [from §9 — what action forces account creation, e.g. "first paid feature purchase"]
- **Auth UI approach:** [Custom screens (consumer products) or Supabase Auth UI (internal tools)]
- **Session handling:** [from §9 — persistent / expires after X / refresh token]
- **Profile data stored:** [from §9 — list every field beyond email/phone: birth date, birth time, gender, family members, etc.]
- **RLS enforcement:** All tables enforce RLS. No table is accessible without a policy. Service role key used only in webhooks and cron jobs.
- **Sensitive data rules:** Birth dates, personal information stored server-side only. Client components receive only the fields in client-safe view types (Section 4).

**If northstar §9 specifies OAuth providers:** List each provider, note which require custom OAuth (e.g., TikTok) vs. native Supabase Auth support (Google, Facebook), and flag any provider that requires app review (affects sprint timeline).

## 12. Environment Variables

**Two scopes:** Vercel env vars (client-safe, VITE_ prefix) and Supabase Edge Function secrets (server-only, set via `supabase secrets set`).

| Variable | Scope | Description | Where to get it |
|---|---|---|---|
| `VITE_SUPABASE_URL` | Vercel (client-safe) | Supabase project URL | Supabase → Project Settings → API |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Vercel (client-safe) | Supabase publishable anon key | Supabase → Project Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Edge Function secret | Service role key — never in frontend | Supabase → Project Settings → API |
| `[OTHER_VARIABLE]` | [scope] | [description] | [source] |

**Rules:**
- Variables prefixed `VITE_` are exposed to the browser bundle — never put secrets here
- Server-only secrets live in Supabase Edge Function environment, NOT Vercel env vars
- Set Edge Function secrets via: `supabase secrets set VAR_NAME=value`
- LLM API keys, payment secrets, email API keys are all Edge Function secrets

**Stack extensions — derive from northstar §10 and §11:**

Every external integration in northstar §10 and §11 specifies env var names. List them all here.

| Extension | Variables | Scope |
|---|---|---|
| [Payment provider from §11] | [env var names from §11] | Edge Function secret (except publishable keys → Vercel VITE_) |
| [External API from §10] | [env var names from §10] | [Edge Function secret / Vercel VITE_ as specified in §10] |
| Resend | `RESEND_API_KEY` | Edge Function secret — include only if email in scope |

## 13. LLM Usage Decisions

| Feature | LLM Used? | Rationale | Estimated calls/month |
|---|---|---|---|
| [feature] | Yes / No | [why LLM or why template/SQL] | |

**Monthly cost ceiling:** [define — e.g. $60/month]
**Default rule:** SQL and templates for deterministic logic. LLM only for unstructured NLP where templating cannot cover the decision space.

```
Is the input unstructured natural language that templating cannot handle?
  YES → LLM call is justified. Document model, prompt approach, cost estimate.
  NO  → Use SQL query or template.
```

Common cases that do NOT need LLM: filtering/sorting structured data → SQL; generating copy from known variables → template; categorisation with a finite set → lookup table.

*Omit this section if no LLM features.*

## 14. AI Module Inventory (if AI features)

| Capability | Type | Source | Build impact |
|---|---|---|---|
| [e.g. Document reader] | REUSE | `@studio/doc-reader` npm package | Wire in Foundation — import wrapper, configure |
| [e.g. Custom scoring] | BUILD | New for this project | Prompt engineering, testing, API route. Budget ~2h. |

**REUSE** — existing package, already built and tested. Wire in Foundation alongside SDK wrappers.
**BUILD** — new AI module requiring prompt engineering, output validation, and testing.

**Module boundary rule (mandatory for BUILD modules):** Every BUILD module must have a fully specified interface contract: input types → output types. Reusable AI modules in `src/lib/` receive all app-specific values as function arguments — never import from `src/config/` or other app-specific files. This enables extraction to a private npm package later without modification.

*Omit this section if no AI features.*

## 15. Scheduled Tasks / Cron Jobs (if applicable)

**Source:** Check northstar §12 for push notification specs. If the northstar defines push notification triggers (seasonal, monthly, event-based), each trigger becomes a cron job row below.

| Job | Schedule | Edge Function | What it does | Auth |
|---|---|---|---|---|
| [e.g. Daily digest] | `0 8 * * *` | `supabase/functions/cron-daily-digest` | [what it does] | Service role |
| [push notification triggers from §12] | [schedule] | `supabase/functions/cron-[trigger]` | [what it sends] | Service role |

**Implementation pattern:**
- Each cron job is a Supabase Edge Function scheduled via Supabase Dashboard (Database → Extensions → pg_cron) or `supabase/config.toml`
- Cron Edge Functions use the service role client — they operate outside auth context
- Deploy via `supabase functions deploy [name]`

*Omit this section if no scheduled tasks.*

## 16. Email / Notification Flows (if applicable)

*Include only if the app sends transactional email. Provider: Resend. See `artifacts/integrations/resend.md` for API patterns.*

**Wrapper:** `supabase/functions/send-email/index.ts` — all email sends go through this Edge Function. No feature or client code imports `resend` directly. Client code calls via `supabase.functions.invoke('send-email', { body: { template, data } })`.

| Trigger | Template | To | Subject | Sent from |
|---|---|---|---|---|
| [e.g. User signs up] | `welcome` | `user.email` | "Welcome to [App]" | `noreply@[domain]` |
| [e.g. Payment confirmed] | `receipt` | `user.email` | "Your receipt" | `noreply@[domain]` |

For each email template:

### [Template name]
**Trigger:** [what causes this email — user action, cron job, webhook]
**Recipient:** [who receives it]
**Data passed in:**
```typescript
{ user: { name: string; email: string }; [other fields] }
```
**Send function signature:**
```typescript
sendWelcomeEmail(user: { name: string; email: string }): Promise<void>
```

*Omit this section if no transactional email.*

## 17. Not Building

**Source:** Copy directly from northstar §8 (Not Building). Do not rewrite, soften, or omit entries. If additional features were excluded during wireframe scoping (Phase 2), add those here too.

The following features are explicitly excluded from this version. Do not build.

- [Feature name] — [one line reason]

**Known shortcuts** (deliberate trade-offs — not bugs):
- [Shortcut] — acceptable for v1
- No pagination — lists capped at 50 items

*Shortcuts that affect data integrity (missing RLS, no input validation) are bugs, not debt — fix immediately.*

## 18. SEO & PWA Infrastructure

This section covers the technical infrastructure for organic search discoverability, social sharing previews, and PWA installability. Built during Foundation.

### Landing Page Pre-rendering (React Router v7)

The landing page at `/` is pre-rendered at build time via `react-router.config.ts` (`prerender: ['/']`). This produces a full static HTML file with all content, meta tags, and JSON-LD — no JavaScript required for crawlers.

The route file at `src/routes/_index/route.tsx` exports meta tags via a `meta` function:
- `title`: from northstar §7b headline
- `description`: from northstar §7b subheadline
- `og:title`, `og:description`, `og:image`, `og:type`, `og:locale`
- `html lang`: set in `src/root.tsx`

### Open Graph Images

**Default OG image:** Static PNG at `public/og-image.png` (1200×630px), referenced in the landing page meta tags.

**Dynamic share card OG images** (if app has branded share cards):
- Option A: Vercel Middleware at `/share/[token]` — detects crawlers via user-agent, returns HTML with dynamic OG tags. Users get SPA redirect.
- Option B: Supabase Edge Function at `supabase/functions/og-image/` — generates dynamic OG images server-side.
- Decision made per project in the northstar. Both options support Vietnamese diacritics with the correct font (Be Vietnam Pro, Inter, or Nunito Sans).

### SEO Static Files

| File | Location | Route |
|---|---|---|
| Sitemap | `public/sitemap.xml` | `/sitemap.xml` |
| Robots | `public/robots.txt` | `/robots.txt` |
| Manifest | `public/manifest.json` | `/manifest.json` |

**Sitemap entries:** Landing page (`/`, priority 1), plus any public share routes. Authenticated app routes are excluded (behind auth, not indexable).

**Robots:** Allow `/`, disallow `/app/` (authenticated routes).

### JSON-LD Structured Data

| Schema | Page | Purpose |
|---|---|---|
| `WebApplication` | Landing page | App name, category, pricing (free), aggregate rating |
| `FAQPage` | Landing page | FAQ items from northstar §7b — enables rich results |

Render as `<script type="application/ld+json">` in the landing page component. Escape `<` as `\u003c` to prevent XSS.

### PWA Manifest

`public/manifest.json` (static file, not generated):
- `name`, `short_name`: from northstar
- `start_url`: `/app/home` (or the authenticated home — not `/` which is the landing page)
- `display`: `standalone`
- `theme_color`, `background_color`: from EDS §5 brand palette
- `icons`: 192×192 and 512×512, both `any` and `maskable` variants
- `screenshots`: at least one with `form_factor: 'narrow'` for app-store-style Android install dialog

### Service Worker

**Library:** `vite-plugin-pwa` (Workbox) or `@serwist/vite` — evaluated during `/init`
- Source: configured in `vite.config.ts`
- Output: `public/sw.js`
- Disabled in development
- Runtime caching: cache-first for static assets, network-first for Supabase API calls
- Offline fallback: static offline page (no data dependency)
- Navigate fallback: `/index.html` for SPA routes (allowlist: `/app/*`)

### Install Prompt

**Hook:** `src/hooks/useInstallPrompt.ts`
- Captures `beforeinstallprompt` event (Chromium-only)
- Defers prompt until user engagement signal (scroll past hero, or CTA tap)
- Detects `display-mode: standalone` to hide install UI when already installed
- iOS fallback: detect iOS + show manual "Add to Home Screen" instructions

### Core Web Vitals Budget

| Metric | Target | How |
|---|---|---|
| LCP | ≤ 2.5s on 4G | Hero image with `loading="eager"`, Vietnamese font with `font-display: swap`, pre-rendered landing page HTML |
| CLS | ≤ 0.1 | Reserved heights on skeleton loaders, font `size-adjust` in @font-face |
| INP | ≤ 200ms | Third-party scripts loaded dynamically, no render-blocking JS, Vite code splitting |

### Font Loading

- Self-host fonts in `public/fonts/` — download .woff2 files during `/init`
- Load via `@font-face` in `src/app.css` with `font-display: swap`
- **Must include Vietnamese glyphs** for proper diacritic rendering (Be Vietnam Pro, Inter, or Nunito Sans recommended)
- Reference via CSS custom property in `@theme inline` block (e.g., `--font-[name]`) — Make's theme.css typically handles this

### Vietnamese SEO Requirements (if Vietnam market)

- `html lang="vi"`
- Title tags and meta descriptions in Vietnamese with proper diacritics
- URL slugs: strip diacritics ("Quản lý công việc" → `/quan-ly-cong-viec`)
- Target both diacritic and non-diacritic keyword variants
- Domain: `.vn` or `.com.vn` TLD for local ranking benefit

### Social Sharing Validation (pre-launch checklist)

| Tool | URL | Purpose |
|---|---|---|
| Facebook Sharing Debugger | `developers.facebook.com/tools/debug/` | Validate OG tags, clear FB cache |
| Zalo Debug Tool | `developers.zalo.me/tools/debug-sharing` | Validate OG tags, clear Zalo cache ("Thu thập lại") |
| OpenGraph.io | `opengraph.io/link-preview` | Cross-platform preview |
| Google Rich Results Test | `search.google.com/test/rich-results` | Validate JSON-LD structured data |

*This section is mandatory for all RAD projects. The PWA infrastructure is built during Foundation; the landing page content is built as the first Frontend Foundation screen.*
````

---

## Quality Check

Before finalizing — all sections present, complete, and traceable to source:

- [ ] 0. Data invariants enumerated — business rules that must always be true, derived from northstar + domain knowledge
- [ ] 0. Domain research conducted — schema patterns for the specific domain reviewed (credit systems, multi-tenant, etc.)
- [ ] 1. Overview — one paragraph, primary user, value prop
- [ ] 2. Functional Requirements — every in-scope capability as a user-observable row; grouped by feature area; cross-checked against northstar §13 scenarios (if present)
- [ ] 3. Non-Functional Requirements — performance, scale (from northstar §12 if specified), availability, accessibility, security targets
- [ ] 4. Shared TypeScript Interfaces — entity interfaces, API request/response shapes, client-safe view types defined
- [ ] 5. External Integrations — extracted from northstar §10 + §11; SDK, init file, key operations, webhook events per service; research docs supplement only what the northstar doesn't cover
- [ ] 6. Tech Stack — all layers listed; payment provider from northstar §11 (not hardcoded Stripe); animation libraries from EDS §6 if needed; unused rows omitted
- [ ] 7. Architecture — data flow described, SDK rule stated
- [ ] 8. Schema — tables derived from invariants + northstar §9/§11/§7 + Make mock shapes; every wireframe data variable maps to a column; indexes on all FK and WHERE columns; seed data created
- [ ] 9. Data Access Layer — query function or hook for every screen data need in the screen specs
- [ ] 10. API Contracts — every Edge Function fully specified; direct client→RLS operations identified; cross-checked against northstar §10 endpoints and screen spec interaction flow branch conditions; northstar §13 scenario endpoints all present
- [ ] 11. Auth & Security — extracted from northstar §9: exact method, anonymous-first behavior, account trigger, profile data, session rules, OAuth providers with custom vs. native distinction
- [ ] 12. Env Vars — derived from northstar §10 + §11; every variable for every integration listed; no hardcoded Stripe vars
- [ ] 13. LLM Usage — complete if any LLM features; omitted if none
- [ ] 14. AI Module Inventory — complete if any AI features; omitted if none
- [ ] 15. Scheduled Tasks — includes push notification triggers from northstar §12 if present; omitted if none
- [ ] 16. Email Flows — complete if transactional email; omitted if none
- [ ] 17. Not Building — copied from northstar §8 + any Phase 2 additions; named features only
- [ ] 18. SEO & PWA Infrastructure — pre-rendered landing page with meta tags, OG image spec with Vietnamese font, static manifest.json with maskable icons + screenshots, PWA service worker configured, useInstallPrompt hook, Core Web Vitals budget, JSON-LD schemas, sitemap/robots, social sharing validation tools listed

## Schema Anti-Pattern Checklist

Run this checklist against Section 8 before finalizing. Each item is a known failure mode:

### Structural
- [ ] **Missing transaction log** — if the app has credits/balance, there must be a `transactions` table. Storing only a balance column is a data integrity time bomb.
- [ ] **Computed columns without source** — if a column is derived (e.g., `total_spent`), the source data must also be stored. Computed columns without a transaction trail cannot be audited or corrected.
- [ ] **Missing soft delete** — tables with user-generated content should use `deleted_at timestamptz` instead of hard DELETE. Hard deletes break audit trails and referential integrity.
- [ ] **Incorrect cascade** — ON DELETE CASCADE on user-facing data tables is almost always wrong. Use RESTRICT or SET NULL. CASCADE silently destroys user data.

### Indexes
- [ ] **Missing FK indexes** — every foreign key column must have a CREATE INDEX statement. Postgres does not auto-index foreign keys.
- [ ] **Missing WHERE-clause indexes** — columns used in RLS policies (`user_id`, `status`, `created_at` ranges) need indexes.
- [ ] **Composite index order** — for multi-column indexes, the most selective column goes first.

### Concurrency
- [ ] **Race condition in balance updates** — credit deduction must use `UPDATE ... SET balance = balance - $1 WHERE balance >= $1 RETURNING balance` (atomic check-and-decrement), not read-modify-write.
- [ ] **Idempotent webhooks** — webhook handlers must check for duplicate event IDs before processing. Store `event_id` in a `processed_events` table or use upsert.

### RLS
- [ ] **Shared resources gap** — if the app has team/family/shared data, RLS policies must handle access beyond `user_id = auth.uid()`. Common pattern: join through a membership table.
- [ ] **Missing INSERT policy** — tables often have SELECT + UPDATE policies but forget INSERT. Every table needs all four CRUD policies explicitly defined (even if some are "denied").
- [ ] **Service role bypass** — Edge Functions using the service role key bypass RLS entirely. Document which functions use service role and why.

### Data Model
- [ ] **Status as free text** — status columns should use a CHECK constraint with an enum list, not free-text strings.
- [ ] **Timestamp without timezone** — all timestamp columns must be `timestamptz`, never `timestamp`. Supabase default is correct but verify.
- [ ] **Missing created_at/updated_at** — every table should have `created_at timestamptz default now()`. Tables with user-editable data should also have `updated_at`.

---

## Cursor-Readiness Check

**Functional requirements**
- Every in-scope capability has at least one FR row
- Acceptance signals are observable behaviors, not implementation details
- If northstar §13 scenarios present: every scenario-tagged endpoint has a matching FR

**Schema**
- Every table/column name is snake_case and final — no renaming later without breaking generated code
- Every foreign key relationship is explicit: `user_id uuid references auth.users(id)`
- Every FK column has a `CREATE INDEX` statement
- Storage columns have a corresponding Supabase Storage bucket documented
- Profile table includes every field from northstar §9 (profile data)
- Credit/payment tables reflect the revenue model from northstar §4 + §11

**TypeScript interfaces**
- Entity interface fields exactly match the database column names and types
- No server-only fields (internal scores, service keys) in client-safe view types
- API request/response interfaces match the JSON shapes in Section 10

**Edge Function contracts**
- Every Edge Function has the exact function name — `payment-webhook` not "a webhook handler"
- If northstar §10 names endpoints: every named endpoint has a contract
- Every screen spec interaction flow branch that calls an Edge Function has a matching contract
- Request body fields use exact TypeScript-compatible types — `string`, `uuid`, `boolean`
- Every Edge Function includes zod validation
- Response shape includes every field needed
- Error cases list exact HTTP status codes — `401`, `404`, `422` not "auth error"

**RLS policies**
- Written as rules, not intentions — "authenticated users can SELECT rows where user_id = auth.uid()"
- Every table has at minimum a SELECT policy

**Auth model**
- Auth method matches northstar §9 exactly — not a different method or "TBD"
- If anonymous-first: account creation trigger documented with the exact user action
- If OAuth: each provider listed with custom vs. native Supabase Auth distinction

**Environment variables**
- Every env var from northstar §10 + §11 is listed
- Server-only secrets marked as Edge Function secrets (not VITE_ prefix)
- Client-safe vars use `VITE_` prefix
- A corresponding `.env.example` entry exists for every variable

**Not Building**
- Feature names match exactly how they would appear in a build prompt — agents pattern-match against this list
- No vague entries like "advanced features" — every item is a specific named feature
- All entries from northstar §8 are present — none silently dropped

**SEO & PWA Infrastructure**
- Landing page at `/` pre-rendered at build time — `view source` shows full HTML with meta tags
- OG image spec includes Vietnamese-compatible font (Be Vietnam Pro, Inter, or Nunito Sans)
- `public/manifest.json` includes `screenshots` with `form_factor: 'narrow'` for app-store-style Android install
- `start_url` in manifest points to authenticated app home, not landing page (`/`)
- Service worker configured in `vite.config.ts` — not a deprecated Next.js plugin
- `useInstallPrompt` hook spec includes iOS detection fallback
- Core Web Vitals budget defined: LCP ≤ 2.5s, CLS ≤ 0.1, INP ≤ 200ms
- FAQ JSON-LD items match the FAQ questions in northstar §7b
- Social sharing validation tools listed for pre-launch checklist
