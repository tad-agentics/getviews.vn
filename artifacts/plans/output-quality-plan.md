# Output Quality Implementation Plan — GetViews.vn
> Source: `getviews-output-quality-plan.md` (Claude.ai)
> Goal: Match LightReel's output quality. Every response must feel like a data briefing, not a chatbot answer.
> Created: 2026-04-11

---

## Status Overview

| Item | Priority | Wave | Status | Owner |
|---|---|---|---|---|
| P0-1: Corpus citations | P0 | Wave 3 | ✅ Built | Backend + Frontend |
| P0-2: Thumbnail reference cards | P0 | Wave 3 | ✅ Built | Frontend |
| P0-3: Bold hook formulas | P0 | Wave 3 | ✅ Built | Frontend + Backend |
| P0-4: Recency tags | P0 | Wave 3 | ✅ Built | Frontend + Backend |
| P0-5: "Why it works" mechanism | P0 | Wave 3 | ✅ Built | Backend (prompt-only) |
| P0-6: Agentic Step Logger | P0 | Wave 3 | ✅ Built | Frontend + Cloud Run |
| P1-6: Trend Card UI component | P1 | Wave 3-4 | ✅ Built | Frontend |
| P1-7: Breakout multiplier | P1 | Wave 3-4 | ✅ Built | Backend (batch) |
| P1-8: Signal strength grading | P1 | Wave 3-4 | ✅ Built | Backend + Frontend |
| P1-9: Trending This Week cards | P1 | Wave 4 | 🔲 Not started | Backend + Frontend |
| P1-10: Meta-pattern Monday email | P1 | Wave 4 | 🔲 Not started | Backend |
| P2-11: Cross-creator detection | P2 | Wave 4-5 | 🔲 Not started | Backend |
| P2-12: Video Đáng Học ranking | P2 | Wave 4-5 | 🔲 Not started | Backend + Frontend |
| P2-13: Creator network mapping | P2 | Wave 5 | 🔲 Not started | Backend |

---

## Dependency Map

```
P0-1 (corpus citations)    ← no dependencies — ship first
P0-3 (hook formulas)       ← no dependencies — ship with P0-1
P0-5 (why it works)        ← no dependencies — ship with P0-1
P0-2 (thumbnail cards)     ← video_corpus.thumbnail_url populated (✅ already ingesting)
P0-4 (recency tags)        ← P0-2 (cards to put tags on)
P0-6 (step logger)         ← SSE event protocol (extend existing) + Cloud Run handlers

P1-6 (trend cards)         ← P0-2 + P0-3 + P0-4 + P0-5
P1-7 (breakout)            ← creator_velocity table (needs new migration)
P1-8 (signal grading)      ← trend_velocity + hook_effectiveness (existing tables)
P1-9 (trending cards)      ← P1-7 + P1-8 + Explore scaffold (✅ built)
P1-10 (meta-pattern email) ← Monday email infrastructure (✅ built)

P2-11 (cross-creator)      ← P1-7 + corpus size (~Month 2+)
P2-12 (video dang hoc)     ← P1-7 + Explore sidebar (✅ built)
P2-13 (creator network)    ← ED /tt/user/followers + P2-11 (stretch)
```

---

## Build Order

```
Batch 1 — Prompt-only (no new components):    P0-1 → P0-3 → P0-5
Batch 2 — First new components:               P0-2 → P0-4
Batch 3 — Step logger (SSE + frontend):       P0-6 backend → P0-6 frontend
Batch 4 — Structured blocks:                  P1-6 (TrendCard)
Batch 5 — Analytics layer:                    P1-7 → P1-8
Batch 6 — Discovery layer:                    P1-9 → P1-10
Batch 7 — Moat features:                      P2-11 → P2-12
Batch 8 — Stretch:                            P2-13
```

---

## P0 — Core Output Quality

### P0-1: Corpus Citations

**Problem:** Responses feel like opinions without data backing.
**Scope:** Backend (Cloud Run) + minimal frontend (prompt injection).

**Backend deliverables (`cloud-run/`):**
1. `getviews_pipeline/corpus_context.py` (new) — `get_corpus_count(niche_id, days)` async function:
   - Supabase RPC call: `SELECT COUNT(*) FROM video_corpus WHERE niche_id = $1 AND indexed_at > NOW() - interval '$2 days'`
   - Returns `(count: int, niche_name: str)`
2. `getviews_pipeline/formatters.py` (new) — shared formatting helpers:
   - `format_vn(n: int) → str` — Vietnamese thousand separator (dots): `1100 → "1.100"`
   - `timeframe_vi(days: int) → str` — `{7: 'tuần này', 14: '2 tuần qua', 30: 'tháng này', 90: '3 tháng qua'}`
   - `citation_vi(count: int, niche_name: str, days: int) → str` — assembles: `"Dựa trên 412 video review đồ gia dụng tháng này"`
3. `getviews_pipeline/prompts.py` — inject citation string into synthesis system prompt context before every Flash call:
   ```
   Bạn đang phân tích dựa trên {citation}. Luôn trích dẫn số lượng video và khung thời gian trong mọi nhận định.
   Dùng cách nói tự nhiên: "tháng này", "tuần này" — không nói "30 ngày gần nhất".
   ```
4. `getviews_pipeline/pipelines.py` — call `get_corpus_count()` before each synthesis call; cache count in session for follow-ups (don't re-query).

**Migration:** None required — reads existing `video_corpus`.

**Acceptance criteria:**
- [ ] Every ①②③④⑥ response includes "Dựa trên X video" with real count
- [ ] Numbers use Vietnamese dot separator: `1.100` not `1,100`
- [ ] Timeframes: "tháng này", "tuần này" — never "30 ngày gần nhất"
- [ ] Follow-up responses reuse cached count (no re-query)

---

### P0-3: Bold Hook Formulas

**Problem:** Generic advice like "cần cải thiện hook" instead of actionable fill-in-the-blank templates.
**Scope:** Backend (Cloud Run prompt) + Frontend (renderer styling).

**Backend deliverables:**
1. `getviews_pipeline/prompts.py` — add hook formula instruction to synthesis system prompt:
   ```
   Khi đề xuất hook, LUÔN viết dưới dạng template: "ĐỪNG [hành động] nếu chưa xem video này"
   Dùng [ngoặc vuông] cho phần thay thế — LUÔN bằng tiếng Việt.
   Không bao giờ chỉ nói "nên cải thiện hook" mà không đưa ra template cụ thể.
   ```
2. `getviews_pipeline/knowledge_base.py` — extend with 8 Vietnamese hook formulas + 5 Shopee-specific hooks (from plan §P0-3).

**Frontend deliverables:**
1. `src/components/chat/CopyableBlock.tsx` (new) — highlighted block with copy button:
   - Background: `--purple-light`, border-left: `2px solid var(--purple)`, font-weight: 600
   - Copy button right-aligned; on tap: clipboard + "Đã copy ✓" toast (per EDS §6a)
2. `src/components/chat/MessageRenderer.tsx` — detect lines starting `Hook:` or `**Hook:**` → render as `<CopyableBlock>`

**Acceptance criteria:**
- [ ] Every ①② response includes at least one hook formula template
- [ ] Hook lines render with purple-light bg + copy button
- [ ] Tap copy → "Đã copy ✓" feedback
- [ ] Placeholders always in Vietnamese: `[hành động]` never `[action]`
- [ ] Knowledge base: 8 Vietnamese patterns + 5 Shopee hooks

---

### P0-5: "Why It Works" Mechanism

**Problem:** Diagnosis tells WHAT is wrong, not WHY the fix works.
**Scope:** Backend (Cloud Run prompt-only) — no new components.

**Backend deliverables:**
1. `getviews_pipeline/prompts.py` — add mechanism instruction:
   ```
   Sau mỗi nhận định, LUÔN giải thích TẠI SAO trong 1-2 câu.
   Dùng "Chạy vì:" — KHÔNG dùng "Tại sao hiệu quả:" (quá formal).
   Pattern: "[Nhận định]. Chạy vì: [lý do]. Dựa trên [data]."
   Viết như đang nói chuyện với creator khác, không phải viết báo cáo.
   ```
2. `getviews_pipeline/knowledge_base.py` — add Vietnamese mechanism examples matching the pattern.

**Acceptance criteria:**
- [ ] Every ① diagnosis: "Chạy vì:" for at least the top fix
- [ ] Every ② direction: "Chạy vì:" for each recommended hook
- [ ] Never uses "Tại sao hiệu quả:" — only "Chạy vì:"
- [ ] Tone: creator conversation, not academic

---

### P0-2: Thumbnail Reference Cards

**Problem:** Claims without visual evidence — user can't verify what GetViews is referencing.
**Scope:** Frontend (new components) + Backend (prompt instructs Gemini to output `video_ref` JSON).

**Backend deliverables:**
1. `getviews_pipeline/prompts.py` — instruct synthesis to output `video_ref` JSON blocks inline:
   ```json
   {"type": "video_ref", "video_id": "xxx", "handle": "@creator", "views": 1100000, "days_ago": 6}
   ```

**Frontend deliverables:**
1. `src/lib/services/corpus-service.ts` (new or extend) — `getVideoMeta(videoId)`: fetch `thumbnail_url`, `video_url` from `video_corpus` by `video_id`
2. `src/components/chat/VideoRefCard.tsx` (new):
   - 9:16 aspect thumbnail, border-radius 12px
   - View count: JetBrains Mono, `--purple`, Vietnamese dot separator
   - Recency: `--ink4`
   - Tap → inline `<video>` from R2 `video_url`; second tap → TikTok universal link (`https://www.tiktok.com/@handle/video/{id}` auto-opens TikTok on Android)
3. `src/components/chat/VideoRefStrip.tsx` (new) — horizontal scroll strip for 3+ cards; shows 2.5 cards on mobile to signal scrollability
4. `src/components/chat/MessageRenderer.tsx` — parse `video_ref` JSON blocks → render `<VideoRefCard>`; buffer complete blocks before display (never partially streamed)

**Acceptance criteria:**
- [ ] ①②③⑥ responses show 2-3 thumbnail cards with real corpus videos
- [ ] Cards: thumbnail + view count (JetBrains Mono, dot separator) + "X ngày trước" + handle
- [ ] Tap → inline video; "Xem trên TikTok" link → TikTok universal link
- [ ] Mobile: horizontal scroll strip, 2.5-card peek

---

### P0-4: Recency Tags

**Problem:** No indication of how fresh the data is.
**Scope:** Frontend (extends P0-2 cards + new SignalBadge) + Backend (emit recency in `video_ref`).

**Backend deliverables:**
1. `getviews_pipeline/prompts.py` — include `days_ago` and `breakout` in `video_ref` blocks (already in schema above)
2. `getviews_pipeline/corpus_context.py` — `compute_breakout(video_id)`: `video.views / creator_avg_views`

**Frontend deliverables:**
1. `src/lib/formatters.ts` — add:
   - `formatRecencyVI(daysAgo)` — `"Hôm nay"`, `"Hôm qua"`, `"3 ngày trước"`, `"Tuần trước"`, `"2 tuần trước"`, `"1 tháng trước"`
   - `formatBreakoutVI(ratio)` — `"3,2x"` (Vietnamese comma decimal)
2. `src/components/chat/SignalBadge.tsx` (new) — colored pill: `🟢 Đang bùng` / `🟡 Tín hiệu sớm` / `⚫ Ổn định` / `🔴 Đang giảm`
3. `src/components/chat/VideoRefCard.tsx` — add recency text + breakout badge (purple, >2x only)

**Acceptance criteria:**
- [ ] Every thumbnail card shows Vietnamese recency (no English "2d ago")
- [ ] Breakout multiplier uses Vietnamese decimal: "3,2x" not "3.2x"
- [ ] Videos with >2x breakout show purple badge
- [ ] Trend responses include SignalBadge per trend
- [ ] All timestamps from real `indexed_at`, not hallucinated

---

### P0-6: Agentic Step Logger

**Problem:** User stares at blank screen for 20-60 seconds. No visibility into what the system is doing.
**Fix:** Stream step events via SSE before and during synthesis. Show every search, lookup, and processing step.

**Scope:** Cloud Run (emit step events) + Frontend (AgentStepLogger component) + SSE protocol extension.

**Backend deliverables (Cloud Run):**
1. `getviews_pipeline/step_events.py` (new) — helper to emit SSE step events:
   ```python
   def emit_step_start(label_vi: str) → str  # "Đang tìm xu hướng..."
   def emit_step_search(source: str, query_vi: str) → str  # source: "corpus"|"tiktok"
   def emit_step_creator(handle: str) → str
   def emit_step_count(count: int, thumbnails: list[str]) → str
   def emit_step_processing(label_vi: str) → str
   def emit_step_complete(summary_vi: str) → str
   ```
2. `getviews_pipeline/pipelines.py` — emit step events at each orchestration point per intent (①②③⑤⑥⑦ — see plan §P0-6 §2 for exact event sequences per intent)
3. All AI-generated search queries MUST be Vietnamese — add prompt instruction: `"Tạo search query bằng tiếng Việt. Không dùng tiếng Anh trừ tên riêng (TikTok, Shopee, etc)."`

**Frontend deliverables:**
1. `src/lib/types/sse-events.ts` (new) — full SSE event union type (from plan §P0-6 §1)
2. `src/components/chat/StepSpinner.tsx` (new) — rotating ⟳ CSS animation (1s, `--purple`) → ✓ on complete
3. `src/components/chat/StepThumbnails.tsx` (new) — 4 circular thumbnail previews, 24px, from corpus
4. `src/components/chat/AgentStepLogger.tsx` (new):
   - Phase header: `--ink`, font-weight 600, rotating spinner → ✓ when complete
   - Step category (Vietnamese only): `--ink3`, font-weight 500
   - Search query (in quotes, Vietnamese): `--ink4`, font-weight 400, margin-left 16px, fade-in 200ms
   - Count line: `--ink`, font-weight 600, `formatVN(count)` + thumbnail circles
   - Creator handle: `--purple`, font-weight 500, margin-left 16px
   - On phase complete (`step_complete`): collapse children to single "✓" line (300ms)
   - When synthesis starts: all logs collapse upward (300ms) + 1px `--border` separator
5. `src/lib/services/stream-handler.ts` — parse step events from SSE; route to AgentStepLogger
6. `src/components/chat/MessageRenderer.tsx` — render `<AgentStepLogger>` before synthesis output
7. ChatScreen — add below input field: `"Phân tích sâu cần 30 giây — 2 phút"`

**Acceptance criteria:**
- [ ] Every deep query (①②③④⑤) shows step logs before synthesis starts
- [ ] ⑥ Trend Spike shows full agentic loop with AI-generated Vietnamese search queries
- [ ] ALL search queries displayed are in Vietnamese — no English
- [ ] Step labels are Vietnamese — no "Searching video database" or "Processing"
- [ ] Proper nouns stay English: TikTok, Shopee, GRWM, POV
- [ ] Count line: `formatVN()` — "Đã tìm 1.200 video" not "Đã tìm 1,200 video"
- [ ] Thumbnail previews (24px circles) in count line
- [ ] Completed phases collapse to "✓" line (300ms)
- [ ] All logs collapse when synthesis starts streaming
- [ ] Time estimate shown below input
- [ ] Mobile: full-width, no horizontal overflow

---

## P1 — Differentiation Layer

### P1-6: Trend Card Structured UI

**Depends on:** P0-2 + P0-3 + P0-4 + P0-5

**Backend deliverables:**
1. `getviews_pipeline/prompts.py` — define `trend_card` JSON output schema in synthesis prompt:
   ```json
   {"type":"trend_card","title":"Hook 'Cảnh Báo' + Mặt Người","recency":"Mới 3 ngày","signal":"rising","breakout":"4,2x","videos":["id1","id2","id3"],"hook_formula":"ĐỪNG [hành động] nếu chưa xem video này","mechanism":"Bỏ câu trả lời cliché, tạo comment hỏi thêm","corpus_cite":"412 video · tuần này"}
   ```
2. `getviews_pipeline/stream_handler.py` (extend) — buffer `trend_card` blocks; emit only when block is complete

**Frontend deliverables:**
1. `src/lib/constants/hook-names-vi.ts` (new) — `HOOK_NAMES_VI` mapping (12 entries from plan §P1-6)
2. `src/components/chat/TrendCard.tsx` (new):
   - Title + recency + breakout (`4,2x` — Vietnamese comma decimal)
   - 3 thumbnail strip (horizontal scroll)
   - Hook formula block (purple-light bg, copyable — reuse `CopyableBlock`)
   - "Chạy vì:" mechanism (not "Tại sao hiệu quả:")
   - Corpus cite footer + SignalBadge
   - D2 animation: 400ms bar fill + 100ms stagger on reveal
3. `src/components/chat/TrendCardSkeleton.tsx` (new) — loading placeholder (optional)
4. `src/lib/services/stream-handler.ts` — buffer `trend_card` blocks; reveal as complete unit
5. `src/components/chat/MessageRenderer.tsx` — detect `trend_card` blocks → render `<TrendCard>`

**Acceptance criteria:**
- [ ] ②⑥ responses render 2-5 TrendCards (not inline text)
- [ ] Each card: title, recency, signal badge, 3 thumbnails, hook formula, "Chạy vì:" mechanism, corpus cite
- [ ] D2 animation (400ms + stagger)
- [ ] Cards appear as complete units — never partially streamed
- [ ] Mobile: full-width, thumbnails in horizontal scroll

---

### P1-7: Breakout Multiplier

**Depends on:** `creator_velocity` table (new migration)

**Backend deliverables:**
1. Migration: `ADD COLUMN breakout_multiplier FLOAT` to `video_corpus` (nullable, default NULL)
2. Migration: create `creator_velocity` table: `(handle TEXT PK, avg_views FLOAT, video_count INT, computed_at TIMESTAMP)`
3. Cloud Run batch job (extend existing nightly ingest):
   ```sql
   UPDATE video_corpus vc
   SET breakout_multiplier = vc.views / NULLIF(cv.avg_views, 0)
   FROM creator_velocity cv
   WHERE vc.creator_handle = cv.handle AND cv.avg_views > 0
   ```
4. `getviews_pipeline/batch_analytics.py` (new) — compute `creator_velocity` from corpus aggregates; run weekly

**Acceptance criteria:**
- [ ] `breakout_multiplier` computed weekly for all corpus videos with known creator averages
- [ ] Videos with >2x breakout display purple "X,Xx" badge (Vietnamese comma decimal)
- [ ] Videos with >5x breakout get ⭐ indicator

---

### P1-8: Signal Strength Grading

**Depends on:** `trend_velocity` + `hook_effectiveness` tables (existing from Wave 2 trends)

**Backend deliverables:**
1. `getviews_pipeline/signal_classifier.py` (new):
   ```
   confirmed: 3+ creators, 100K+ total views, <7 days
   rising:    2+ creators, positive velocity, <14 days
   early:     1-2 creators, <7 days, velocity unclear
   declining: negative velocity in last 7 days
   ```
2. Expose signal via synthesis context — include in `trend_card` blocks

**Frontend deliverables:**
1. `src/components/chat/SignalBadge.tsx` (from P0-4) — already built

**Acceptance criteria:**
- [ ] Every trend in ②⑥ responses has a signal badge
- [ ] Signal uses real corpus data — not Gemini hallucination
- [ ] "Tín hiệu sớm" trends explicitly flagged

---

### P1-9: Trending This Week (Explore)

**Depends on:** P1-7 + P1-8 + Explore scaffold (✅ built)

**Backend deliverables:**
1. Migration: create `trending_cards` table:
   ```sql
   CREATE TABLE trending_cards (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     niche_id INT REFERENCES niches(id),
     title TEXT, description TEXT, signal TEXT,
     video_ids UUID[], computed_at TIMESTAMPTZ, week_of DATE
   );
   ```
2. Cloud Run weekly batch (Sunday night, after trend_velocity refresh):
   - For each of 17 niches: read top 5 hook_type shifts → select top 3 videos by `breakout_multiplier` → call Gemini Flash-Lite (Vietnamese prompt: creator tone, "Chạy vì:", hook names in Vietnamese) → store in `trending_cards`
   - Cost: 17 Flash-Lite calls/week ≈ $0.04/week

**Frontend deliverables:**
1. `src/components/explore/TrendingSection.tsx` (new) — "Xu hướng tuần này" section in ExploreScreen:
   - Horizontally scrollable cards
   - Each card: title + description + 3 fan-out thumbnails + SignalBadge

**Acceptance criteria:**
- [ ] 17 niches × 3-5 cards generated weekly (Sunday night)
- [ ] Cards stored in DB — served instantly, no live Gemini call on load
- [ ] Explore shows "Xu hướng tuần này" scrollable section
- [ ] Each card: title, description, 3 thumbnails, SignalBadge

---

### P1-10: Meta-Pattern Monday Email

**Depends on:** Monday email infrastructure (✅ built in email-cron)

**Backend deliverables:**
1. `supabase/functions/cron-monday-email/` (extend existing) — after per-niche plans generated, one additional Flash-Lite call:
   - Input: all 17 niche trend summaries
   - Output: 2-3 sentence Vietnamese cross-niche insight
   - Only included when a genuine cross-cutting pattern exists (don't force)
2. Email template — add meta-insight as header block before per-niche sections
3. Email subject: Vietnamese, ≤42 chars, mobile-optimized: `"Tuần này: hook Cảnh Báo bùng trong 4 niche"`
4. Preview text: first sentence of the meta-insight

**Acceptance criteria:**
- [ ] Monday email opens with 2-3 sentence cross-niche insight in Vietnamese
- [ ] Insight references specific niche count ("4/17 niche thấy xu hướng này")
- [ ] Email subject ≤42 chars, Vietnamese, mobile-optimized
- [ ] Tone: creator conversation — "Chạy vì:" not "Tại sao hiệu quả:"

---

## P2 — Moat Features

### P2-11: Cross-Creator Pattern Detection

**Depends on:** P1-7 (breakout) + corpus size (~Month 2+, ≥100 videos/niche)

**Backend deliverables:**
1. Migration: create `cross_creator_patterns` table: `(niche_id, hook_type, creator_count, total_views, creators TEXT[], week_of DATE)`
2. Weekly batch step:
   ```sql
   SELECT hook_type, COUNT(DISTINCT creator_handle) as creator_count,
          SUM(views) as total_views, array_agg(DISTINCT creator_handle) as creators
   FROM video_corpus
   WHERE indexed_at > NOW() - interval '7 days'
   GROUP BY niche_id, hook_type
   HAVING COUNT(DISTINCT creator_handle) >= 3
   ORDER BY total_views DESC
   ```
3. Synthesis context — include cross-creator counts when available: "3 creator khác nhau trong niche này đang dùng hook này tuần này"

**Acceptance criteria:**
- [ ] Patterns with 3+ creators flagged weekly
- [ ] Synthesis mentions creator count for coordinated trends
- [ ] Creator handles listed (tappable → ③ competitor analysis)

---

### P2-12: Video Đáng Học Ranking

**Depends on:** P1-7 (breakout) + Explore sidebar (✅ built)

**Backend deliverables:**
1. Migration: create `video_dang_hoc` table: `(id, video_id, list_type TEXT, rank INT, velocity FLOAT, refreshed_at TIMESTAMP)`
2. Daily batch extension:
   - "Bùng Nổ": `breakout_multiplier > 3`, last 7 days, ORDER BY views DESC LIMIT 20
   - "Đang Hot": velocity = `views / hours_since_indexed`, last 48h, ORDER BY velocity DESC LIMIT 20
3. RLS: public read

**Frontend deliverables:**
1. `src/components/explore/VideoDangHocSidebar.tsx` (new):
   - Section title: "Video Đáng Học" (never "Videos to Copy")
   - Sub-lists: "🔴 Bùng Nổ" + "🟡 Đang Hot"
   - Each row: thumbnail + handle + views (`formatVN`) + "X,Xx breakout" (Vietnamese comma decimal)

**Acceptance criteria:**
- [ ] Bùng Nổ: 10-20 videos, sorted by views, all >3x breakout
- [ ] Đang Hot: 10-20 videos, sorted by velocity (views/hour), last 48h
- [ ] Title: "Video Đáng Học" — never "Videos to Copy"
- [ ] Lists refresh daily

---

### P2-13: Creator Network Mapping (Stretch)

**Depends on:** ED `/tt/user/followers` endpoint + P2-11
**Cost:** 50 creators × 17 niches × 2 ED units = 1,700 units/week (within Wood plan spare capacity)

**Backend deliverables:**
1. Migration: create `creator_graph` table: `(creator_handle, follows_handle, discovered_at)`
2. Weekly batch: top 50 creators per niche → fetch follower list via ED → store in `creator_graph`
3. Cluster detection: connected components where mutual_follows ≥ 5
4. Surface in ③ competitor analysis and trend responses: "Đây là nhóm 8 creator đang follow nhau"

**Acceptance criteria:**
- [ ] Top 50 creators per niche have follow graph updated weekly
- [ ] Clusters of 5+ mutual-follow creators detected and stored
- [ ] Network info available in ③ competitor analysis

---

## Feature Tracking

| Feature | Wave | Backend | Frontend | QA | Status |
|---|---|---|---|---|---|
| P0-1 (corpus citations) | 3 | ✅ | ✅ | 🔲 | Built |
| P0-3 (hook formulas) | 3 | ✅ | ✅ | 🔲 | Built |
| P0-5 (why it works) | 3 | ✅ | — | 🔲 | Built |
| P0-2 (thumbnail cards) | 3 | ✅ | ✅ | 🔲 | Built |
| P0-4 (recency tags) | 3 | ✅ | ✅ | 🔲 | Built |
| P0-6 (step logger) | 3 | ✅ | ✅ | 🔲 | Built |
| P1-6 (trend cards) | 3-4 | ✅ | ✅ | 🔲 | Built |
| P1-7 (breakout) | 3-4 | ✅ | — | 🔲 | Built |
| P1-8 (signal grading) | 3-4 | ✅ | ✅ | 🔲 | Built |
| P1-9 (trending cards) | 4 | 🔲 | 🔲 | 🔲 | — |
| P1-10 (meta-pattern email) | 4 | 🔲 | — | 🔲 | — |
| P2-11 (cross-creator) | 4-5 | 🔲 | — | 🔲 | — |
| P2-12 (video dang hoc) | 4-5 | 🔲 | 🔲 | 🔲 | — |
| P2-13 (creator network) | 5 | 🔲 | — | 🔲 | — |

---

## New Files Summary

### Cloud Run (new)
| File | Purpose |
|---|---|
| `getviews_pipeline/corpus_context.py` | `get_corpus_count()`, `compute_breakout()` |
| `getviews_pipeline/formatters.py` | `format_vn()`, `timeframe_vi()`, `citation_vi()` |
| `getviews_pipeline/step_events.py` | SSE step event emitters |
| `getviews_pipeline/batch_analytics.py` | `creator_velocity` computation |
| `getviews_pipeline/signal_classifier.py` | Trend signal strength classification |

### Frontend (new)
| File | Purpose |
|---|---|
| `src/lib/types/sse-events.ts` | Full SSE event union type |
| `src/lib/services/corpus-service.ts` | `getVideoMeta()`, `getCorpusCount()` |
| `src/lib/constants/hook-names-vi.ts` | Vietnamese hook name mapping |
| `src/components/chat/CopyableBlock.tsx` | Highlighted block + copy button |
| `src/components/chat/VideoRefCard.tsx` | Thumbnail reference card |
| `src/components/chat/VideoRefStrip.tsx` | Horizontal scroll strip for cards |
| `src/components/chat/SignalBadge.tsx` | Colored signal pill |
| `src/components/chat/AgentStepLogger.tsx` | Step log renderer |
| `src/components/chat/StepSpinner.tsx` | ⟳ → ✓ spinner |
| `src/components/chat/StepThumbnails.tsx` | Circular thumbnail preview row |
| `src/components/chat/TrendCard.tsx` | Full trend card |
| `src/components/chat/TrendCardSkeleton.tsx` | Trend card loading state |
| `src/components/explore/TrendingSection.tsx` | "Xu hướng tuần này" section |
| `src/components/explore/VideoDangHocSidebar.tsx` | Ranked video sidebar |

### Migrations (new)
| Migration | Purpose |
|---|---|
| `add_breakout_multiplier_to_video_corpus` | `breakout_multiplier FLOAT` column |
| `create_creator_velocity` | Creator avg views tracking |
| `create_trending_cards` | Weekly pre-generated trend cards |
| `create_cross_creator_patterns` | Cross-creator hook coordination |
| `create_video_dang_hoc` | Daily Bùng Nổ + Đang Hot rankings |
| `create_creator_graph` | Creator follow graph (P2-13) |
