# Diagnosis rollout — shadow validation & flag-flip runbook (v1)

**Status:** Operational runbook
**Scope:** Taking docs #1–#5 + corpus follow-ups from *built & shadow-logging* to *live*. All features are flag-gated **OFF**; the user-facing report is unchanged until these flags flip. This is the bridge between "reviewed" and "shipped."
**Principle:** enable ONE flag, observe ~3–5 live diagnoses (+ the shadow logs), check the kill criteria, then proceed. Never flip two at once — you lose attribution.

---

## 0. Pre-flight — measure coverage first (thin pre-launch corpus)

Most of these features only fire when the corpus is deep enough (claim-tier floors). On a thin corpus they may be empty most of the time — that's expected, but **measure it before flipping** so you know whether a flag will actually do anything. Parse the shadow logs (Cloud Logging) over the last N diagnoses for:

| Signal | Log line | Field to count |
|---|---|---|
| Grounding coverage | `[diagnosis_grounding]` (`diagnosis_grounding.py:198`) | `hook_emitted=true` rate, mean `hook_buckets`, `comment_emitted=true` rate |
| Retention shadow | `[retention_shadow]` (`video_analyze.py:298`) | `struct_end` vs `syn_end` delta, `risk_count` distribution |
| Extraction signals | `[extraction_signals_shadow]` (`video_analyze.py:269`) | non-null `ttfv` / `loop` / `dead_air` rate |
| Calibration | `signal_calibration` table | rows with `adopted=true`, `rho_holdout - rho_baseline` |

If a flag's coverage is ~0% (e.g. no hook bucket ever clears the floor), flipping it is harmless but pointless — prioritize the FE flags and retention first, revisit grounding/calibration as the corpus grows.

---

## 1. Flip order (lowest-risk first)

Each row: flip → observe → check kill criteria → proceed. Env var = the name shown.

### Step 1 — `VITE_REPORT_PRESENTATION_V2` (FE only, near-zero risk)
- **Does:** mounts the retention chart, hook-timeline strip, `bright_spot` lead chip, cross-format strip, comment next-step bullet, "xem thêm" expanders; relocates script-structure prose to the block closing (A1b).
- **Watch:** the report visually — do the retention chart + hook strip render with data; does the lead chip ever duplicate the headline.
- **Healthy:** charts render when curve data present, hide cleanly when absent; lead chip distinct from headline.
- **Kill if:** charts render empty/garbled, lead chip echoes the headline (dedup guard should prevent this — if it doesn't, that's a bug), or layout breaks on mobile (360–393px).

### Step 2 — `DIAGNOSIS_RETENTION_STRUCTURAL`
- **Does:** replaces the synthetic retention curve with the structure-driven one (dead-air / static / late-hook risk), emits `risk_events`.
- **Watch:** `[retention_shadow]` — `struct_end` should track the niche median (close to `syn_end`); `risk_count ≥ 1`; spot-check that the biggest drop lands on a real moment.
- **Healthy:** end-retention anchored to niche median; drops coincide with plausible structural moments.
- **Kill if:** `struct_end` drifts materially from the niche median (anchor broken), or risk events land on nonsense timestamps.

### Step 3 — `DIAGNOSIS_HOOK_LEADERBOARD` + `DIAGNOSIS_COMMENT_GROUNDING`
- **Does:** injects the measured hook-lift leaderboard + comment-signal block into the prompt.
- **Watch:** `[diagnosis_grounding]` — `hook_emitted` / `comment_emitted`, `hook_buckets`. Spot-check the rendered rank/multiplier against the `hook_effectiveness` table.
- **Healthy:** ranks/multipliers only appear when buckets clear the floor (class total ≥50, per-bucket ≥5); comment block only at `sampled ≥ 8` + vi/mixed.
- **Kill if:** a rank/multiplier appears on a sub-floor bucket, or any number can't be traced to the table (fabrication — should be impossible by gating).

### Step 4 — `DIAGNOSIS_VOICE_LINT_RUNTIME`
- **Does:** runs the word-boundary forbidden-word scrub on synthesized `*_vi` fields.
- **Watch:** the `soft-scrubbed N forbidden copy hit(s)` log.
- **Healthy:** low hit-rate; scrubbed sentences still read naturally.
- **Kill if:** scrubs mangle legitimate words (boundary bug — "hack" inside "hackathon") or hit-rate is high (means the prompt itself is leaking — fix upstream, not by scrubbing).

### Step 5 — `DIAGNOSIS_WIDE_CONTEXT`
- **Does:** feeds the model wider raw context (full scenes/timeline + retention/benchmark curves) instead of the trimmed digest.
- **Watch:** output length + focus before/after.
- **Kill if:** reports bloat or lose focus (small-model dilution — the tradeoff we flagged).

### Step 6 — `DIAGNOSIS_LEAD_LEVER`
- **Does:** asks the model to emit a single `lead_finding`; FE elevates it.
- **Kill if:** the lead finding just restates the headline or isn't the actual biggest lever.

### Step 7 — `DIAGNOSIS_PROPOSED_FINDINGS`
- **Does:** allows LLM-proposed findings beyond fired signals (labeled `confidence_tier:"proposed"`).
- **Watch:** count of proposed vs signal-backed findings; **every proposed finding must cite a number/timestamp.**
- **Kill if:** any proposed finding is ungrounded (no cited evidence) — that's the hallucination risk this whole guardrail exists to prevent.

### Step 8 — `SIGNAL_CALIBRATION_ADAPTIVE` (LAST, deepest change)
- **Pre-req:** `run_signal_calibration` has written `signal_calibration` rows with `adopted=true` (otherwise the reader falls back to static weights and nothing changes).
- **Does:** viral-score weights + signal salience read from the calibrated table; synthesis confidence priors.
- **Watch:** `classes_adopted`, mean `rho_holdout - rho_baseline` (> 0), global ρ.
- **Kill if:** global ρ drops below 0.35 (rubric drifting from reality) — set the flag back off; static weights resume.

### Related (enable with its owners, not in this sequence)
- `EXTRACTION_SIGNALS_V2` (surfaces Tier 1/2 signals into the digest) — flip after shadow confirms the signals look sane; ideally after Loop B can predictive-ρ-gate them.
- `DIAGNOSIS_SALIENCE_RANK_ONLY` (demote salience from emit-gate to ranking) — pairs with calibration; enable after Step 8 is stable.

---

## 2. Rollback
Every flag is independently reversible — set it back to `false`/unset and behavior reverts to the prior step with no migration. There is no data migration to undo; the shadow tables (`signal_calibration` etc.) are append-only and harmless when the reader ignores them.

## 3. Definition of "shipped"
A flag graduates from shadow to shipped when: coverage is non-trivial on the live corpus, the kill criteria held across the observation window, and (for grounding/calibration) the numbers are traceable to source. Record the flip date + observed coverage in `changelog.md` per flag.

## 4. Open items gating full value (track separately)
- **Peer-reference timestamps** (B2) — not yet wired; until then peer contrast in the prompt stays non-time-anchored even with presentation V2 on.
- **Extraction-signal calibration gating** — new signals surface unconditionally when `EXTRACTION_SIGNALS_V2` is on; tighten via Loop B once it registers predictive-ρ for them.
