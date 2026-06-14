# Design — Close the calibration loop (outcome-driven rubric re-weighting) (v1)

**Status:** Proposed (ready for implementation in Cursor)
**Owner:** —
**Surface:** Cloud Run Python — `viral_alignment_backtest.py`, signal salience, synthesis confidence
**Related:** `diagnosis-grounding-hook-effectiveness-comments-v1.md`, `diagnosis-retention-curve-structural-v1.md`, `corpus-ingest-criteria-v1.md`
**Cost impact:** ~0 on the hot path (one periodic batch job over corpus; no per-diagnosis Gemini/ED cost)

---

## 1. Problem

The system **measures** whether its rubric predicts reality but never **acts** on the measurement — it's one-directional (maturity Level 1 of 4). The two grounding docs above both surface real evidence into synthesis, but neither corrects the underlying weights that decide what the diagnosis emphasizes. Three concrete open loops:

1. **Viral-score weights are static.** `viral_alignment_backtest.py:61-63` hardcodes `W_HOOK=0.5 / W_FORMAT=0.3 / W_TIME=0.2`; the harness computes Spearman ρ vs `breakout_multiplier` (`:396`), checks a `0.35` gate (`:419-421`), and stores it in `batch_job_runs.summary` for **observability only** (`routers/admin.py` backtest endpoint). Nothing reads ρ to re-tune the weights. The file itself says the calibration suite is "Wave 4" (`:18`).

2. **Signal salience is hand-tuned.** Each signal's `salience: float` (`signals/base.py:26`) is a hardcoded heuristic per module (e.g. `channel_findings.py` `0.92 if n>=5 else 0.85`); the section-emit threshold is a static constant with one env flag (`signals/salience.py`). No signal is ever demoted because it failed to predict outcomes.

3. **Measured hook lift isn't a prior.** `hook_effectiveness` / `content_class_hook_effectiveness` empirically rank hook_type by `avg_views`/`avg_engagement_rate`/`avg_completion_rate` per class with `sample_size` + `trend_direction` (`hook_effectiveness_compute.py`), but only the UI/pattern reports read it.

**Goal:** turn measurement into a **closed loop** — periodically learn weights from corpus outcomes, adopt them only when they *provably* improve prediction on a holdout, and let synthesis lean on calibrated confidence. Keep it conservative (this is pre-launch with a thin corpus): static weights remain the floor/fallback, nothing adopts from thin samples.

---

## 2. Non-goals

- No ML training infra, no gradient descent service. A coarse weight sweep + correlation is sufficient for 3 weights and a handful of signals, and stays auditable.
- No real-time/online learning. Periodic (nightly or weekly) batch recompute, like `run_hook_effectiveness`.
- Doesn't change extraction or the diagnosis schema.

---

## 3. Current-state anchors (verified)

| Piece | Location |
|---|---|
| Viral score + static weights | `viral_alignment_backtest.py:61-63`, score at `:186` (`W_HOOK*hook_align + W_FORMAT*format_align + W_TIME*time_align`) |
| ρ computation + gate + storage | `:239 spearman_rho`, `:396 rho`, `:414-421` (weights echoed, `spearman_gate=0.35`, stored to `batch_job_runs.summary`) |
| Backtest entrypoint (observational) | `:349 run_viral_score_backtest`, admin endpoint in `routers/admin.py` |
| Niche sample gate (graceful fail) | `:139` |
| Per-signal salience field | `signals/base.py:26 salience: float`; module heuristics (`channel_findings.py`, etc.) |
| Section emit threshold (static) | `signals/salience.py` |
| Measured hook lift (already a usable prior) | `hook_effectiveness_compute.py` → tables `hook_effectiveness` (`niche_id,hook_type`), `content_class_hook_effectiveness` (`content_class_id,hook_type`) |
| Claim-tier sample floors | `claim_tiers.py` |

---

## 4. Design — three loops, staged by confidence

Ship **Loop A** first (smallest, safest, immediate value); B and C are follow-ons on the same machinery.

### Loop A — Adaptive viral-score weights (the obvious win)

**New table `signal_calibration`** (migration; register any new cron in `expected_cron_jobs`):

| col | meaning |
|---|---|
| `scope` | `"global"` or `"content_class"` |
| `content_class_id` | nullable (set when scope=content_class) |
| `w_hook, w_format, w_time` | tuned weights (sum normalized to 1) |
| `rho_holdout` | Spearman ρ of tuned score vs breakout on holdout |
| `rho_baseline` | ρ of the static weights on the same holdout |
| `sample_size` | videos used |
| `computed_at` | timestamp |

**New job `run_signal_calibration(client)`** (sibling of `run_hook_effectiveness`, nightly or weekly):
1. Pull a corpus sample with `breakout_multiplier` + the `hook_align/format_align/time_align` components (reuse `viral_alignment_backtest`'s feature extraction).
2. Split train/holdout (e.g. 70/30, fixed seed for reproducibility).
3. **Sweep** weights on a coarse simplex grid (step 0.05, `w*≥0`, `Σ=1`) — ~231 combos, trivial — maximizing train ρ. (Closed-form is possible but the grid is auditable and bounded.)
4. **Adopt-only-if-better guardrail:** write tuned weights **only if** `rho_holdout ≥ max(0.35, rho_baseline + ε)` (ε ~0.02 to avoid noise-chasing) **and** `sample_size ≥` a floor (propose 200 globally, `niche_norms`=30 per class — fall back to global below floor). Otherwise keep static. This makes overfitting/thin-data adoption structurally impossible.
5. Per-`content_class` weights when its sample clears the floor; else inherit `global`.

**Reader `viral_score_weights(content_class_id) -> (w_hook,w_format,w_time)`** — reads `signal_calibration` (class → global ladder), returns the **static constants as the default** when the flag is off or no calibrated row clears the gate. `viral_alignment_backtest.py:186` and any production viral-score caller switch to this reader.

### Loop B — Signal predictive value → salience demotion

Extend the calibration job to compute, per signal type, the correlation between *that signal firing* and `breakout_multiplier` on the corpus sample. Persist a `signal_predictive_rho` per signal (+ class). Then:
- A signal whose ρ is ≈0 or negative across a healthy sample gets a **salience multiplier < 1** applied at manifest build (so it stops crowding the report) — never hard-removed, just demoted, behind the flag.
- Surfaces a per-signal "does this predict?" audit for the team. This replaces hand-tuned `0.92/0.85` heuristics with evidence over time.

### Loop C — Calibrated confidence into synthesis

Feed ρ (and per-hook `sample_size`/`trend_direction`) into the diagnosis prompt's confidence framing (complements the hook-effectiveness doc): when the rubric is well-calibrated for a class (ρ high, sample deep) the copy can be assertive ("hook mạnh là yếu tố dự đoán breakout trong ngách này, n=120"); when ρ is weak/thin, the copy stays hedged. This is the honest-confidence behavior that separates a calibrated system from a confident-sounding one — and it reuses the claim-tier gating already in `claim_tiers.py`.

---

## 5. Guardrails (essential, given thin pre-launch corpus)

- **Static floor always available.** Flag off or gate unmet → exact current behavior. Zero-risk rollback.
- **Holdout improvement required** before adoption (Loop A step 4) — prevents fitting noise.
- **Sample floors** via `claim_tiers.py`; class falls back to global, global falls back to static.
- **Weight bounds** (each `w ∈ [0.1, 0.7]`, `Σ=1`) so no single axis can dominate from a small sample.
- **Auditability:** store `rho_baseline` next to `rho_holdout` so every adoption is explainable ("adopted: class 42 ρ 0.31→0.44, n=260").

---

## 6. Flag + rollout

- `SIGNAL_CALIBRATION_ADAPTIVE` (bool, default `false`). When false, the job still runs and writes the table (shadow), but readers ignore it and use static weights.
- Observe `signal_calibration` rows + `[calibration]` logs for several cycles; flip on per-scope once ρ improvements are stable and sane.
- New cron registered in `expected_cron_jobs` (the daily `cron-inventory-watch` alerts on drift — required by repo convention).

---

## 7. Telemetry

- Per run: `classes_calibrated`, `classes_adopted` (cleared gate), mean `rho_holdout - rho_baseline`, global ρ trend.
- Alert if global ρ falls below 0.35 across cycles (rubric drifting from reality → corpus or extraction regression).

---

## 8. Testing

- **Unit (pure, deterministic):**
  - Weight sweep returns the argmax-ρ simplex point on a synthetic dataset with a known best.
  - Adopt guardrail: tuned weights rejected when `rho_holdout < rho_baseline + ε` or sample below floor (→ falls back to static).
  - Reader ladder: class → global → static fallback.
  - `spearman_rho` already exists; add ties/degenerate-input tests if missing.
- **Job test:** `run_signal_calibration` on a fixture corpus writes a row only when the gate is met.
- No live-Gemini test needed.

---

## 9. Acceptance criteria

1. A periodic job learns per-scope viral-score weights from corpus outcomes and writes `signal_calibration` with `rho_holdout`/`rho_baseline`/`sample_size`.
2. Tuned weights are **adopted only** when they beat static on a holdout and clear sample + ρ gates; otherwise static weights are used (verified by test).
3. With the flag off, behavior is byte-identical to today.
4. (Loop B) non-predictive signals can be salience-demoted from evidence, behind the flag.
5. (Loop C) synthesis confidence language scales with measured ρ + sample depth via existing claim tiers.
6. New cron registered in `expected_cron_jobs`; migration writes both MCP + local SQL (no drift); `pytest`/`ruff` clean.

---

## 10. Sequencing

This is the **shared dependency** the other two docs call out: it's what upgrades hook-effectiveness, comment grounding, and the structural retention curve from "more evidence in the prompt" to "a rubric that provably tracks reality." Recommend: ship Loop A right after the hook/comment grounding doc (it reuses the same `hook_effectiveness` + backtest plumbing), then B/C as the corpus deepens post-launch and sample floors are routinely met.
