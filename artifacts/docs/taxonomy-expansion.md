# content_format Taxonomy Expansion — Design Spec

**Status:** Wave 5+ design-doc commit (a): scaffold.
**Audience:** engineering (to implement if greenlit) + reviewers.
**Related:** `artifacts/docs/implementation-plan.md` Wave 5+, the
`classify_format` TAXONOMY LOCK docstring in
`cloud-run/getviews_pipeline/corpus_ingest.py:564`, and the Wave 5+
expanded eval harness at `tests/test_classifier_eval.py` (54-item
golden set, MIN_ACCURACY=0.88).

This commit pins the *what-for* and *what's-in-the-way* before commit
(b) proposes buckets and commit (c) specs the build. If you're
reading this before (b) lands, you know the decision being made, not
the outcome.

---

## 1. The problem

`video_corpus.content_format` is a 15-value taxonomy. **37% of rows
(669/~1,830) land in the `other` catch-all** because they don't fit
any bucket. The `other` residual is concentrated in a handful of
niches:

| niche | other rows | dominant tone |
|---|---:|:---|
| 17 (Gaming / esports)         |  82 | entertaining |
| 13 (Comedy / entertainment)   |  82 | humorous |
| 6  (Aspirational lifestyle)   |  76 | entertaining |
| 11 (Education)                |  62 | educational |
| 16 (Travel / tourism)         |  57 | entertaining |
| 8  (Fitness / gym)            |  50 | educational |
| 21 (Sports / outdoor)         |  38 | entertaining + inspirational |

Downstream consequence: `niche_intelligence.format_distribution` —
the JSONB aggregate that feeds Pattern + Ideas + Diagnosis reports —
shows `other: 37%` for nearly every niche. The reports' "top format
in your niche" insight degrades to "most videos don't fit any
category we track", which is accurate but unactionable.

---

## 2. Two paths (the decision)

**Path A — Expand the taxonomy.** Add 3-5 new buckets covering the
dominant "other" patterns (gaming, comedy skits, educational content
the tutorial regex misses, short highlight clips). Commit (b)
proposes the exact bucket list + per-bucket heuristics.

  - **Benefit:** `other` drops from 37% → ~19% (estimated on the
    current corpus; commit (b) pins the rough-cut numbers). Reports
    gain a meaningful "top format" insight for the gaming / comedy /
    education-heavy niches.
  - **Cost:** atomic 7-layer refactor. The TAXONOMY LOCK docstring
    enumerates the impacted files (corpus_ingest, output_redesign's
    FORMAT_ANALYSIS_WEIGHTS, gemini.py prompt injection,
    layer0_niche, layer0_migration, niche_intelligence
    materialized-view, prompts.py). Plus a SQL backfill on the live
    corpus — stale `content_format` values silently fall through to
    the `other` branch of FORMAT_ANALYSIS_WEIGHTS, degrading
    diagnosis prompts until the UPDATE runs.

**Path B — Accept `other` as terminal.** Document that the residual
is a product-wide known-unknown; surface "other" explicitly in
reports as "không có công thức chính" instead of mis-branding it.
Zero code change.

  - **Benefit:** no migration risk. The taxonomy stays small + stable.
  - **Cost:** the 37% residual persists. Reports for gaming / comedy
    / education niches stay light on the "top format" dimension,
    which is the niche's most intuitive slot.

**Recommendation (this doc):** Path A, but scoped. Commit (b)
proposes 4 buckets — gameplay, comedy_skit, lesson, highlight — that
rough-cut to ~48% of the current `other` residual. The remaining
~52% stays `other` because forcing heterogeneous content into false
labels would degrade downstream reports more than the `other`
residual does. Commit (c) estimates the effort (~1 week) + pins the
exit criteria.

---

## 3. The taxonomy-lock constraint

From `classify_format` docstring — the 7 call sites that read
`content_format` and how each reacts to an unknown value:

| Layer | What it does with `content_format` | Failure mode on unknown |
|---|---|---|
| `corpus_ingest.py` | writes it into the DB column | new value lands in DB, no crash |
| `output_redesign.py` `FORMAT_ANALYSIS_WEIGHTS` | switch table: per-format signal weights for the diagnosis prompt | unknown key → fallback to `other` weights; degrades diagnosis framing silently |
| `gemini.py` | passes format string into the synthesis prompt context | Gemini sees a word it hasn't been shown examples for; no hard break but quality drops |
| `layer0_niche.py` | aggregates "top hook × top format" per week | unknown value dilutes the formula-detection ranking |
| `layer0_migration.py` | groups migration signals by week × format | unknown value creates a new ungrouped bucket in the output |
| `niche_intelligence` MV | `format_distribution` JSONB aggregation | unknown value surfaces in the %-distribution |
| `prompts.py` | format_distribution injected into corpus-citation blocks | Gemini reads the new key; no-op unless the string is gibberish |

**Atomic change requirement:** adding a new bucket means touching all
7 layers AND running a SQL backfill on existing rows in one migration
window. Skipping the backfill leaves old rows at `other` permanently;
skipping a code layer leaves that layer's behaviour undefined on
new-bucket rows.

**Pre-check:** commit (c) specifies "add new values to
FORMAT_ANALYSIS_WEIGHTS FIRST, run the migration + backfill SECOND,
then update `classify_format` THIRD" — the docstring's own
prescription, which we honor here.

---

## 4. Related prior work (learned from)

- **Wave 0 `content_format_reclassify.py`** — already does a SQL
  catch-up from `other` → detected bucket when a regex tweak adds a
  new signal. Same code path we'd reuse for the taxonomy-expansion
  backfill; no new tooling needed.
- **Wave 5+ content_format golden set** — just landed at 54 items /
  0.907 accuracy / 0.88 floor. Commit (c) specs adding ~3 golden
  items per new bucket (12-15 total) so the eval harness locks the
  new buckets' accuracy from day one.
- **Wave 3 viral-alignment-score design doc** — structurally what
  this doc mirrors. That doc said "backtest first, decide after"; we
  do the same: commit (b) proposes buckets, commit (c) sets the
  exit criteria (accuracy floor, `other` residual shrink), a
  follow-up implementation PR would then run the backfill and
  measure against the criteria.

---

## 5. What this spec does NOT cover yet

- **Exact bucket labels + per-bucket heuristics.** Commit (b).
- **Implementation effort + backfill plan + validation gates.**
  Commit (c).
- **Gemini-classification alternative.** The classify_format
  docstring called out a deferred proposal (M.8) to replace regex
  with Flash-Lite classification. That's out of scope here — this
  doc proposes regex-heuristic expansions only, same deterministic
  model. A separate design doc is needed if the regex path saturates.
- **Per-niche taxonomy.** Some new buckets (gameplay) are niche-
  specific. Whether to gate them by niche_id (like the existing
  mukbang niche=4 heuristic) or keep them global is a bucket-level
  decision in commit (b).

These three sections land in commits (b) and (c).

---

## 6. Proposed buckets (v1)

Four new buckets. Each one gets (a) a classifier heuristic grounded
in existing `classify_format` patterns — regex + optional niche /
tone / scene gates, (b) an estimated coverage count against the
current 669 `other` rows, (c) a first-cut
`FORMAT_ANALYSIS_WEIGHTS` signal prioritization for the diagnosis
prompt.

The list is deliberately short (4, not 8). Each bucket must earn
its slot against three tests:

1. **≥ 5% of the current `other` residual** — smaller than that and
   the taxonomy burden outweighs the format_distribution signal.
2. **Clean heuristic** — ideally one regex + one gate (niche OR
   tone OR scene). A bucket that needs 5 signals to detect is a
   sign the content is still heterogeneous underneath.
3. **Actionable diagnosis** — the downstream `FORMAT_ANALYSIS_WEIGHTS`
   entry must surface DIFFERENT signal priorities from `other`. A
   bucket that's "just a label" with no effect on the prompt is
   cosmetic and doesn't belong in the 7-layer lock.

### 6.1 `gameplay`

Video of someone playing a video game — commentary, reactions,
highlights, tournament clips. The single biggest `other` cohort.

- **Niche gate:** `niche_id = 17` (Gaming & Esports).
- **Topic signal:** any of `Gaming`, `Esports`, `Liên Quân`, `Arena
  of Valor`, `Honor of Kings`, `Roblox`, `Attack on Titan`, specific
  game titles (add as observed).
- **Heuristic:** niche=17 OR (any topic matches the game-keyword
  set). Put it high in priority order — before `mukbang` /
  `storytelling` / `dance`, because gaming clips frequently trigger
  those with their entertaining tone + action scenes.
- **Coverage:** **~85 / 669 `other` rows (12.7%)**. Live breakdown
  skews entertaining (47) + educational (16 — "game guide" /
  "character tutorial" pattern) + authoritative (6).
- **`FORMAT_ANALYSIS_WEIGHTS` skeleton:**
  - `hook_strength`: high (the first 2s of a gameplay clip decides
    whether the viewer cares about the match result)
  - `audio_cue`: high (commentator voice energy drives retention)
  - `scene_pacing`: high (cuts between gameplay feed + overlay)
  - `text_overlay_count`: medium (kill counters, score overlays)
  - `cta_presence`: skip (gameplay rarely carries a CTA)

### 6.2 `comedy_skit`

Scripted dialogue comedy — setup + punchline, often 2-3 characters
with a reveal. Distinct from `storytelling` (recall / narration)
and `pov` (first-person monologue).

- **Niche gate:** `niche_id = 13` (Comedy & Entertainment) is a
  strong signal but comedy leaks into niches 6/11/19 too.
- **Tone signal:** `tone = 'humorous'`.
- **Topic signal:** `comedy`, `skit`, `humor`, `prank`, `funny`,
  `family chaos`, `relatable memes`.
- **Heuristic:** (niche=13 AND tone=humorous) OR (any topic matches
  the comedy-keyword set). Must land AFTER `storytelling` in the
  priority order so narrative-recall humor stays where it is.
- **Coverage:** **~91 / 669 rows (13.6%)**. Live: 40 humorous +
  entertaining / conversational tones.
- **`FORMAT_ANALYSIS_WEIGHTS` skeleton:**
  - `hook_strength`: high (first-line setup is the whole contract)
  - `audio_cue`: high (delivery timing, laugh tracks, SFX)
  - `scene_pacing`: high (cut timing IS the punchline)
  - `text_overlay_count`: medium (subtitle-dependent for VN viewers
    with sound off)
  - `cta_presence`: low — skits lean on the punchline, not a CTA.

### 6.3 `lesson`

Educational content that's NOT a how-to / procedural tutorial.
Language vocab drills, parenting advice, "word of the day" type
content. The tutorial regex intentionally requires a procedural
verb (`hướng dẫn`, `cách làm`, `bước 1`); `lesson` covers the
broader educational-but-non-procedural content that currently
falls through.

- **Niche gate:** `niche_id = 11` (Education) is the primary
  concentration; extends to niche 7 (parenting advice), niche 15
  (finance education).
- **Tone signal:** `tone IN ('educational', 'authoritative')`.
- **Topic signal:** `vocabulary`, `grammar`, `language learning`,
  `parenting tip`, `finance education`, `kinh nghiệm`, `bài học`,
  `từ vựng`.
- **Heuristic:** tone=educational|authoritative AND (niche=11 OR
  lesson-topic match). Must land AFTER `tutorial` in priority so
  procedural content keeps its bucket; `lesson` is the fallback
  for "educates without a step-by-step".
- **Coverage:** **~45 / 669 rows (6.7%)**. Concentrated: 37 of
  niche 11's 62 `other` rows are tone=educational.
- **`FORMAT_ANALYSIS_WEIGHTS` skeleton:**
  - `audio_transcript_density`: high (lessons carry info in speech)
  - `text_overlay_count`: high (vocabulary drills / definitions on
    screen)
  - `scene_pacing`: medium (can be slow — trivia + repeat)
  - `hook_strength`: medium (less first-frame driven than gameplay)
  - `cta_presence`: medium (classroom-style "follow for more" is
    common)

### 6.4 `highlight`

Short reaction / moment clips — sports goals (niche 21), travel
"wow" vignettes (niche 16), celebrity reaction (niche 6), gaming
montage (niche 17 — but gaming wins first). Typically music-only
or light narration, 5-10 scenes of rapid cuts, one "payoff" moment.

- **Niche gate:** `niche_id IN (6, 16, 21)` (aspirational / travel
  / sports) + a residual in `17`.
- **Tone signal:** `tone IN ('entertaining', 'humorous',
  'inspirational')`.
- **Scene signal:** scenes ≥ 4 AND `action` or `broll` dominant.
- **Transcript signal:** short / music-only (< 80 chars including
  "[âm nhạc]"-style placeholders) helps disambiguate from
  `storytelling` or `vlog`.
- **Heuristic:** niche IN (6,16,21) AND tone IN (entertaining,
  humorous, inspirational) AND (scene_count ≥ 4) AND (short
  transcript OR music-only marker). Lands AFTER `dance` (all-
  action) and `faceless` (no face_to_camera scenes) in the
  priority order.
- **Coverage:** **~101 / 669 rows (15.1%)** — the biggest cohort.
  Mostly niche 16 travel moments + niche 6 lifestyle aspirational
  + niche 21 sports highlights.
- **`FORMAT_ANALYSIS_WEIGHTS` skeleton:**
  - `scene_pacing`: high (montage timing is the format)
  - `audio_cue`: high (music drop / sync is the emotional payoff)
  - `hook_strength`: medium (first clip sets expectation, payoff
    comes later)
  - `text_overlay_count`: low (highlights rely on visual not
    explanatory)
  - `cta_presence`: skip

### 6.5 Combined coverage

| Bucket        | Est. new rows | % of current `other` |
|:--------------|--------------:|---------------------:|
| `gameplay`    |            85 |                12.7% |
| `comedy_skit` |            91 |                13.6% |
| `lesson`      |            45 |                 6.7% |
| `highlight`   |           101 |                15.1% |
| **Total**     |       **322** |            **48.1%** |

`other` drops from 669 / 1,830 rows (**37%**) → 347 / 1,830 rows
(**~19%**) post-backfill. The remaining ~347 rows are genuinely
heterogeneous: crime news clips, music-only fitness montages,
cinematic auto B-roll, K-drama reposts, one-off habit monologues,
niche-feature tips that slip all four heuristics. Forcing them
into any single new bucket would degrade reports more than the
residual does — this is the "Path A scoped" recommendation from
commit (a).

---

## 7. Priority order (where each new bucket lands)

`classify_format`'s priority order is intentional — highest-
specificity-first. Proposed insertion points:

```
 1. mukbang       (unchanged — niche=4 + scenes≥10 heuristic)
 2. grwm          (unchanged)
 3. NEW: gameplay (niche=17 OR game-title topic; before mukbang-like
                   gaming rows get captured by entertainment signals)
 4. recipe        (unchanged)
 5. tutorial      (unchanged — procedural verbs)
 6. NEW: lesson   (broader educational, AFTER tutorial)
 7. comparison    (unchanged)
 8. NEW: comedy_skit  (niche=13 + humorous; BEFORE storytelling so
                       pure-dialogue jokes don't capture recall-style
                       narrative)
 9. storytelling  (unchanged — catches narrative recall)
10. before_after  (unchanged)
11. pov           (unchanged)
12. outfit_transition (unchanged)
13. vlog          (unchanged)
14. dance         (unchanged)
15. faceless      (unchanged)
16. NEW: highlight (LAST positive match — after dance + faceless
                    because highlight's heuristic is the loosest
                    and would catch everything if it ran first)
17. other         (terminal)
```

Priority-shift risk: inserting `gameplay` at position 3 preempts
`recipe` / `tutorial` for niche-17 rows with cooking or
instructional topics (there are a few gaming channels that show
"how to play X"). Commit (c) specifies a golden-set regression
test to catch this — if any existing `tutorial` / `recipe` row
for niche 17 flips to `gameplay`, that's a signal the heuristic
is too loose.

---

## 8. Implementation plan

### 8.1 File-by-file change list

Per the taxonomy-lock docstring in
`cloud-run/getviews_pipeline/corpus_ingest.py:564`, a single
migration must touch ALL of the following — partial landings
degrade silently. Estimated ~1 week total:

| File | Change | Cost |
|---|---|---|
| `cloud-run/getviews_pipeline/corpus_ingest.py` | Extend `classify_format` with 4 new branches per §6 heuristics; insert at the §7 priority positions; update the TAXONOMY LOCK docstring to say 19 values not 15. | 0.5d |
| `cloud-run/getviews_pipeline/output_redesign.py` | Add 4 keys to `FORMAT_ANALYSIS_WEIGHTS` with §6 skeletons; update `get_analysis_focus()` switch to route the new formats to format-specific prompt snippets. | 1d (prompt copy is the long pole) |
| `cloud-run/getviews_pipeline/gemini.py` | No code change — it just passes `content_format` through. Verify via grep that no call site hardcoded a 15-value check. | 0.1d |
| `cloud-run/getviews_pipeline/layer0_niche.py` | Formula detection (top hook × format) re-runs on next Layer 0 cron tick — no code change but dogfood the output to confirm new formats surface in top-formula rankings where expected (gameplay × curiosity_gap hook, comedy_skit × bold_claim, etc.). | 0.2d verify |
| `cloud-run/getviews_pipeline/layer0_migration.py` | Migration grouping key is `content_format` — will automatically pick up new values. No code change; verify via dogfood. | 0.1d verify |
| `niche_intelligence` MV definition | `format_distribution` JSONB aggregates over `video_corpus.content_format` — MV refresh picks up new values automatically. No schema change; run `refresh_niche_intelligence()` after the backfill. | 0.2d verify |
| `cloud-run/getviews_pipeline/prompts.py` | `format_distribution` is injected via `corpus_citation` block; new format keys flow through unchanged. Spot-check 3 diagnosis prompts to confirm Gemini handles the new bucket names gracefully. | 0.1d |
| `content_format_reclassify.py` backfill | Re-run over existing `other` rows; re-classifier pushes the ~322 matching rows into their new buckets. Zero Gemini cost (regex only). | 0.3d + the actual run |
| `tests/test_classify_format.py` | Add ~6 regression tests per new bucket (24 total): positive match + priority-order interactions (e.g. niche-17 tutorial stays tutorial) + defensive negatives. | 0.5d |
| `tests/test_classifier_eval.py` + golden set | Add 3 golden items per new bucket (12 items) to the existing 54-item set. Re-measure accuracy + adjust the floor if needed; new set expected to be ~60 items at ≥ 0.88 floor. | 0.5d |
| `artifacts/docs/implementation-plan.md` | Update Wave 5+ "Taxonomy expansion" row: ongoing → shipped; add a note pointing at this doc. | 0.1d |

**Total: ~3.6 engineering days** (conservative). Previously estimated
at ~1 week in the implementation plan because of the coordination
cost of touching 7 files atomically; the per-file work itself is
small but the deploy sequence matters.

### 8.2 Backfill strategy

Atomic migration window:

1. Land all 7 file changes in a single PR. Do not merge partial —
   rolling one piece to main without the rest leaves the system in a
   mixed-state where new rows use the new taxonomy but
   `FORMAT_ANALYSIS_WEIGHTS` doesn't know about them (diagnosis
   prompts silently fall through to the `other` signal weights).
2. Deploy Cloud Run with the new classifier.
3. Run `content_format_reclassify.py` over existing rows — zero
   Gemini cost, ~45s for 1,830 rows. It re-runs `classify_format` on
   `analysis_json` → UPDATE where the result differs. Log per-bucket
   flip count for the commit (d) decision log.
4. `SELECT refresh_niche_intelligence()` to re-aggregate
   `format_distribution` with the new values.
5. Spot-verify one diagnosis session per new bucket (4 total)
   hitting prod to confirm the prompt routing works end-to-end
   through `FORMAT_ANALYSIS_WEIGHTS`.

No data loss risk — the reclassifier only UPDATEs, never DELETEs,
and if a re-classification flips an `other` to a wrong bucket the
next `content_format_reclassify` run can fix it after a heuristic
tweak.

### 8.3 Validation gates (go/defer decision)

The implementation is conditional on clearing all four:

| Gate | Measurement | Threshold |
|---|---|---|
| `other` residual shrink | Post-backfill: `SELECT COUNT(*) FROM video_corpus WHERE content_format='other'` vs pre-backfill 669 | ≥ 40% drop (i.e. ≤ 400 rows remain `other`) |
| Eval accuracy preserved | `python -m pytest tests/test_classifier_eval.py` | MIN_ACCURACY stays ≥ 0.85 (tighter than the Wave 5+ 0.88 floor because the 12 new golden items should all pass) |
| No legacy miss-flips | Per priority-shift risk in §7: `SELECT content_format FROM video_corpus WHERE content_format != @prev_value AND @prev_value IN ('tutorial','recipe','mukbang','grwm','review')` | Fewer than 5 existing core-bucket rows flip to a new bucket |
| Diagnosis dogfood | 4 sessions (one per new bucket) reviewed by 2 reviewers each | Both reviewers rate "format-specific framing is materially better than it was on 'other'" for at least 3/4 sessions |

**If any gate fails:** revert the reclassifier UPDATE, keep the
code merged (it's a no-op on the `other` rows without the
backfill), file a follow-up PR with the bucket heuristic tuned,
re-run the backfill + gates.

### 8.4 Calendar

| Phase | Work | Days |
|---|---|---|
| 1 — PR assembly | §8.1 file changes + tests + golden set items | 3.5d |
| 2 — Ship | Merge, deploy, run backfill, refresh MV, verify dogfood | 0.5d |
| 3 — Dogfood + tune | 4 sessions across the new buckets; heuristic tweaks if any gate fails | 1-2d |

**Total: ~5-6 working days** to ship + soak. Factor in 2-3 days for
review cycles → **~1-1.5 weeks calendar**.

---

## 9. Out of scope for v1

- **Niche-specific sub-buckets.** `gameplay` could split into
  `esports_highlight` vs `gameplay_walkthrough` vs `game_news` if
  downstream reports benefit. Defer until the single `gameplay`
  bucket is live + the format_distribution reveals whether the
  splits matter.
- **News as a bucket.** The remaining 52% `other` includes a
  recognizable news-clip cohort (crime reports, sports news,
  entertainment news). News is tempting but heterogeneous underneath
  — forcing a rule like "authoritative tone + recent-event topics"
  would capture legitimate analysis content too. Revisit when the
  classifier has per-niche gating sophistication to distinguish
  "niche-specific news" from generic news.
- **Music performance / livestream recap** as dedicated buckets.
  Edge cohorts that would clear test 1 (≥5%) only on specific
  niches. Defer.
- **Gemini-backed classification.** The M.8 proposal the taxonomy-
  lock docstring mentions. Out of scope here — separate design doc
  needed if the regex path saturates after this expansion.

---

## 10. Re-evaluation triggers

Re-open this design doc + revisit scope when ANY of these land:

| Trigger | Why it matters |
|---|---|
| Post-backfill `other` residual stays ≥ 30% | Expansion under-shot — add another round of buckets. |
| Any new bucket sees < 2% usage after 30 days of ingest | Heuristic too narrow or the content cohort genuinely doesn't exist in steady-state. Remove the bucket before it pollutes reports. |
| `format_distribution` in niche 17/13/11/6/16/21 still reads "other: 30%+" | Backfill worked but new ingests land too many rows in `other` — heuristic tuning or additional bucket. |
| Gemini-classification cost drops to < $0.001/video | The deferred M.8 proposal becomes economical. Revisit vs regex. |
| Per-niche split demand surfaces in dogfood | Evidence creators want the `gameplay → esports_highlight` split (see §9). |

---

## 11. Decision log

| Date | Decision | Outcome |
|---|---|---|
| 2026-05-13 | Design doc committed (a)+(b)+(c). Awaiting greenlight on Path A (4-bucket scoped expansion) vs Path B (accept `other`). | — |

Future re-runs append here. Don't squash — decision history is
load-bearing for a 7-layer-atomic refactor.


