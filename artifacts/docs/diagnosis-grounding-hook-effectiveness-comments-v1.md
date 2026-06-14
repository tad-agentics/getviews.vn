# Design — Ground video diagnosis in measured hook-effectiveness + audience comments (v1)

**Status:** Proposed (ready for implementation in Cursor)
**Owner:** —
**Surface:** Cloud Run Python — video diagnosis synthesis (`POST /answer/sessions/{id}/turns` video path)
**Related:** `system-design.md` §16 (diagnosis), `claim_tiers.py`, `corpus-ingest-criteria-v1.md`
**Cost impact:** ~0 (prompt-token only; **no new Gemini/ED calls** on the hot path)

---

## 1. Problem

Two high-value datasets are already computed and already reach the live diagnosis path, but **never reach the synthesis prompt**, so the creator-facing diagnosis can't say *what actually works in your niche* or *what your audience actually said*:

1. **Measured hook effectiveness** — `hook_effectiveness_compute.py` upserts empirical per-`(niche_id, hook_type)` and per-`(content_class_id, hook_type)` lift (`avg_views`, `avg_engagement_rate`, `avg_completion_rate`, `sample_size`, `trend_direction`) weekly. Today it is consumed **only** by the pattern/ideas reports and the script-page UI leaderboard (`script_data.py:55 latest_hook_effectiveness_rows`, `report_pattern_compute.py:898`, `report_ideas_compute.py:377`). The video diagnosis assesses hook quality purely via LLM + heuristics — it ignores the empirical lift table.

2. **Audience comments** — `comment_radar` (sentiment %, purchase-intent count/phrases, questions count) is resolved on the live path (`video_analyze.py:133-160 _ensure_comment_radar_on_out`) and threaded into `ctx_dict` (`gemini.py:1914`, via `build_diagnosis_ctx(..., comment_radar=...)`). But it feeds **only** the seeding-suspicion signal (`signals/distribution.py:365-449`) and is **not rendered into the prompt** — `diagnose_prompts.py` has zero `comment_radar` references. The creator never hears what their viewers reacted to.

**Goal:** make the diagnosis read like an analyst who (a) knows the empirical hook leaderboard for the creator's class, and (b) watched the comment section — **without fabricating numbers** when evidence is thin.

---

## 2. Non-goals

- No new extraction signals (that's the separate retention-curve / info-density work).
- No deepening of `comment_radar`'s extraction yet (quoted-moment / objections / FAQ→next-video is a **follow-up** — see §9). v1 renders what's already extracted.
- No change to the nightly `run_hook_effectiveness` job or `comment_radar_cache` TTL.

---

## 3. Current-state anchors (verified)

| Piece | Location |
|---|---|
| v6 synthesis entry (builds ctx + prompt) | `gemini.py` ~1875–1960 (`comment_radar` param at :1875, ctx build at :1904, prompt build call after) |
| ctx builder (already takes `comment_radar`) | `signals/registry.py build_diagnosis_ctx(...)` |
| prompt builder (does NOT render comments) | `diagnose_prompts.py:277 build_diagnosis_v6_user_prompt(...)` |
| hook-effectiveness writer + table | `hook_effectiveness_compute.py:234` (`hook_effectiveness`, conflict `niche_id,hook_type`); `:267` (`content_class_hook_effectiveness`) |
| hook-effectiveness reader (dedup→latest) | `script_data.py:55 latest_hook_effectiveness_rows(rows)` |
| tier/class benchmark fetch on live path | `video_niche_benchmark.py:502 fetch_video_benchmark_with_axis(...)`, called in `video_analyze.py:588/2106/2718` |
| claim-tier thresholds | `claim_tiers.py` (`hook_effectiveness: 50`, `niche_norms: 30`) |
| comment shape | `comment_radar.py:118 CommentRadar.to_dict()` → `{sampled, sentiment:{positive_pct,negative_pct,neutral_pct}, purchase_intent:{count,top_phrases}, questions_asked, language}` |

---

## 4. Design

Two independent, small additions. Ship behind one flag, gate each on its own evidence tier.

### 4A. Hook-effectiveness grounding

**Fetch (new, on live path).** Add `fetch_class_hook_effectiveness_sync(sb, content_class_id) -> list[dict]` in `video_niche_benchmark.py` (or `hook_effectiveness_compute.py`), reading `content_class_hook_effectiveness` for the resolved `content_class_id`, passed through `latest_hook_effectiveness_rows()` to dedup to the latest `computed_at` per `hook_type`. Fall back to `hook_effectiveness` by `niche_id` when the class table is empty (mirror the benchmark axis ladder). Call it next to the existing `fetch_video_benchmark_with_axis` in `video_analyze.py` so the resolved `content_class_id` is reused.

**Thread it** the same way `comment_radar` is threaded: new optional param `hook_effectiveness: list[dict] | None` on the synthesis fn (`gemini.py`) → `build_diagnosis_ctx(..., hook_effectiveness=...)` → into `ctx_dict`.

**Render it** in `build_diagnosis_v6_user_prompt` as a compact, claim-tier-gated block. Compute the **rank of the user's own hook_type** (`user_analysis.hook_analysis.hook_type`) within its class:

```
HOOK_LEADERBOARD (ngách: <class_vi>, n_class=<Σ sample_size>):
- Hook bạn đang dùng: <hook_vi> — hạng <r>/<n> theo views TB (n=<sample_size>, xu hướng: <trend_vi>)
- Hook mạnh nhất ngách: <top_hook_vi> — views TB cao hơn ~<x>× (n=<sample_size>)
```

**Gating (honesty):**
- Only emit a per-hook row when that bucket's `sample_size >= CLAIM_TIERS["hook_effectiveness"]` (50). Below floor → omit the row (do **not** print a number).
- If the user's hook bucket is below floor but the class top is above floor, still allow "top hook in class is X" but never assert the user's relative rank.
- If nothing clears the floor → emit nothing (the LLM keeps its current heuristic read). Add an instruction line: *"Chỉ dùng số liệu HOOK_LEADERBOARD nếu khối này xuất hiện; KHÔNG tự bịa hạng/bội số."*

**How synthesis uses it:** instruct the prompt (in the existing `hook_analysis` section guidance in `diagnose_prompts.py`) to weave the measured lift into the hook finding's *fix*, e.g. "hook hiện tại là `<X>` — trong ngách, hook `<Y>` cho views TB cao hơn ~3× (n=70); thử mở bằng `<Y-pattern>`." This turns the existing generic hook advice into evidence-backed advice.

### 4B. Comment grounding (render-only)

**No fetch needed** — `comment_radar` is already in `ctx_dict`. Add rendering in `build_diagnosis_v6_user_prompt`:

```
COMMENT_SIGNAL (mẫu <sampled> bình luận):
- Cảm xúc: tích cực <p>%, tiêu cực <n>%
- Câu hỏi lặp lại: <questions_asked> (gợi ý nội dung tiếp theo)
- Ý định mua: <count> — cụm: "<top_phrase_1>", "<top_phrase_2>"
```

**Gating:**
- Only render when `sampled >= COMMENT_MIN_SAMPLE` (propose 8 — matches the seeding-signal floor in `distribution.py:423`) **and** `language in {"vi","mixed"}`. Below that, omit (don't show 0%/empty).
- Instruct: *"COMMENT_SIGNAL phản ánh khán giả thực; nếu `questions_asked` cao, nêu 1 gợi ý nội dung tiếp; nếu cảm xúc tiêu cực cao, soi nguyên nhân. KHÔNG bịa nội dung bình luận."*

**Where it lands in the report:** comment sentiment maps naturally onto the existing `metadata`/context block and the next-steps section (questions → next-video idea). Don't create a new section; enrich existing ones to avoid section-count churn.

---

## 5. Copy rules (mandatory)

All new strings Vietnamese. Obey `.cursor/rules/copy-rules.mdc`: no forbidden openers (`Chào bạn`, `Tuyệt vời`…) or forbidden words (`bí mật`, `công thức vàng`, `triệu view`, `bùng nổ`…). Follow the house formula: **state the data → name the finding → give the specific fix** — which is exactly what measured hook lift + comment signal enable. Use JetBrains Mono for the numeric leaderboard values on the FE if surfaced; for the prompt block, plain text is fine.

---

## 6. Flag + rollout

- `DIAGNOSIS_HOOK_LEADERBOARD` (bool, default `false`) and `DIAGNOSIS_COMMENT_GROUNDING` (bool, default `false`) in `settings.py`.
- **Shadow first:** when off, still fetch + log the would-be block (`[diagnosis_grounding]` structured log) for 3–5 sessions to eyeball quality vs. fabrication risk, then flip on. (Same shadow discipline as `corpus-ingest-criteria-v1.md`.)
- Rollback = flip flags off; no migration.

---

## 7. Telemetry

- Log per diagnosis: `hook_leaderboard_emitted` (bool), `hook_buckets_above_floor` (int), `comment_block_emitted` (bool), `comment_sampled` (int).
- These let you measure coverage (how often real evidence is available pre-launch given the thin corpus) before trusting the copy.

---

## 8. Testing

- **Unit (pure):**
  - `latest_hook_effectiveness_rows` already tested; add a `build_hook_leaderboard_block()` pure fn + tests: above-floor renders rank+multiplier; below-floor omits the number; empty input → "".
  - `build_comment_signal_block()` pure fn + tests: below `sampled` floor → ""; non-vi language → ""; happy path renders sentiment + questions + intent.
- **Prompt-shape test:** assert the blocks appear in `build_diagnosis_v6_user_prompt` output when ctx carries above-floor data, and are absent below floor (guards the no-fabrication contract).
- **No live-Gemini test needed** (deterministic prompt assembly).

---

## 9. Follow-ups (explicitly out of v1)

- Deepen `comment_radar`: quoted-moment mapping, objection clustering, recurring-question → next-video backlog, share-intent ("tag bạn bè"). High value, separate task.
- Feed measured hook lift back into **signal salience** (close the calibration loop) — see the calibration-loop recommendation; `viral_alignment_backtest.py` ρ is computed but never re-weights anything.

---

## 10. Acceptance criteria

1. With above-floor `content_class_hook_effectiveness` data, the diagnosis hook finding cites the creator's hook rank + the class's top hook with real `n=`, and the fix references the higher-lift hook.
2. With sub-floor data, **no** numeric hook claim appears (verified by test).
3. With ≥8 vi comments, the report reflects audience sentiment / a repeated-question next-step; with fewer, nothing is shown.
4. Both behaviors gated by flags; shadow logs present; zero new Gemini/ED calls on the hot path.
5. `npm`/`ruff`/`pytest` clean; copy passes the forbidden-word lint.
