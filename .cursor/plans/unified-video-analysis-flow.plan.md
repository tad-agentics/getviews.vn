---
name: Unified Video Analysis Flow (collapse user-chosen win/flop)
overview: |
  Today the video-diagnosis product has TWO inputs that mean the same thing: (1) a user-chosen win/flop `mode` (two composer pills + `?mode=` URL param + `video_mode` POST field) and (2) a measured `performance_tier` (hit/average/ flop/early/unknown) computed from corpus + channel signals. This plan collapses them into ONE flow where win/flop is an OUTPUT of analysis, never a user INPUT. A flop video shows MORE gaps than strengths; a win video shows MORE strengths than gaps — driven by `performance_tier`, not by which pill the user clicked.
  CRITICAL (per user 2026-06-12): the system must STILL know win vs flop — and analyze DEEPER for flops. A flop must yield MORE weaknesses → MORE suggestions → MORE reference videos so the creator knows what to fix. The audit found this depth-scaling does NOT exist today (REF_N is a fixed 5; flop findings are capped at 3, same as win) — so Phase 2 adds tier-scaled depth, not just tier-scaled tone.
  Architectural decision (from the 2026-06-12 audit): we do NOT rip out `mode`. `mode` stays as an INTERNAL field derived from tier (preserving the stored discriminator in `VideoPayload.mode` + answer-turn JSONB + cache replay + the existing coherence helpers). We only remove it as a USER input. This is the low-risk path the coherence layer (`reconcile_video_mode`, `effectiveVideoReportMode`, `resolve_extraction_mode`) was already built for.
  Phasing: Phase 0 makes `mode` purely tier-derived at one BE seam (contract safety first). Phase 1 collapses the entry surface (pills + URL + deep links). Phase 2 makes synthesis fully tier-driven incl. early/unknown. Phase 3 removes the UI forks in VideoBody. Phase 4 handles TD-4 resume + stale-doc cleanup + test migration. Each phase is independently shippable and reversible.
todos:
  - id: p0-derive-mode-from-tier
    content: "P0: Make stored `mode` purely tier-derived at the single BE seam (pipeline_reconcile_mode / finalize_video_narrative_layer). Caller-supplied + query-detected mode become at most a tone nudge; measured tier always wins. Keep VideoPayload.mode populated (backward-compat). Add regression test: user mode=flop on a hit-tier video stores mode=win."
    status: completed
  - id: p0-soften-query-detect
    content: "P0: detect_mode_from_query becomes a TIEBREAKER, not a branch driver. When performance_tier is hit/average/flop (a real measured signal), tier wins and the query hint is ignored. When performance_tier is UNKNOWN (no cohort, thin niche), the query hint ('tại sao flop' / 'video viral') IS the deciding signal — it must NOT be dropped, or cohort-less flops mis-render as average. Document this precedence in report_video.py docstring."
    status: completed
  - id: p1-single-composer-pill
    content: "P1: Collapse STUDIO_COMPOSER_PILLS video_flop + video_win into ONE 'Phân tích video' pill. Remove videoModeForPill. Update placeholder copy. Update QueryComposer/HomeScreen/AnswerScreen/FollowUpComposer pill rendering + defaults."
    status: completed
  - id: p1-drop-mode-from-handoff
    content: "P1: Stop writing `?mode=` in buildAnswerHandoffPath for normal video entry; keep parseAnswerHandoffParams tolerant of legacy `?mode=` (back-compat for shared links) but treat it as advisory only. Drop the forced params.set('mode','win') at AnswerScreen.tsx:421."
    status: completed
  - id: p1-fix-deeplinks
    content: "P1: Remove hardcoded mode=win from the 5 deep-link entry points (BreakoutGrid, PatternModal, IdeaBlock, trendsVideoHandoffPath, inheritHandoffFromSearch). They should hand off a URL with no mode and let tier decide."
    status: completed
  - id: p1-stop-sending-video-mode
    content: "P1: Stop sending `video_mode` in the POST body from useSessionStream (drop from args + body). BE field stays optional/back-compat. Verify no caller still passes videoMode for fresh sessions."
    status: completed
  - id: p2-tier-driven-synthesis
    content: "P2: Make extraction + synthesis fully tier-driven for all 5 tier values. resolve_extraction_mode maps hit→win, average/early→average, flop→flop, unknown→average. Ensure `early` is never framed as flop (neutral 'còn sớm' framing) and `unknown` uses average framing. Add tests for early + unknown."
    status: completed
  - id: p2-depth-by-tier
    content: "P2 (NEW — the core of the user's ask): Make ANALYSIS DEPTH scale with tier, which today it does NOT. Currently REF_N=5 is fixed (pipelines.py:71) and the flop extraction prompt caps at 'đúng 1–3, tối đa 3 mục' — the SAME or tighter ceiling than win (extraction.py:443–466). So flop does not currently produce more weaknesses/suggestions/refs than win. Change: tier-scaled reference count (flop → more refs e.g. 6–8, hit → fewer e.g. 3) and tier-scaled finding/suggestion ceilings (flop → up to ~5–6 gaps + fixes, hit → 1–3 strengths + ≤1 polish). Update FE caps too (resolveDiagnosisSections.ts:30 slice(0,3))."
    status: completed
  - id: p2-section-weighting
    content: "P2: Confirm v6 diagnosis section TITLES already adapt to tier (diagnose_sections.py VIDEO_SECTION_DEFAULT_TITLES — hit 'Đang làm tốt', average 'Điểm mạnh và khoảng trống', flop 'Vấn đề chính'). Wire the p2-depth-by-tier counts into salience gating so the number of emitted sections/findings matches depth. Acceptance test: a flop fixture yields strictly MORE gap findings + MORE reference videos than a hit fixture of the same niche."
    status: completed
  - id: p3-unify-videobody-header
    content: "P3: Collapse VideoBody header forks — single kicker derived from tier (PHÂN TÍCH VIDEO / CAROUSEL + PerformanceTierChip), single headline style. Remove the isFlop-only flop kicker branch. Keep tier-correction note as a neutral tier message."
    status: completed
  - id: p3-merge-flop-only-blocks
    content: "P3: Fold flop-only blocks (FlopDiagnosisStrip, view-improvement scenarios, header 'Viết lại kịch bản' CTA) and win-only block ('3 điều bạn có thể copy') into tier-conditioned rendering inside the unified diagnosis sections / a single tier-aware block. Drive purely off performance_tier, not viewMode."
    status: completed
  - id: p3-simplify-coherence
    content: "P3: After UI forks are tier-driven, simplify effectiveVideoReportMode usage so VideoBody reads performance_tier directly for framing decisions; keep effectiveVideoReportMode only where the stored mode field is genuinely needed. resolveDiagnosisSections title shim becomes tier-based."
    status: completed
  - id: p4-td4-resume
    content: "P4: TD-4 SSE resume — stop persisting/replaying videoMode in sseResume; confirm reconnection replays identical content from performance_tier without the mode field. Add resume test without videoMode."
    status: completed
  - id: p4-cleanup-stale
    content: "P4: Remove the stale 'FE fires parallel win+flop' documentation in comment_radar_cache.py (VideoScreen + /app/video are gone; answer-session fires a single turn). Audit comment_radar dedupe lock — keep the lock (still useful) but fix the rationale."
    status: completed
  - id: p4-test-migration
    content: "P4: Migrate the ~23 test files that pin the two-input model (BE ~10 + FE ~13). Tests should assert tier-driven framing, not user-chosen mode. List in body. typecheck + full vitest + pytest green."
    status: completed
  - id: p4-scope-out-shared-cores
    content: "P4: Explicitly scope-out + document the shared cores that legitimately keep an internal default mode: DiagnosisInput.mode default 'flop' (models.py), marketing_corpus_pick hardcoded win. Add code comments clarifying these are internal, not user-facing."
    status: completed
isProject: false
---

# Unified Video Analysis Flow

**Created:** 2026-06-12 · **Branch:** `main` · **Status:** draft, awaiting human go

## Why

The product asks the user up front "is this a win or a flop?" via two composer
pills ("Phân tích video" = flop framing, "Học video viral" = win framing). But
the system ALSO measures performance objectively via `performance_tier`
(corpus ratio + channel median). These two signals can disagree — and when they
do, a whole coherence layer (`reconcile_video_mode`, `effectiveVideoReportMode`)
exists only to reconcile the conflict. The user's mental model is simpler:
**"analyze my video; tell me what's strong and what's weak."** Whether it leans
strength-heavy or gap-heavy should fall out of the measured tier.

## Architectural decision

**Keep `mode` as an internal, tier-derived field. Remove it only as a user input.**

This is deliberately NOT a "delete mode" refactor. Three things make full removal
high-risk and unnecessary:

1. `VideoPayload.mode` is a **required discriminator** persisted in answer-turn
   JSONB (`report_types.py:589`) and consumed by the FE (`api-types.ts:278`).
   Cache replay reads it. Removing it breaks every stored session.
2. The coherence helpers were **purpose-built** to let measured tier override a
   user-chosen mode (`reconcile_video_mode` only ever flips user `flop` → `win`
   when tier implies a win). We reuse this seam instead of fighting it.
3. `DiagnosisInput.mode` (default `"flop"`, `models.py:1411`) is shared by the
   channel/diagnostic cores. Those are internal and out of scope.

So: input surface shrinks to one pill, `mode` continues to exist downstream but
is **always computed from tier**, never from the user.

## Current coupling (from 2026-06-12 audit)

Full maps: BE audit `172e48ee-166a-4ba1-bd34-c8ac7cc63810`,
FE audit `a633550e-e846-448e-805a-3eb679b20531`.

### Backend (`cloud-run/`)
- `routers/answer.py:47,231` — `video_mode: Literal["win","flop"] | None = None` (optional)
- `answer_session.py:613–626` — sanitizes + passes `mode=video_mode`
- `report_video.py:457–514` — precedence: caller mode → `detect_mode_from_query` → `is_flop_mode`
- `video_analyze.py:229–272,2077–2086,2185–2193,1558–1573` — `is_flop_mode`, override, `resolve_extraction_mode`, `finalize_video_narrative_layer` re-reconcile
- `video_report_coherence.py:61–157` — `reconcile_video_mode`, `resolve_extraction_mode`, `pipeline_reconcile_mode`
- `services/extraction.py:443–466` — three Gemini `mode_block` prompts (win/average/flop)
- `pipelines.py:1970–1978` — `run_video_diagnosis` is **already tier-native** (no win/flop input)
- `diagnose_sections.py:241–298` — `VIDEO_SECTION_DEFAULT_TITLES` keyed by `(section_id, tier)`; **already tier-expressive**
- `report_types.py:589` — `VideoPayload.mode` required (KEEP)
- `models.py:1411` — `DiagnosisInput.mode` default `"flop"` (internal; KEEP)
- `marketing_corpus_pick.py:19` — hardcoded win (internal; KEEP)

### Frontend (`src/`)
- `lib/studioComposer.ts:11–47` — two pills + `videoModeForPill`
- `lib/answerHandoff.ts:5–71` — `AnswerHandoffMode`, `?mode=`, defaults `"win"`
- `routes/_app/answer/AnswerScreen.tsx:142,421,668,761,900–901,989,1075,1223` — mode plumbed everywhere
- `hooks/useSessionStream.ts:146,262,304` — `videoMode` → POST `{ video_mode }`
- `lib/sseResume.ts:71,149–155` — persists `videoMode` (TD-4)
- `components/v2/answer/video/VideoBody.tsx:182–192` + many forks — `viewMode`/`isFlop`
- `lib/videoReportCoherence.ts:16–46` — `tierImpliesWinFraming`, `effectiveVideoReportMode`
- `lib/resolveDiagnosisSections.ts:46–47` — mode-based title shim
- `lib/intentCtaSuggestions.ts:71,85–91` — `ctx.mode` branches (Soi kênh / Sửa hook)
- Deep links hardcoding `mode=win`: `BreakoutGrid.tsx:38`, `PatternModal.tsx:161`, `IdeaBlock.tsx:120`, `trendsVideoHandoffPath`, `inheritHandoffFromSearch`
- `PerformanceTierChip.tsx`, `KpiGrid` — **already tier-driven, independent of mode**

### Stale (NOT a blocker — clean up)
- `comment_radar_cache.py:13–22` documents "VideoScreen fires two parallel
  win+flop analyze calls." **No longer true** — `/app/video` route + `VideoScreen`
  were removed; the answer-session path fires a single turn. The per-video lock
  is still worth keeping, but the rationale comment is wrong.

---

## Sequencing

```
P0 (BE contract)  ──►  P1 (entry surface)  ──►  P2 (tier synthesis)  ──►  P3 (UI forks)  ──►  P4 (resume + cleanup + tests)
```

- **P0 must land first** — it guarantees that once P1 stops sending a user mode,
  the stored `mode` is still correct (tier-derived). Ship + verify in prod before P1.
- **P1 and P2 can run in parallel** after P0 (entry vs synthesis are independent).
- **P3 depends on P2** (UI reads the tier-driven output).
- **P4 last** — resume + test migration + stale-doc cleanup are finishing moves.

---

## Phase 0 — BE contract (tier always wins)

### p0-derive-mode-from-tier
**Files:** `video_report_coherence.py:61–157`, `video_analyze.py:1558–1573,2077–2086`, `report_video.py:457–514`
**Change:** At `finalize_video_narrative_layer` / `pipeline_reconcile_mode`, make
the final stored `mode` a pure function of the refined `performance_tier`
(hit→win, average/early/unknown→average framing→win-leaning, flop→flop). Any
caller-supplied `video_mode` or `detect_mode_from_query` result is reduced to an
advisory that **cannot** override the measured tier.
**Acceptance:**
- `VideoPayload.mode` still always populated (no schema change).
- New test: caller `mode="flop"` on a `tier="hit"` video → stored `mode=="win"`.
- Existing `reconcile_video_mode` tests still green (behavior is a superset).

### p0-soften-query-detect
**Files:** `report_video.py:389–414` (`detect_mode_from_query`)
**Change:** Keep the keyword detector but route its result only into a tone hint,
never the pipeline branch. Update the docstring precedence list.
**Acceptance:** A query "tại sao video này flop" on a hit-tier video does NOT
produce flop framing. Test added.

---

## Phase 1 — Collapse entry surface

### p1-single-composer-pill
**Files:** `lib/studioComposer.ts:11–47`, `components/v2/QueryComposer.tsx`, `routes/_app/home/HomeScreen.tsx`, `routes/_app/answer/AnswerScreen.tsx`, `components/v2/answer/FollowUpComposer.tsx`
**Change:** `STUDIO_COMPOSER_PILLS` keeps one video pill (`"Phân tích video"`).
Drop `video_win`. Remove `videoModeForPill`. One placeholder.
**Acceptance:** Composer renders one video pill; submitting a TikTok URL produces
a handoff path with no `mode`. `studioComposer.test.ts` updated.

### p1-drop-mode-from-handoff
**Files:** `lib/answerHandoff.ts:18–71`, `routes/_app/answer/AnswerScreen.tsx:421`
**Change:** `buildAnswerHandoffPath` no longer appends `?mode=` for video entry.
`parseAnswerHandoffParams` still reads a legacy `?mode=` if present (shared old
links) but it is advisory only. Remove the forced `params.set("mode","win")`.
**Acceptance:** Fresh entries have no `mode` in URL; old links with `?mode=flop`
still load (and tier decides framing). Tests updated.

### p1-fix-deeplinks
**Files:** `BreakoutGrid.tsx:38`, `PatternModal.tsx:161`, `IdeaBlock.tsx:120`, `trendsVideoHandoffPath`, `inheritHandoffFromSearch` (`lib/answerHandoff.ts:58–71`)
**Change:** All five hand off a URL with no `mode`.
**Acceptance:** Grep shows no remaining `mode: "win"` / `mode=win` literals in
these entry points. `BreakoutGrid.test.tsx` updated.

### p1-stop-sending-video-mode
**Files:** `hooks/useSessionStream.ts:146,262,304`, `routes/_app/answer/answerStreamTurn.ts:49`
**Change:** Drop `videoMode` from stream args + POST body for fresh sessions.
BE field remains optional for back-compat.
**Acceptance:** Network POST to `/answer/.../turns` no longer includes
`video_mode`. BE still returns a correct tier-derived report.

---

## Phase 2 — Tier-driven synthesis (all 5 tiers)

### Depth differentiation — the core requirement (per user, 2026-06-12)

The product intent: **"if flop → more weaknesses → more suggestions + reference
videos so they know how to fix."** The audit found this is **NOT implemented today**:

| Lever | Today | Target |
|-------|-------|--------|
| Reference videos | `REF_N = 5` **fixed** for all tiers (`pipelines.py:71`) | flop → 6–8 refs; average → ~5; hit → 3 |
| Findings ceiling | win "0–3", average "0–3", **flop "đúng 1–3, tối đa 3"** (`extraction.py:443–466`) — flop is the SAME or tighter | flop → up to 5–6 gaps; hit → 1–3 strengths + ≤1 polish |
| FE finding cap | `flopIssues.slice(0, 3)` (`resolveDiagnosisSections.ts:30`) | scale with tier |

So differentiation today is **tone only** (titles/framing), not **depth/quantity**.
This phase adds the depth scaling the user wants. Without it, a flop video gives
the creator no more fixes than a win video — which defeats the purpose.

### p2-depth-by-tier
**Files:** `pipelines.py:71` (`REF_N`), `services/extraction.py:443–466` (mode_block caps), `services/references.py:217`, `src/lib/resolveDiagnosisSections.ts:30`
**Change:** Introduce tier-scaled depth: a small map `tier → {ref_n, max_findings}`.
flop pulls more reference videos + allows more gap findings/fixes; hit pulls fewer
refs + caps gaps low (lead with strengths). Update the flop `mode_block` ceiling
above win. Update the FE `slice(0,3)` to read the tier-scaled cap.
**Acceptance:** Flop fixture returns strictly more reference videos AND more gap
findings than a hit fixture in the same niche. No fabricated findings (empty when
no evidence — the existing "TUYỆT ĐỐI không bịa lỗi" guard stays).

### p2-tier-driven-synthesis
**Files:** `video_report_coherence.py` (`resolve_extraction_mode`), `services/extraction.py:443–466`
**Change:** Ensure `resolve_extraction_mode` maps every tier:
hit→win, average→average, **early→average (never flop)**, unknown→average,
flop→flop. The `early` framing must say "số liệu còn sớm" (matches
`PerformanceTierChip` "MỚI ĐĂNG" neutral chip), not a flop verdict.
**Acceptance:** Tests for `early` and `unknown` tiers added; neither produces
flop framing or the `ERR_fallback_extraction` flop fallback.

### p2-section-weighting
**Files:** `diagnose_sections.py:241–298` + salience gating, `output_redesign.py:681–688`
**Change:** Verify (and extend if needed) that flop tier surfaces gap-weighted
findings and hit tier surfaces strength-weighted findings. Titles are already
tier-keyed ("Đang làm tốt" / "Điểm mạnh và khoảng trống" / "Vấn đề chính").
**Acceptance:** New test: a flop fixture yields more gap findings than strengths;
a hit fixture yields more strengths than gaps. Title matches tier.

---

## Phase 3 — Unify UI forks (VideoBody)

### p3-unify-videobody-header
**Files:** `VideoBody.tsx:459–523`
**Change:** One kicker block derived from tier + `PerformanceTierChip` (drop the
`isFlop` flop-kicker branch). One headline style (pick the cleaner of `gv-serif`
vs `gv-tight`, applied regardless of tier). Keep the "đang breakout" note but as
a neutral tier message.
**Acceptance:** `VideoBody.test.tsx` — header renders the same shell for flop and
hit fixtures; only the tier chip + finding weighting differ.

### p3-merge-flop-only-blocks
**Files:** `VideoBody.tsx:443–456,525–552,731–761`, `blocks/FlopDiagnosisStrip.tsx`
**Change:** `FlopDiagnosisStrip`, view-improvement scenarios, the "Viết lại kịch
bản" header CTA, and the win-only "3 điều bạn có thể copy" block become
tier-conditioned within the unified flow (driven by `performance_tier`, not
`viewMode`). Low-tier → show gaps + improvement scenarios; high-tier → show
strengths/lessons. They are no longer mutually-exclusive "modes."
**Acceptance:** A flop fixture still shows improvement scenarios; a hit fixture
still shows lessons — but both come from one code path keyed on tier.

### p3-simplify-coherence
**Files:** `VideoBody.tsx:182–192`, `lib/videoReportCoherence.ts`, `lib/resolveDiagnosisSections.ts:46–47`
**Change:** VideoBody framing decisions read `performance_tier` directly.
`effectiveVideoReportMode` is retained only where the persisted `mode` field is
genuinely consumed. `resolveDiagnosisSections` title shim switches to tier.
**Acceptance:** Grep: VideoBody layout branches reference `performanceTier`/tier
helpers, not `viewMode === "flop"`. `videoReportCoherence.test.ts` still green.

---

## Phase 4 — Resume, cleanup, tests

### p4-td4-resume
**Files:** `lib/sseResume.ts:71,149–155`
**Change:** Stop persisting/replaying `videoMode`. Confirm TD-4 reconnection
replays identical content from `performance_tier`.
**Acceptance:** Resume test without `videoMode`; replayed turn matches original.

### p4-cleanup-stale
**Files:** `cloud-run/getviews_pipeline/comment_radar_cache.py:13–22`
**Change:** Rewrite the stale rationale (VideoScreen/`/app/video` are gone; single
turn now). Keep the per-video asyncio lock; fix only the comment.
**Acceptance:** Comment no longer claims parallel win+flop calls. Lock behavior
unchanged; dedupe test still green.

### p4-test-migration
**BE (~10):** `test_video_analyze.py`, `test_video_analyze_on_demand.py`,
`test_report_video.py`, `test_video_report_coherence.py`, `test_tier_bias_guards.py`,
`test_report_types_video.py`, `test_extract_video_errors_hi5.py`,
`test_marketing_corpus_pick.py`, `test_analysis_depth.py`, `test_comment_radar_cache_dedupe.py`
**FE (~13):** `VideoBody.test.tsx`, `studioComposer.test.ts`, `videoReportCoherence.test.ts`,
`intentCtaSuggestions.test.ts`, `AnswerScreen.test.tsx`, `answerHandoff.test.ts`,
`sseResume.test.ts`, `QueryComposer.test.tsx`, `HomeScreen.test.tsx`,
`BreakoutGrid.test.tsx`, `IntentCtaRail.test.tsx`, `resolveDiagnosisSections.test.ts`
**Change:** Assert tier-driven framing, not user-chosen mode.
**Acceptance:** `npm run typecheck`, full `vitest run`, and `pytest` all green.

### p4-scope-out-shared-cores
**Files:** `models.py:1411` (`DiagnosisInput.mode`), `marketing_corpus_pick.py:19`
**Change:** Add code comments clarifying these defaults are internal (channel /
marketing cores), not user-facing video-analysis inputs. No behavior change.
**Acceptance:** Comments present; grep confirms no user path sets them.

---

## Out of scope
- Channel diagnosis (`/channel/diagnose`) win/flop framing — separate model.
- URL-less diagnostic (`report_diagnostic.py` own_flop_no_url) — keeps its own copy.
- Removing `VideoPayload.mode` from storage — explicitly KEPT (back-compat).
- Marketing corpus path — stays win-pinned (internal).

## Breaking-change analysis

**No hard breaks** (verified):
- Stored data: `VideoPayload.mode` / `report.mode` KEPT → cache replay + answer-turn
  JSONB unaffected.
- Old shared links `?mode=flop`: parse stays tolerant (advisory) → still load.
- Schema: no field removed from request/response; `video_mode` POST field stays
  optional on the BE for back-compat.

**One subtle behavior change to manage (the user's exact worry):**
- For **cohort-less videos** (`performance_tier == "unknown"` — new niche, thin
  corpus), the system genuinely cannot measure win vs flop. Today the user's pill
  choice resolves it. After P1 strips the pill, resolution falls to `is_flop_mode`
  absolute thresholds, which the code itself flags as less accurate. A genuine flop
  in a thin niche could mis-render as "average" → fewer gaps → the creator does NOT
  get the fixes they need.
- **Mitigation (already folded into p0-soften-query-detect):** when tier is
  UNKNOWN, the query-text hint becomes the deciding signal. So a user typing
  "tại sao video này flop" still gets full flop depth even with no cohort. The
  system "still knows win vs flop" — from measurement when it can, from the user's
  words when it can't.

**In-flight sessions during P4 deploy:**
- Sessions started before the `videoMode` drop (P1/P4) replay from stored `mode`
  (kept) → no break. New sessions simply omit the field.

## Risk + rollback
- Each phase is independently revertable. P0 is the safety net: even after P1
  strips the user input, stored `mode` stays correct because it is tier-derived.
- Rollback P1 by re-adding the second pill + `?mode=` (data unaffected).
- Old shared links with `?mode=flop` keep working (advisory parse retained).
- P2 depth scaling is env-tunable (the tier→{ref_n,max_findings} map can revert to
  flat values) so a quality regression rolls back without code surgery.
