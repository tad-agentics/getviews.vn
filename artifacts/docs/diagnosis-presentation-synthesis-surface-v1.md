# Design — Presentation & synthesis-surface quality: make the insight visible & cohesive (v1)

**Status:** Proposed (ready for implementation in Cursor)
**Owner:** —
**Surface:** React FE (`VideoBody` + diagnosis renderers + a new retention chart) **and** Cloud Run synthesis surface (prompt, prose lint, reference block, salience role)
**Related:** the four generation docs — `diagnosis-grounding-hook-effectiveness-comments-v1.md`, `diagnosis-retention-curve-structural-v1.md`, `diagnosis-calibration-loop-v1.md`, `diagnosis-extraction-signals-v2.md`. **This doc is their last mile.**
**Cost impact:** FE work is ~0 backend cost; the synthesis-surface changes are prompt/validation/context-shape (no new model calls except an optional paid-path pass, scoped out here).

---

## 0. Thesis

Docs #1–4 make the diagnosis *smarter*. This doc makes that intelligence *survive to the screen*. Three review passes (presentation, prompt/prose/reference, architecture) found the same systemic failure: **the pipeline produces more insight than it shows, in good prose, with cohesion.** Insight is lost at the last mile in three layers — what the FE **renders**, what the prompt is **allowed to argue**, and what the **salience architecture lets reach the model**. Honesty/copy-rules/sanitization are NOT the problem — they protect quality and stay.

---

## Part A — Frontend presentation gaps (verified)

The BE payload carries insight the report never shows. Each below is verified in source.

### A1. The retention drop-off curve is never plotted (🔴 HIGH)
- **Now:** `VideoBody.tsx:92,175-176` consumes `retention_curve` only via `retentionEndPct()` → the single "GIỮ CHÂN 75%" KPI scalar. `Timeline.tsx` takes `segments` (structure), **not** the curve. No component plots `retention_curve` / `niche_benchmark_curve`.
- **Fix:** add a `RetentionCurveChart` component (user curve + dashed niche overlay, x-axis = seconds, mark the biggest-drop `risk_event` from the structural-curve doc). This is **the render target `diagnosis-retention-curve-structural-v1.md` depends on** — without it that doc's content-aware curve is invisible.
- **Where:** in the structure section or directly under the KPI strip in `VideoBody`.

### A2. The sub-second hook timeline is built but orphaned (🔴 HIGH)
- **Now:** `HookTimelineStrip.tsx` exists, fully VI-labeled (`hookTimelineLabels.ts`), but is **never imported/mounted** — grep for its name returns only a *comment* in `ThumbnailTile.tsx`. The Gemini-extracted `hook_timeline` (face_enter@0.4s, first_word@1.2s, reveal@2.8s) is invisible.
- **Fix:** mount `HookTimelineStrip` in the `hook_analysis` section, fed by `meta`/`user_analysis.hook_analysis.hook_timeline`. Near-free win.

### A3. `bright_spot_signal` is resolved then never rendered (🟡 MED / dead code)
- **Now:** `VideoBody.tsx:198-200` computes `brightSpotEffective` (the crisp one-liner, e.g. "vấn đề chỉ ở hook, nội dung ổn") and **no JSX displays it.**
- **Fix:** render `bright_spot_signal.message_vi` as a lead diagnostic chip directly under the headline (see C1 — it's a natural "lead lever").

### A4. `cross_format_signal` isn't rendered (🟡 MED)
- **Now:** `CrossFormatSignal` (trending format across niches + `top_hooks`) reaches the payload; no FE component renders it.
- **Fix:** a compact trend strip ("format X đang lan ở N ngách; hook mạnh: …") in the niche/metadata zone, claim-tier gated.

### A5. Comments are a tile, not an insight (🟡 MED)
- **Now:** `comment_radar` renders only as a standalone tile when `sampled>0` (`VideoBody.tsx:711-717`); sentiment/questions/intent aren't woven into the narrative.
- **Fix:** the FE half of `diagnosis-grounding-…-comments-v1.md` — surface "khán giả hỏi lặp X (gợi ý video tiếp)" inside the next-steps/metadata sections, not as an isolated card.

### A6. Caps truncate silently — no "xem thêm" (🟡 MED, deliberate-but-opaque)
- **Now:** findings capped per tier (hit=3, flop=6, `videoReportCoherence.ts`), reference tiles `slice(0,3)` (`diagnosisReferenceTiles.ts:123`), merged structure findings/tiles capped 6/3 (`mergeVideoStructureSections.ts:31-32`). All silent.
- **Fix:** keep the default view bounded but add an **"xem thêm"** affordance to reach findings 4–N / extra peers. For a paid diagnosis, recovering dropped value matters.

### A7. Inline gap peer tiles — pairing contract (hook + structure axes)
- **Surface:** `SectionFindingCard` + `peerTilesForGapAtIndex` (`diagnosisReferenceTiles.ts`) when `inlineGapRefs` is on (`hook_analysis`, `script_structure` flat + multi-axis).
- **One corrective gap** in the section/axis → every `embedded_tiles[]` entry renders **inside** that gap card (thumbnail row + woven prose).
- **Multiple corrective gaps** → `embedded_tiles[i]` pairs with `gaps[i]` (same order as synthesis `findings` after strength/gap partition). Extra tiles ignored; unpaired gaps show `GAP_PEER_MISSING_VI`.
- **Enrichment** (`buildGapLinkedTileNarrative` with `inlineBridge`) runs only in `peerTilesForGapAtIndex` — axis/section builders must pass raw `buildDiagnosisReferenceTiles` output (no pre-slice, no pre-enrich).
- **Prose:** `buildFindingInlinePeerProse` merges `body_vi` + per-peer lesson; multi-peer gaps prefix `Với «{gap title}»,` then one sentence per `@handle`.

---

## Part B — Synthesis surface: prompt, prose, references (verified)

### B1. Forbidden brand-voice words are prompt-only at runtime (🟡 MED)
- **Now:** `voice_lint.lint_forbidden_copy()` exists but is **not called** on the diagnosis synthesis path (grep in `gemini.py`/`video_analyze.py` → none); only `build_forbidden_phrases_prompt_block()` injects the list into the prompt. English jargon/enums *are* stripped at runtime (`voice_copy.py`); VN guru-words ("bùng nổ", "công thức vàng") are not — an asymmetry.
- **Fix:** run `lint_forbidden_copy()` on the synthesized `*_vi` fields (log + soft-scrub or one targeted retry). You already wrote the linter.

### B2. Peer references have no timestamps → contrast can't be time-anchored (🟡 MED)
- **Now:** the reference block gives the model `hook_phrase` (≤110) + `opening_line` (≤90) but **no time anchors** (`pipelines.py:1116-1182`), yet the prompt asks for "bạn mở bằng X, @handle mở bằng Y" contrast (`diagnose_prompts.py:590-592`). `shot_reference_matcher.py` has `start_s/end_s` but only on the `/script` path.
- **Fix:** port `shot_reference_matcher`'s timestamps into `_reference_evidence_project` so the prompt's contrast can be time-anchored, and the FE peer tile can deep-link the peer *moment* (not just the thumbnail).

### B3. Forced archetype naming + `niche_pattern findings:[]` manufacture/suppress insight (🟡 MED)
- **Now:** `diagnose_prompts.py:73` forces the model to invent a 2–4 word archetype even on eclectic videos (false specificity, circular "theo hình mẫu này…"); `:78/:88` force `niche_pattern` to `findings:[]` → a whole section with no actionable finding.
- **Fix:** make archetype **optional** (emit only when the pattern is real); allow `niche_pattern` one actionable finding so the section isn't insight-free.

### B4. No "lead lever" instruction (ties to C1)
- **Now:** the prompt emits parallel sections of equal weight; nothing marks the single highest-impact finding.
- **Fix:** instruct the model to flag one `lead_finding` (the biggest lever, with its impact rationale); rank by predicted impact once the calibration loop exists.

---

## Part C — Cohesion & the salience re-scope (architecture)

The deepest tension: the **signal-first salience architecture caps insight at what the rule layer detects** (LLM writes pre-selected signals) and produces **slot-filled sections, not one argument**. Resolve by changing salience's *role*, not deleting it — dropping it would hurt a small (`flash-lite`) model, which relies on the curation to stay focused. Salience does three jobs; only the *gate* fights the goal:

| Job | Today | Change |
|---|---|---|
| Detection/grounding | signals surface evidence (quote/number/ts) | **Keep** — it's the anti-hallucination floor |
| Selection/routing | `salience≥0.5` + `DEEP_SECTION_CAP=7` include/exclude (`signals/salience.py`) | **Demote to ranking** — order + elevate the lead lever, don't hard-drop |
| Finding constraint | every finding must map to a fired `signal_id` | **Relax to two-tier** (below) |

### C1. Lead-thesis layer (cohesion)
A thin layer above the modular sections: one biggest lever (from B4 / `bright_spot_signal` / calibration impact rank), rendered as a lead block under the headline (consumes A3). Sections become supporting detail. This is the FE+prompt fix for "no single biggest lever."

### C2. Widen the raw context the model sees (cheapest real "get all the data")
- **Now:** the model gets a *trimmed manifest* + a *summarized* evidence digest — `hook_timeline` collapsed to one line, scenes capped ~8, distributions reduced to a salience score (`diagnose_prompts.py` digest builders).
- **Fix:** feed the full scene list, full hook timeline, benchmark *distributions* (not just the score), comments. Lowest-risk depth win; do this **first** and measure before touching the gate.

### C3. Two-tier findings (lift the recall ceiling safely)
- *Signal-backed findings* — must cite a fired signal (high confidence, as today).
- *LLM-proposed findings* — allowed **beyond** fired signals, but each must cite raw evidence from the (now wider) digest — a timestamp/number/quote — and is labeled lower-confidence.
- **Policed by the calibration loop** (`diagnosis-calibration-loop-v1.md`): measure whether proposed findings predict outcomes; tighten if not. This is what makes the relaxation safe rather than a hallucination risk.

**Tradeoff to respect:** {cheap small model} · {raw unfiltered data} · {focused output} — pick two. C2/C3 keep curation but make it smarter; truly raw-data synthesis wants a bigger model on the **paid path only** (scoped out of this doc; keep the nightly corpus on the cheap curated path).

---

## Flags + rollout
- FE (Part A): `REPORT_PRESENTATION_V2` gates A1–A6 (or ship A2/A3 immediately — they're near-zero-risk). 
- B1 runtime lint: log-only first, then soft-scrub.
- C2 context-widening: behind `DIAGNOSIS_WIDE_CONTEXT`, shadow-compare output quality before/after.
- C3 two-tier findings: `DIAGNOSIS_PROPOSED_FINDINGS`, shadow + calibration-gated.
- All reversible by flag; no migrations except optional peer-timestamp columns (additive/nullable).

## Telemetry
- FE: render coverage — % reports showing retention chart / hook timeline / lead lever (catches regressions where data is present but unshown).
- Synthesis: count of proposed vs signal-backed findings; forbidden-word lint hits; mean output length before/after C2.

## Testing
- FE: `RetentionCurveChart` renders user+niche series, marks risk event, hides gracefully when curve empty; `HookTimelineStrip` mounted in hook section; `bright_spot` lead block renders when present; "xem thêm" expands capped lists. (Pure render tests, jsdom — match existing patterns; project has no jest-dom, use `container.firstChild`/`getAttribute`.)
- Synthesis: `lint_forbidden_copy` invoked on `*_vi` output (assert a planted "bùng nổ" is caught); reference block includes peer timestamps when matcher provides them; two-tier finding shape validates; wide-context digest round-trips.

## Acceptance criteria
1. Retention curve is **plotted** (user + niche overlay, biggest-drop marked); `HookTimelineStrip` and `bright_spot_signal` are visible.
2. Capped lists offer "xem thêm"; cross-format + comment insight surface in-narrative.
3. Forbidden VN words are caught at runtime on diagnosis output, not prompt-only.
4. Peer contrast is time-anchored where the matcher has timestamps.
5. A single lead lever is elevated in both prompt and UI.
6. Salience demoted from emit-gate to ranking; model receives widened raw context; LLM-proposed findings exist behind a flag and are calibration-policed.
7. Honesty/copy-rules/sanitization unchanged; `pytest`/`ruff`/`npm typecheck`/token-lint clean.

## Sequencing (across all five docs)
1. **Quick FE wins now:** A2 (mount hook strip) + A3 (render bright_spot) — minutes, high credibility.
2. Doc #1 grounding (hook-effectiveness + comments) → its FE half is A5.
3. Doc #2 retention curve **+ A1 chart** (build together — curve is pointless unmapped) **+ extraction Tier 1**.
4. **C2 widen context** (measure) → C1 lead lever → A6 expand affordance → B1–B3.
5. Doc #3 calibration loop → unlocks **C3 two-tier findings** safely + impact-ranked lead lever.

Net: docs #1–4 raise the ceiling of what the diagnosis *knows*; this doc raises the ceiling of what the creator *sees and trusts*. Both are required to reach top-tier.
