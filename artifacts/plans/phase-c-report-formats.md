# Phase C — intents × reports (Claude Design handoff)

**Purpose:** Enumerate every user intent the Studio composer will route. Each intent either **dispatches to a destination screen** (already shipped in Phase B) or **lands on `/answer` as one of 4 report formats**. This doc specifies the content contract for each report format so Claude Design can produce the visuals.

**Scope note:** This is a content/layout spec. It does not prescribe pixel treatments — those are Claude Design's call. It DOES prescribe what sections must exist, what data each section shows, and where the reference design (`answer.jsx`, `thread-turns.jsx`, `idea-directions.jsx`) is sufficient vs where we need new layouts.

---

## 1 · Intent × destination map

All 20 realistic creator intents. Each row: intent → destination → notes.

### 1.1 Dispatch to existing screen (no `/answer` report)

| # | Intent | Trigger | Destination | Shipped? |
|---|---|---|---|---|
| 1 | `video_diagnosis` | TikTok video URL | `/app/video?video_id=…` | ✅ B.1 |
| 2 | `competitor_profile` | `@handle` with competitor framing | `/app/channel?handle=…` | ✅ B.3 |
| 3 | `own_channel` | `@handle` + self-reference ("mình/tôi") | `/app/channel?handle=…` | ✅ B.3 |
| 4 | `creator_search` / `find_creators` | "tìm KOL/creator/KOC" | `/app/kol?filters=…` | ✅ B.2 |
| 5 | `shot_list` | "viết kịch bản / shotlist / cách quay" | `/app/script?topic=…&hook=…` | ✅ B.4 |
| 6 | `metadata_only` | URL + "stats/lượt view" only | `/app/video?video_id=…` (mode=stats) | ✅ B.1 covers; mode flag minor |
| 7 | Comparison A vs B | 2+ `@handles` with compare framing | `/app/kol?pinned=a,b&mode=compare` | ⚠️ KOL has pinned tab; compare-mode is new |
| 8 | `series_audit` | Multi-URL (2+ videos) | `/app/video?video_ids=…&mode=series` | ❌ Phase D |
| 9 | Own-content flop diagnostic | "tại sao video tôi ít view" without URL | Prompt for URL → dispatch to `/app/video` | ⚠️ Graceful-degrade needed |

### 1.2 Lands on `/answer` — needs report format

| # | Intent | Trigger | Format |
|---|---|---|---|
| 10 | `trend_spike` | "hook đang hot / tuần này / đang viral" | **Pattern** |
| 11 | `content_directions` | "nên làm gì / format nào / hướng nội dung" | **Pattern** |
| 12 | Sub-niche breakdown | "Beauty skincare / Tech AI tools" | **Pattern** (with niche filter) |
| 13 | Format/length optimization | "30s vs 60s / carousel vs video" | **Pattern** (format section emphasized) |
| 14 | `fatigue` / lifecycle | "pattern nào đang chết / hết trend" | **Pattern** (lifecycle emphasized) |
| 15 | `brief_generation` | "viết brief tuần tới / 5 ý tưởng video" | **Ideas** |
| 16 | Hook variants | "biến thể của hook X / 5 cách viết hook này" | **Ideas** (variant mode) |
| 17 | Timing | "đăng giờ nào / thứ mấy tốt nhất" | **Timing** |
| 18 | Content calendar | "tuần này post gì khi nào" | **Pattern + Timing** (merged) |
| 19 | `follow_up` — classifiable | Natural language, intent detected | Route to Pattern/Ideas/Timing by subject |
| 20 | `follow_up` — unclassifiable | Natural language, no intent | **Generic** fallback |

### 1.3 Phase D (explicit stub — not shipped in C)

- **Commerce/seller** — "sản phẩm TikTok Shop bán chạy", "affiliate rate ngách X", "product angle finder"
- **Personalized `Ship Next`** — creator-channel ingest + 3 personalized angle cards
- **Loop closure** — measure tool-originated posts vs self-sourced
- **Long-form strategy** — "should I rebrand my channel?"

---

## 2 · Four report formats

**Shared shell** (reuse from `answer.jsx` — keep as-is):
- `QueryHeader` (serif question + research-stage narrative + done badge)
- `SessionDrawer` (past sessions)
- Right rail (`Sources`, `RelatedQs`, `TemplatizeCard` — upgraded from `SaveCard`)
- `FollowUpComposer`
- Timeline rail for continuation turns

**Shared content primitives** (new — small, used by all formats):
- `ConfidenceStrip` — band below `QueryHeader`: `N=47 · 7 ngày · Tech · cập nhật 3h trước`. Always visible. Never hidden.
- `<Metric value>` with inline definition: `74% *(viewers past 15s)*`. Reveal-on-hover/tap.
- `WoWDiffBand` — optional band above TL;DR: `🆕 NEW pattern vào #2 · hook X rớt từ #2 → #4`.
- `HumilityBanner` — shown when `sample_size < 30`: "Kết quả chỉ dựa trên N video trong W ngày. Hãy xem như định hướng."

---

### 2.1 Format 1 — **PATTERN**

**Purpose:** Answer "what's working/not working right now" with auditable evidence and lifecycle context.

**Covers intents:** 10, 11, 12, 13, 14 (+ 19 when classified as pattern-family).

**Required sections, in render order:**

| # | Section | Required fields | Reference match? |
|---|---|---|---|
| 1 | `ConfidenceStrip` | `sample_size`, `window_days`, `niche_scope`, `freshness_hours` | ❌ **NEW** |
| 2 | `WoWDiffBand` (optional, shown when data available) | `new_entries[]`, `dropped[]`, `rank_changes[]` | ❌ **NEW** |
| 3 | **TL;DR** — 1-sentence thesis + 3 `SumStat` | `thesis`, `callouts[3]: {label, value, trend, tone}` | ✅ Reference has `.lead` + `SumStat × 3` |
| 4 | **HookFindings** (3 positive, ranked) | Each: `rank`, `pattern`, `retention` (with definition tooltip), `delta`, `uses`, **`lifecycle: {first_seen, peak, momentum}`**, **`contrast_against: {pattern, why_this_won}`**, **`prerequisites[]`**, `insight`, `evidence_video_ids[]` | ⚠️ Reference has `HookFinding` but **missing lifecycle, contrast, prerequisites** |
| 5 | **WhatStalled** (2–3 negative findings) — **NEW — BALANCE SHEET** | Same shape as HookFinding + `why_stalled` | ❌ **NEW — critical to ship** |
| 6 | **EvidenceVideos** (6 cards) | `EvidenceCard[6]`: creator, title, views, retention, duration, bg, hook_family | ✅ Reference has this |
| 7 | **PatternCells** (2×2 grid) — Duration / Hook timing / Sound / CTA | 4 cells: `{title, finding, detail, chart}` | ✅ Reference has this |
| 8 | **ActionCards** (3) with forecast | Each: `icon`, `title`, `sub`, **`forecast: {expected_range, baseline}`**, `route`, `primary` | ⚠️ Reference has `ActionCard` but **missing forecast line** |

**Empty state:** If `sample_size < 30`, render `HumilityBanner` + skip `HookFindings` ranks 2–3 + skip `WhatStalled`. Keep `ConfidenceStrip`, TL;DR, and 3 `EvidenceVideos` only.

**Design delta vs reference:** Reference covers ~5 of 8 sections. **Needs new design for `ConfidenceStrip`, `WoWDiffBand`, `WhatStalled`, forecast line on `ActionCard`, lifecycle + prerequisites row inside `HookFinding`.** Content sections 4 and 5 share a layout (symmetric balance sheet).

---

### 2.2 Format 2 — **IDEAS**

**Purpose:** 5 shootable video concepts with production scaffolding. The "what to make this week" report.

**Covers intents:** 15, 16 (+ 19 when classified as idea-family).

**Required sections, in render order:**

| # | Section | Required fields | Reference match? |
|---|---|---|---|
| 1 | `ConfidenceStrip` | Same as Pattern | ❌ NEW |
| 2 | **LeadParagraph** | 2–3 sentences setting up: "Dựa trên N video thắng trong ngách X, đây là 5 kịch bản có retention cao nhất. Mỗi kịch bản kèm slide-by-slide." | ✅ Reference has lead copy on `IdeaDirections` |
| 3 | **IdeaBlocks × 5** — the hero section | Each: `id`, `title`, `tag`, **`angle`**, **`why_works` (with citations)**, `style`, `styleRef`, **`evidence[]` (2 videos)**, **`hook` (callout)**, **`slides[6]`** (collapsible), **`metric: {label, value, range}`**, **`prerequisites[]` — NEW**, **`confidence: {sample_size, creators}` — NEW** | ⚠️ Reference has `IdeaBlock` but **missing prerequisites + confidence** per idea |
| 4 | **StyleCards × 5** (visual styles to run in parallel) | Each: `id`, `name`, `desc`, `paired_ideas[]` | ✅ Reference has `StyleCard` |
| 5 | **StopDoing × 5** (bad habits → why → fix) | Each: `bad`, `why`, `fix` | ✅ Reference has `StopRow` |
| 6 | **ActionCards** (2): "Mở Xưởng Viết với ý tưởng #1" + "Lưu cả 5 ý tưởng" | Same as Pattern action card | ⚠️ Needs forecast line |

**Variant mode (intent 16 — hook variants):** Suppresses `StopDoing`, renders `IdeaBlocks × 5` where each "idea" is a hook phrasing variant with the same angle. `hook` callout dominates; `slides[6]` can be 2–3 bullets instead of 6.

**Empty state:** If `sample_size < 60` (tighter bar than Pattern because concepts need richer corpus), render humility banner + reduce to 3 `IdeaBlocks` and skip `StopDoing`.

**Design delta vs reference:** Reference is the strongest on this format — `IdeaBlock` is the most-built element. **Only small additions needed: `ConfidenceStrip`, `prerequisites` row per idea, confidence meta per idea.**

---

### 2.3 Format 3 — **TIMING**

**Purpose:** When to post. Primary artifact is a heatmap; narrative wraps it.

**Covers intents:** 17 (+ 18 when paired with Pattern in merged mode).

**Required sections, in render order:**

| # | Section | Required fields | Reference match? |
|---|---|---|---|
| 1 | `ConfidenceStrip` | Same as Pattern | ❌ NEW |
| 2 | **Headline** — dominant window + insight | `top_window: {day, hours}`, `lift_vs_niche_median` (with definition), `lowest_window: {day, hours}` | ✅ Reference has `.timing-head` |
| 3 | **TopWindows × 3** (ranked) | Each: `rank`, `day`, `hours`, `lift_multiplier` | ✅ Reference has this |
| 4 | **Heatmap** — 7 days × 8 hour buckets | `grid[7][8]`: cell values 0–10; tone mapping to 5 levels | ✅ Reference has this |
| 5 | **VarianceNote** — NEW | When `top_window.lift > 2×`: "Heatmap CÓ ý nghĩa" chip (green). When `top_window.lift < 1.3×`: "Heatmap CHƯA ổn định — mẫu thưa" (grey chip). | ❌ **NEW — prevents false confidence** |
| 6 | **FatigueBand** — NEW, optional | If the preferred window has been "best" for 4+ weeks: "Cửa sổ này đã là #1 trong 6 tuần — có thể đang bão hòa." | ❌ **NEW — anti-staleness** |
| 7 | **ActionCards** (2): "Lên lịch post vào T7 18:00" + "Xem kênh đối thủ đang khai thác cửa sổ này" | Same as Pattern | ⚠️ Needs forecast |

**Empty state:** If `sample_size < 80` (timing needs more samples than pattern because it's 2D), render `HumilityBanner` + hide heatmap cells below 5 value + show top-3 windows list only.

**Design delta vs reference:** Reference covers the heatmap well. **New: `ConfidenceStrip`, `VarianceNote` chip, optional `FatigueBand`.**

---

### 2.4 Format 4 — **GENERIC** (fallback)

**Purpose:** Humility-first fallback when intent classification is low-confidence. Not a marketed destination; an honest "we don't know how to answer this in a structured way."

**Covers intents:** 20 (unclassifiable `follow_up`).

**Required sections, in render order:**

| # | Section | Required fields | Reference match? |
|---|---|---|---|
| 1 | `ConfidenceStrip` — but labeled "FALLBACK" | `sample_size`, `window_days`, **`intent_confidence: "low"`** | ❌ NEW |
| 2 | **OffTaxonomyBanner** — NEW | "Câu hỏi này ngoài taxonomy — gợi ý: dùng Soi Kênh / Xưởng Viết / Tìm KOL thay vì" + 3 chips routing to destination screens | ❌ **NEW — the humility move** |
| 3 | **NarrativeAnswer** | 1–2 serif paragraphs; LLM is instructed to hedge explicitly | ✅ Reference has `GenericTurn` narrative |
| 4 | **EvidenceVideos × 3** | Same as Pattern's 3-card grid | ✅ Reference has this |
| 5 | **NoActionCards** | — | — |

**Empty state:** Same shape, shorter narrative. Always show `OffTaxonomyBanner`.

**Design delta vs reference:** Reference has narrative + 3 cards. **New: `ConfidenceStrip` "FALLBACK" mode + `OffTaxonomyBanner` chip row.**

---

## 3 · Multi-intent handling (at a glance)

| Case | Rule | Example |
|---|---|---|
| Destination + report | Destination wins; report becomes `ActionCard` on destination | "Phân tích URL + 3 hook variants" → `/app/video` + action chip "hook variants" |
| Report + report (same family) | Merge in-shape | trend_spike + content_directions → single Pattern with both emphases |
| Report + action | Report + `ActionCard` with corpus-backed prefill | "Hook hot + viết kịch bản hook #1" → Pattern + prominent script ActionCard |
| Report + timing | Merge — Pattern + Timing section | "Post gì khi nào" → Pattern report with Timing section inserted |
| Everything else | Primary intent only; secondary signals → filters/params | "Hook Tech < 500K follower" → Pattern with `followers_lt: 500000` |

---

## 4 · Summary — what's sufficient vs what needs Claude Design work

| Format | Reference coverage | New sections Claude Design needs to draw |
|---|---|---|
| **Pattern** | ~60% sufficient | `ConfidenceStrip`, `WoWDiffBand`, `WhatStalled`, `Lifecycle + Prerequisites` rows inside `HookFinding`, `Forecast` line on `ActionCard` |
| **Ideas** | ~85% sufficient | `ConfidenceStrip`, `Prerequisites` row per idea, confidence meta per idea |
| **Timing** | ~70% sufficient | `ConfidenceStrip`, `VarianceNote` chip, optional `FatigueBand` |
| **Generic** | ~60% sufficient | `ConfidenceStrip` (FALLBACK mode), `OffTaxonomyBanner` |
| **Cross-cutting** | — | `<Metric>` inline-definition primitive, `HumilityBanner`, `TemplatizeCard` (upgrade of `SaveCard`) |

---

## 5 · The one non-negotiable piece

Across all 4 formats, **Pattern's `WhatStalled` section is the critical design addition.** Every other gap is quality-of-life. Missing the balance sheet is what makes research feel like marketing. A `HookFinding`-shaped negative block (red-accent border instead of accent-red, kicker "ĐÃ THỬ NHƯNG RƠI", same 3-column grid) is the single piece that moves the product from "prettier Trends" to "auditable research tool."

If Claude Design only delivers ONE new layout, that's the one.

---

## 6 · Data contract (for reference when pydantic schemas land in C.3)

```
ReportV1 = Pattern | Ideas | Timing | Generic

Pattern {
  confidence: ConfidenceStrip
  wow_diff: WoWDiff | null
  tldr: { thesis: string, callouts: SumStat[3] }
  findings: HookFinding[3]      // required — positive
  what_stalled: HookFinding[2..3]  // required — negative, may be empty with reason
  evidence_videos: EvidenceCard[6]
  patterns: PatternCell[4]
  actions: ActionCard[3] with forecast
}

HookFinding {
  rank: int
  pattern: string
  retention: Metric              // with inline definition
  delta: Metric
  uses: int
  lifecycle: { first_seen: date, peak: date, momentum: "rising" | "plateau" | "declining" }
  contrast_against: { pattern: string, why_this_won: string }
  prerequisites: string[]
  insight: string                // now grounded in contrast_against
  evidence_video_ids: string[]
}

// Similar shapes for Ideas, Timing, Generic — see body.
```

This contract is what the Cloud Run LLM pipeline must produce. The UI is a pure function of this payload. If a field is missing, the UI shows its empty/humility state — never a silent hole.

---

**Next step for you:** Take this doc to Claude Design. Ask them to extend the reference `answer.jsx` / `idea-directions.jsx` / `thread-turns.jsx` with the 7 new content sections listed in §4, starting with `WhatStalled` (§5 — the non-negotiable). Once the new layouts come back, I'll fold them into `phase-c-plan.md` with milestone slicing.
