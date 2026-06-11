# Lightreel prompt reverse-engineering → improvements for our analysis prompts

**Date:** 2026-06-11
**Source material:** Two Lightreel output snapshots — (1) a full channel analysis of
`@curnon.official` (VN watch brand, 72K followers), (2) a "shoot this week" video script
for the same channel.
**Caveat:** This is an informed reconstruction from output structure, not the actual
prompt. Lightreel's real system may split this across multiple agent steps; what matters
for us is the *behavioral contract* the output reveals, which we can adopt regardless of
how they implement it.

---

## 1. What the snapshots reveal about the prompt

### 1.1 Channel analysis (snapshot 1)

Output structure, in order:

| Section | What it does |
|---|---|
| **The Big Picture** (thesis headline: "Curnon Has Fallen Off a Cliff") | Quantified rise-and-fall narrative (10M peak → 1,500–33K now, "99% drop from peak") + an explicit causal verdict: *"This isn't algorithmic bad luck. The content itself has fundamentally changed."* |
| **What Used to Work (And Still Would)** | 4 named content archetypes ("Livestream energy", "Satisfying packaging process", "Lifestyle aesthetic", "List hook"), each = 2–3 sentence explanation + an embedded video tile (views + age). Closes with an **induced threshold rule**: *"every single video above 100K has either a human face, a satisfying process, or a strong list/ranking framework. Usually two of the three."* |
| **What's Failing Now** | Contrast cards (3 failing archetypes with view counts) + a **feature-absence audit** of recent content: "No human faces / No hooks / Music is background noise / Captions are product copy / Photo carousels are dead weight" — each bullet evidenced. |
| **Creator UGC vs. Curnon's Own Content** | External creators posting *about this brand* outperform the brand channel 10–100× with fewer followers. Evidence tiles with handles, follower counts, views. Punchline: *"The product isn't the problem — the content strategy is."* |
| **Competitive Landscape** | Same-niche VN creator (@odaychicodongho: format, per-video views, engagement 1.8–3.5% vs Curnon 0.07–0.15%) + international analogue (Daniel Wellington's creator-integrated strategy). |
| **What Curnon Should Do Differently** | 7 numbered imperatives. The section opens with an explicit traceability claim: *"These recommendations come directly from what's working in the data — both from Curnon's own history and from what their creators and competitors prove works."* Every recommendation names its proof (specific video IDs, view counts, handles). |

### 1.2 Video script (snapshot 2)

| Section | What it does |
|---|---|
| **The Format** | Format chosen by **triangulation**: 3 independent proofs — the channel's own best video (V10, 202K = 10× channel average) + 2 external creators in the same niche (@dialarchive 170.1K, @jeffyamazaki 48.2K), each with an evidence tile. *"This isn't a guess."* |
| **Why This Angle, Not a Repeat of V10** | Explicit differentiation from the channel's own prior video: V10 = style categories, new script = occasion categories; rationale for why occasion framing retains better. |
| **The Full Script** | ~11s, 6 frames. Each frame: **Shot** / **Text overlay** (exact lines, size hierarchy) / **Music cue** ("Cut on the beat") — followed by a rationale paragraph grounding the frame in channel data (real current SKUs: Kashmir Sharp, Moraine Grace, Lucerne Deep Night, Fortis, Grandeur Moren; which past video each appeared in and at what views). |
| **Production Specs** | Duration, text style, music type, cut rhythm, voiceover (none), face (optional) — each derived from frame-level analysis of the reference videos, not generic advice. |
| **What Makes This Different From V10** | 3 named upgrades, each tied to a data point. |

### 1.3 The behavioral contract (the actual "prompt" beneath the output)

Reconstructed instruction set the model is clearly operating under:

1. **Every claim carries its proof inline.** No sentence about performance without a
   specific video (views, age, format) or creator (handle, followers, engagement). The
   output never says "your top videos tend to…" — it says *which* videos.
2. **Thesis-first, narrative section titles.** Titles are verdicts ("…Has Fallen Off a
   Cliff", "What's Failing Now"), not labels ("Overview", "Analysis").
3. **Contrast is the analytical engine.** Three comparison axes, each its own section:
   *past-self vs present-self*, *brand channel vs UGC about the brand*, *channel vs
   niche competitors*. Diagnosis emerges from the deltas, not from absolute numbers.
4. **Induce one threshold rule** from the evidence: "every video above X views has A, B,
   or C — usually two of three." Memorable, falsifiable, cites ≥3 tiles.
5. **Preempt the creator's default excuse.** Explicitly attribute the decline to a
   content change at a named inflection point and rule out "algorithm bad luck."
6. **Coin a short name for every content archetype** ("process porn", "List hook",
   "dead weight"). Names make patterns referenceable in the recommendations.
7. **Feature-absence audit** of recent content: enumerate what the failing videos *lack*
   (faces, hooks, music-as-driver, native captions), per-feature, with counts.
8. **Recommendations must be traceable**: each one re-cites evidence already shown
   earlier in the memo. Nothing generic ("post consistently") survives this filter.
9. **Script = mirror of a proven reference structure**, not a fixed template. Duration,
   frame count, overlay style, cut rhythm are copied from the analyzed winning video;
   only the *content* of each slot is new. Plus a mandatory "why this isn't a repeat"
   differentiation clause and per-frame rationale.
10. **Tiles interleaved with prose** — evidence is shown next to the claim it supports,
    not appendixed.

### 1.4 Reconstructed prompt skeleton (channel analysis)

```text
ROLE: TikTok growth strategist writing a paid consulting memo for the channel owner.
Direct, opinionated, evidence-bound. Never hedge; never state a claim without naming
the specific video/creator that proves it.

INPUT (injected):
- CHANNEL_TIMELINE: every post {id, date, views, format, caption, media_type}
- FRAME_ANALYSIS (top ~10 all-time + ~10 most recent): {human_face?, first_3s,
  hook_type, edit_pace, music_role: driver|background, overlay_text, scenes}
- UGC_MENTIONS: external creators' videos featuring this brand {handle, followers,
  views, format, hook}
- COMPETITOR_SET: same-niche channels {handle, followers, views/video, format,
  engagement_rate}
- (optional) INTERNATIONAL_ANALOGUE for the niche

OUTPUT — exactly this arc, markdown, tiles inline via [tile:{video_id}]:
1. BIG PICTURE — thesis headline; quantified trajectory (peak → now, % drop);
   one-sentence causal verdict that names the content change and rules out the
   algorithm excuse.
2. WHAT USED TO WORK — 3–4 archetypes; coin a 2–4 word name for each; explanation +
   tile each; close with ONE induced threshold rule covering all top performers.
3. WHAT'S FAILING NOW — failing archetypes with tiles, then a feature-absence list:
   for each missing feature (face, hook, music role, caption style, format) one bullet
   with evidence from FRAME_ANALYSIS.
4. UGC VS OWN CHANNEL — only if UGC_MENTIONS non-empty; per-creator proof; state the
   multiplier; end with what the UGC creators give viewers that the brand doesn't.
5. COMPETITIVE LANDSCAPE — per-competitor: format + numbers + engagement delta; one
   "lesson" sentence; optional international analogue.
6. RECOMMENDATIONS — 5–7 numbered imperatives; each MUST re-cite a video/creator from
   sections 2–5; include at least one "stop doing X" and one "study/repost Y".
```

---

## 2. Gap analysis vs our three prompt surfaces

Reference: `cloud-run/getviews_pipeline/channel_diagnose_prompts.py`,
`diagnose_prompts.py` (answer-session V6), `script_generate.py`.

### What we already do as well or better

- **Verdict-first, bold first sentence** — both our channel memo and V6 enforce this.
- **Evidence tiles tied to prose** (`embedded_tiles` + TOP/WORST PERFORMERS blocks).
- **Inflection-point data** — we already inject `<<<INFLECTION POINT>>>` (before/after
  format mix + drop %); Lightreel's "fallen off a cliff" narrative is built on exactly
  this data, we just don't *narrativize* it as hard.
- **Peer creators + niche benchmarks** (`<<<KÊNH CÙNG NGÁCH>>>`, percentile tiers) —
  equivalent to their Competitive Landscape, and ours is honest about thin data, which
  theirs is not (the Daniel Wellington claim is uncited; our claim-tier rules would
  forbid it).
- **NGỪNG LÀM subsection** — we already mandate "stop doing" recommendations.
- **Deterministic score card** — they have nothing equivalent; ours derisks hallucinated
  numbers.

### Where Lightreel is ahead

| # | Gap | Lightreel behavior | Our current behavior |
|---|---|---|---|
| G1 | **Induced threshold rule** | "Every video above 100K has A, B, or C — usually two of three" | Bullets list per-format observations; no cross-cutting rule |
| G2 | **Causal verdict / excuse preemption** | "This isn't algorithmic bad luck — the content changed" tied to the inflection | Verdict states trajectory + forecast, but doesn't explicitly attribute cause or rule out the algorithm excuse |
| G3 | **Named archetypes** | Coins memorable labels per pattern, reused in recommendations | Uses taxonomy `format_label` only |
| G4 | **Feature-absence audit of recent content** | "No human faces / No hooks / Music is background noise…" across all recent posts, with counts | What_falling bullets are per-video/per-format; no aggregated feature audit (we have the frame-level features — `hook_timeline`, `scene_pattern`, `audio_character` — but only for the *target* video) |
| G5 | **UGC-about-the-brand axis** | Dedicated section: external creators posting about this brand outperform it 10–100× | We compare against niche peers, not creators *featuring this specific brand/channel* |
| G6 | **Script skeleton derived from reference video** | Duration, frame count, overlay style, cut rhythm mirrored from the channel's own proven video + 2 external proofs | Fixed 6-shot backbone with hardcoded camera/overlay template regardless of what actually works for this channel |
| G7 | **Format triangulation surfaced to the user** | "This isn't a guess" + 3 proof tiles before the script | We inject hook evidence into the prompt but the *user* never sees why the format was chosen |
| G8 | **Anti-repeat differentiation clause** | "Why this angle, not a repeat of V10" — checks the channel's own recent similar video | No repeat check; script could duplicate the channel's last attempt |
| G9 | **Per-frame rationale citing channel data** | Each frame followed by why-this-works grounded in a named past video / current SKU | Shots have `viz`/`voice` but no rendered rationale |
| G10 | **Depth** | Long-form (~1,500+ words) consultant memo | Hard ~350–450 word budget (deliberate mobile choice — see §3.4) |

### What NOT to copy

- **English output** — structure transfers; language stays Vietnamese, copy-rules
  (`.cursor/rules/copy-rules.mdc`) still apply to every coined label and headline.
- **Uncited benchmark claims** (Daniel Wellington paragraph) — violates our claim-tier
  discipline. Any international analogue must come from corpus or be dropped.
- **Unbounded length by default** — our mobile skim mandate exists for a reason; depth
  should be a tier, not the default (see §3.4).
- **Their hype-adjacent labels** ("dead weight" is fine; anything drifting toward
  "công thức vàng" territory is banned by copy rules).

---

## 3. Recommended changes (prioritized)

> **Status (2026-06-11):** P1.1–P1.4, P2.5 (prompt-level variant), P2.6 and P2.7 are
> **implemented** (`channel_diagnose_prompts.py`, `script_generate.py`,
> `report_script.py`, `ScriptBody.tsx`, `api-types.ts`). P2.5 keeps the fixed 6-shot
> template (frozen FE contract) and instead injects the niche's top `video_shots`
> video as a "NHỊP CẢNH" rhythm block. P2.8 is **not implementable at this surface** —
> `ScriptGenerateBody` carries no channel identity; the anti-repeat intent is covered
> by P1.4 (channel-diagnosis `next_video`). P3 items remain unplanned.

### P1 — prompt-only changes to channel diagnosis (cheap, high yield)

All in `channel_diagnose_prompts.py`; no new data, no new cost.

1. **G1 — pattern rule instruction.** Add to §2 (`what_worked`) output spec: after the
   3 bullets, emit one final bold sentence inducing a threshold rule from the TOP
   PERFORMERS tiles ("Mọi video trên X view của kênh đều có A hoặc B — thường là cả
   hai"), valid only if it covers ≥3 tiles; otherwise omit. Guard against fabricated
   thresholds: X must be a round number below the minimum views of the cited tiles.
2. **G2 — causal verdict.** Extend §1 (`verdict`) rules for `decline_from_peak` /
   `stagnant`: when `<<<INFLECTION POINT>>>` shows a format-mix shift, the verdict must
   name the content change and explicitly rule out the algorithm excuse ("không phải do
   thuật toán — từ {quarter}, kênh chuyển từ {format A} sang {format B}"). This is pure
   instruction; the data is already injected.
3. **G3 — coined archetype labels.** Require each `what_worked` / `what_falling` bullet
   to open with a 2–4 word Vietnamese label in bold (e.g. **"Quy trình đóng hộp"**,
   **"Ảnh catalog tĩnh"**), and require §7 recommendations to reuse those exact labels —
   this is what makes Lightreel's recommendations feel traceable.
4. **G8-lite for next_video (§6).** Add: LÝ DO must also state how the concept differs
   from the channel's most recent video in the same format (data already present in
   FORMAT PERFORMANCE + TOP PERFORMERS).

### P2 — script generation upgrades (`script_generate.py`)

5. **G6 — reference-derived skeleton.** When the channel (or corpus cohort) has a
   proven video in the chosen format, fetch its `analysis_json.scene_pattern` /
   duration / overlay style and inject a `REFERENCE STRUCTURE` block; instruct Gemini to
   mirror frame count, duration, and overlay hierarchy, filling slots with new content.
   Keep the current 6-shot `_BACKBONE` as the fallback when no reference exists —
   it also remains the deterministic no-LLM path.
6. **G7 — surface the format case.** Add a `format_rationale` field to the response
   (3 proofs: own-channel video + 2 corpus videos with views) and render it above the
   shot list. The evidence is already fetched (`_fetch_top_niche_hooks`, hook_lines);
   today it dies inside the prompt.
7. **G9 — per-shot `reason_vi`.** Optional ≤140-char field per shot citing the data
   point ("Định dạng này đạt {views} trong video {id} — slot này tái dùng nhịp đó"),
   rendered as a caption under the shot card.
8. **G8 — anti-repeat clause.** Inject the channel's most recent video in the same
   format (caption + views) and require a one-line "khác gì video trước" statement.

### P3 — new data work (bigger lifts, separate plans)

9. **G4 — recent-content feature audit.** Aggregate frame-level features (face %, hook
   presence in first 3s, music role, caption type, carousel share) across the channel's
   N most recent videos and inject as `<<<RECENT CONTENT AUDIT>>>`; `what_falling`
   bullets then cite per-feature counts. **Cost guard:** only where extraction already
   exists (channel videos already in `video_corpus`) or cap at ~6 videos at low media
   resolution on the paid Channel Sâu path — must stay inside the ~$80–90/mo ceiling.
10. **G5 — UGC-about-the-brand axis.** EnsembleData keyword/mention search for the
    handle/brand name → external creators' videos featuring the brand → new optional
    memo section ("UGC vs kênh chính") for brand-type accounts, with the multiplier
    stat. New ingest surface + new prompt block; needs its own plan and quota check.

### 3.4 — the depth question (G10, product decision, not prompt tweak)

Lightreel's report works *because* it's long: the contrast sections need room. Our
350–450-word budget is a deliberate mobile choice and shouldn't be silently abandoned.
Options, in increasing effort: (a) keep budget, rely on P1 items to add density rather
than length; (b) raise the channel-diagnosis budget only (it's the flagship paid
artifact) to ~600–800 words while keeping verdict-first bold-skim structure; (c)
progressive disclosure — ≤50-word section verdicts always visible, evidence prose
collapsed behind "Xem chứng cứ". Recommend (a) now, evaluate (b) after P1 ships.

---

## 4. Suggested sequencing

1. P1.1–P1.4 in one PR (prompt text + parser untouched; section markers unchanged).
2. P2.6 + P2.7 next (additive JSON fields; frontend renders if present).
3. P2.5 + P2.8 (reference fetch + injection; fallback path untouched).
4. P3 items as separate planned features with cost/quota review.
