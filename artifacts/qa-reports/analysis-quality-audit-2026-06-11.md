# Analysis-Quality Audit — The Four Core Features (2026-06-11)

Perspective: head of a short-form agency advising KOC/KOL, grading what the
product actually outputs. Evidence: **real production reports** sampled from the
live DB (95 video diagnoses, 7 scripts, 4 pattern reports, channel diagnoses),
plus two pipeline dissections tracing where each weakness originates
(file:line). Load-bearing claims verified by hand.

## The corpus reality that frames everything

| Asset | Coverage | Used by the four features? |
|---|---|---|
| Videos with hourly view-velocity (`stats_history`) | 9,321 / 9,321 | Barely (distribution_shape only; no velocity story in diagnosis prose) |
| Scene-level shot grammar (`video_shots`) | 69,243 scenes / 6,666 videos | Script reference tiles only; never in pattern reports |
| **ASR transcripts (what videos SAY)** | **124 / 9,321 (1.3%)** | Effectively unused |
| Comment radar (sentiment/intent) | exists, cached | Computed but never reaches synthesis prompts |
| Trending sounds / trend velocity | nightly aggregated | Pattern reports only; absent from scripts & diagnosis |

**The product analyzes an audio-first platform on mute, and throws away most of
what it sees.** Those two sentences explain the majority of findings below.

---

## Feature grades

### 1. Phân tích video — **B** (the strongest feature)

**What's genuinely good (verified in production output):** prose is
video-specific, not cookie-cutter (six sampled openers each engage the actual
video — a TVC-style critique, a carousel praise, a 35%-of-channel-median
warning). Benchmarks against the creator's own median ("99.180 view = 35% so
với median 285.646 của kênh bạn") — that's real agency framing. Timestamped
error list with severity + concrete fixes. KPI strip vs niche.

**What caps it:**
- **Fabricated retention presented as measurement.** The retention curve is a
  pure heuristic (`video_structural.py:252` — niche median + a log-boost bump;
  zero signal from the actual video). `retention_source="modeled"` exists in
  the schema but is **never passed to the synthesis prompt**, so Gemini writes
  "tỷ lệ giữ chân 46%" as observed fact. The day a creator compares this
  against their real TikTok Studio analytics, trust dies. This is the #1
  honesty bug in the product.
- **Evidence amputation at the prompt** (`diagnose_prompts.py:240`):
  `user_analysis` is truncated to its **first 24 JSON keys** — scene grammar
  (framing/pace/overlay per scene), `audio_transcript`, `hook_timeline` events
  (sub-second face/text/sound timing!), `loop_architecture_score`,
  `sound_layering`, `persona_consistency_signals` are all extracted (paid for
  in Gemini vision tokens) and then **discarded before synthesis**. The
  diagnosis literally cannot say "chữ overlay vào trước khi beat drop" because
  it never sees the timeline it extracted.
- Comment radar computed (`video_analyze.py:118`) but never reaches the prompt
  — audience reaction, the richest "why" signal, unused.
- Caption advice is generic because **no niche keyword/search data exists** —
  there is nothing to ground it in.
- "Video tiếp theo nên quay" = static lookup of 12 hook templates
  (`knowledge_base.py`), identical across all niches and creator sizes.

### 2. Học video viral — **C−** (weakest vs. its promise)

The promise is "learn the craft of this week's winners." The delivery is a
ranked table of hook-type *labels* with deltas — and in production the craft
fields are empty:
- `why_it_works`, `narrative`, `micro_pattern`, `cultural_framing` — **all
  NULL/""** in sampled production rows. Cause: the Gemini narrative call fails
  → `report_pattern_gemini.py:316` silently falls back and pads with empty
  strings; the user gets the same boilerplate insight on every rank ("giữ được
  retention tốt hơn trung vị — phù hợp để test trong 3 video tiếp theo").
- **"+248% so với ngách" claimed off 6 uses / 4 creators** — exactly the
  thin-sample confidence the product's own rules forbid.
- **A −26% (below-baseline) hook ranked in the top-3 "what's working"**
  (`report_pattern_compute.py` ranks by score, never filters negative deltas).
- **Retention column renders "0%"** (ER unit confusion, 0–1 vs 0–100 scale).
- The 69K-scene shot-grammar corpus — the actual *how* of winning videos —
  never appears in this report at all.

An agency strategist could not hand this to a KOL as-is. The data to make it
excellent already exists in the corpus; the report just doesn't use it.

### 3. Soi kênh đối thủ — **B−** (closest to agency shape, shallowest evidence)

**Good:** honest new-account empty state ("Kênh mới — chưa đủ data để nói
pattern" — exemplary), trajectory classification with a real heuristic table,
format-gap analysis with named peers, `next_video` with HOOK/PREMISE/LÝ DO and
a *realistic* expectation ("100+ views" for a 44-view channel — honest, not
hype), and the posting-window finding (5–7h = 13x, only 17% of uploads in
window) is genuinely the kind of thing agencies charge for.

**Caps:**
- **"Soi" promises looking; the feature counts.** It never inspects a single
  frame, hook, or script of the channel's videos *or* its competitors' —
  purely EnsembleData metadata (views/format/cadence) + Gemini narrative glue.
  Competitor context = avg views + format label per peer. The "what are rivals
  doing" section is statistics wearing a strategist's coat.
- **Confirmed template misfire:** finding `channel_recent_vs_peak_er_drop`
  fired at HIGH strength claiming "lệch audience" when recent ER == peak ER
  (both 9.6%) on a 1-day-old channel — `channel_findings.py:242` initializes
  `peak_er = recent_er`, and the gate `er_drop < 1.0` *passes* at exactly 0.
  Missing: equality gate, min account age, min video count.
- Peer selection is aspirational (4.3M-view channels as "peers" of a 44-view
  channel) and the next-video recommender fires the same "do format X like
  @toppeer" template for any <45% format share, with no significance gate.

### 4. Viết kịch bản — **B−** (best skeleton, weakest grounding)

**Good:** the output structure is ahead of most agency templates — per-shot
timed VO with SFX cues, camera/framing/overlay/pace per shot, corpus pacing
benchmarks (`corpus_avg` vs `winner_avg` cuts/sec), reference frames per shot.
A KOC can *shoot from this*.

**Caps:**
- **Reference tiles fail the sniff test.** Production sample: a skincare
  Retinol-warning script's "references" = a makeup-transformation video and a
  showbiz-gossip channel, labeled "Cùng ngách". The matcher
  (`shot_reference_matcher.py`) hard-filters on coarse legacy `niche_id`,
  scores only visual mechanics (framing/pace/overlay/motion, min_score=15),
  has **zero topic/subject similarity signal**, and doesn't even penalize a
  hook-type mismatch. One glance from a KOL's manager and credibility is gone.
- **VO timing is unvalidated.** Shots get `t0–t1` windows; Gemini's VO text has
  no syllable-count check against Vietnamese speech rate (~3–4 syl/s). A 35-
  syllable line in a 3-second shot ships without complaint.
- **Hooks come from 12 static templates, not from winners.** `knowledge_base.py`
  has fill-in-the-blank patterns ("ĐỪNG [hành động]..."); the prompt never sees
  a single real winning hook line from the niche — because (see corpus table)
  the product has transcripts for 1.3% of its corpus.
- No sound/music direction at all in scripts — on TikTok. The trending-sounds
  data exists nightly and is simply not wired in.

---

## What's already excellent (keep and build on)

- **Wave-distribution model** in the domain knowledge (sóng 0→3, "low view +
  high ER = hook problem, not content problem") — correct and contrarian in
  the right way.
- **Honesty machinery where it's wired**: fixture leak-guards, empty states,
  realistic expectations in next_video, the trajectory heuristic ordering.
- **Per-creator median benchmarking** in video diagnosis — the single most
  agency-like number in the product.
- **Vietnamese voice guide** — creator slang, grammar discipline, anti-hype
  rules. The prose reads native.
- **Format-aware signal weights** (mukbang skips transitions, dance skips CTA)
  — sophisticated, though only used as prompt instruction today.

---

## The five strategic moves (in order)

### 1. A claims ledger — stop saying modeled things in a measured voice *(days)*
Every number that renders must carry its source. Concretely: pass
`retention_source` into the synthesis prompt with a mandatory hedge clause for
modeled values; kill the four correctness bugs (negative-delta in top-3, ER
unit/0% display, ER-equality finding gates, silent narrative fallback → use
deterministic per-field fallbacks from `knowledge_base.mechanism_vi` instead of
empty strings). This is a week of small diffs and it protects the only thing
that matters pre-launch: trust.

### 2. Stop amputating the evidence *(days)*
Remove the 24-key truncation; add four prompt blocks the pipeline already has
in hand: scene-pattern summary (one line per scene from `scenes[]`), the
hook-timeline events, an audio descriptor (`audio_track_role`+`sound_layering`),
and the comment-radar summary. This is the cheapest quality lift in the
codebase — the marginal cost is prompt tokens on data already extracted.

### 3. Turn the sound on — corpus-wide ASR *(the strategic unlock, ~1 sprint + STT budget)*
124→~9K transcripts via the existing HI-14 path on the nightly batch, then mine
**real winning first-lines per niche/class** into a `hook_lines` asset. This
single dataset upgrades three features at once: pattern reports get actual
quotable hooks ("here are the 5 opening lines beating the median this week"),
scripts get real exemplars instead of fill-in-the-blank templates, and video
diagnosis can compare *what you said* vs *what winners say*. On an audio-first
platform this is not an enhancement, it's table stakes the product is missing.

### 4. References that survive a professional's glance *(days)*
Topic gate on the shot matcher: subject_matter/caption similarity as a scoring
dimension, hook-type mismatch disqualifies, min_score raised, and an honest
match label ("cùng nhịp dựng" not "cùng ngách" when only mechanics matched).
Plus the VO syllable-fit validator on scripts.

### 5. Close the outcome loop — the agency moat *(1–2 sprints)*
The product already collects hourly stats for 9K videos but never checks
whether its own advice worked. Track the user's next 3 uploads after a
diagnosis/script; report back: "Video sau lời khuyên: 2.1x median kênh của
bạn." That feedback (a) is the retention feature — creators return to see
their score; (b) builds the only defensible asset in this category: a growing
dataset of *advice → outcome* pairs no competitor can scrape. TikTok-CEO hat
on: tools that demonstrably improve creator outcomes get embraced by the
platform; tools that recite metadata get commoditized by the next GPT wrapper.

Also missing for a top-tier offering (backlog, post-ASR): sound strategy in
scripts/diagnosis (data already aggregated nightly), series/episode
architecture and comment-reply mechanics in the knowledge base, trend-jacking
windows surfaced from the existing `trend_velocity` table.

## Verdict

Architecture and voice: **A−**. Analysis substance today: **C+** — a sharp
junior analyst with excellent templates, a blindfold (no transcripts), and a
habit of stating estimates as measurements. The encouraging part: almost every
gap is a *wiring* problem, not a data problem — the corpus already contains
the evidence (velocity, scenes, sounds, comments) that the reports fail to
use. Moves 1–2 are a week and lift the floor; move 3 changes what the product
*is*; move 5 builds the moat.
