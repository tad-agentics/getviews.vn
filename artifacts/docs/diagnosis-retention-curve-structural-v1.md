# Design — Content-aware retention curve (replace synthetic decay) (v1)

**Status:** Proposed (ready for implementation in Cursor)
**Owner:** —
**Surface:** Cloud Run Python — `video_structural.py` (curve model) + `video_analyze.py` (call sites) + existing prompt/UI consumers
**Related:** `system-design.md` §16, `corpus-ingest-criteria-v1.md`, calibration-loop recommendation
**Cost impact:** ~0 (deterministic compute over already-extracted signals; **no new Gemini/ED calls**)

---

## 1. Problem

The diagnosis already ships a retention curve end-to-end — data model, niche-benchmark overlay, a one-line prompt summary, the `retention_drop_pct_3s/10s` prompt fields, and the `Timeline` UI all consume it. **But the curve is content-blind.** `model_retention_curve()` (`video_structural.py:256`) is a synthetic smooth decay shaped by exactly three scalars — `duration`, `niche_median_retention`, `breakout_multiplier` (call sites `video_analyze.py:2173`, `:2786`). It does not read the video's actual structure, so:

- The "biggest drop" that `_summarise_retention_curve()` (`services/extraction.py:233`) feeds into the prompt is a math artifact of the decay shape, **not a real moment**. Synthesis can't say *where* attention breaks or *why*.
- `retention_source` is hardcoded `"modeled"` (`models.py:1414`) and the curve is effectively decoration.

"Where do viewers scroll away, and why" is the #1 question a top-tier analyst answers. We have the signals to *predict* it deterministically.

**Goal:** replace the synthetic shape with a **structure-driven attention-risk curve** that localizes drops at real moments (dead air, over-long static scenes, late hook payoff, redundancy), while staying **calibrated** to the niche's end-retention and honestly labeled as modeled (not measured telemetry).

---

## 2. Non-goals

- Not claiming real TikTok retention telemetry — EnsembleData doesn't expose it. This stays **modeled**; copy/UI must not present it as measured. (`retention_source` gains a value to distinguish.)
- No new extraction signals — v1 consumes existing `Scene[]` + transcript + `hook_timeline`.
- The niche **benchmark overlay** curve (`model_niche_benchmark_curve`) stays synthetic — it's the dashed comparison baseline, not the user's curve.

---

## 3. Current-state anchors (verified)

| Piece | Location |
|---|---|
| Synthetic curve model (to replace internals) | `video_structural.py:256 model_retention_curve(duration, niche_median_retention, breakout_multiplier, n_points)` |
| Niche benchmark overlay (keep) | `video_structural.py:288 model_niche_benchmark_curve(...)` |
| Live call sites | `video_analyze.py:2173`, `:2786` (both pass `niche_meta["avg_retention"]`, `breakout_multiplier`) |
| Curve → prompt summary | `services/extraction.py:233 _summarise_retention_curve()`, used at `:401`; `retention_drop_pct_3s/10s` at `:436-437`; injected in prompt template at `:481` |
| Curve data model + source label | `models.py:1408-1428` (`retention_curve`, `retention_user`, `retention_source: Literal["real","modeled"]`) |
| Scene signal available | `models.py:293-309` — `Scene{start,end,type,framing,pace,motion,overlay_style,subject,description}` |
| Hook payoff timing | `models.py:216-241` — `HookTimelineEvent` (0–3s notable moments), `hook_body_contract` |
| Transcript (for dead-air) | `user_analysis.audio_transcript` (+ `audio_track_role` to know if silence is expected) |

---

## 4. Design

### 4.1 New function: `model_retention_curve_from_structure(...)`

Add alongside the existing one (keep `model_retention_curve` as the **fallback** for carousels / scene-less extractions). Signature:

```python
def model_retention_curve_from_structure(
    duration_sec: float,
    scenes: list[dict],               # from user_analysis["scenes"]
    *,
    niche_median_retention: float | None,
    breakout_multiplier: float | None,
    transcript: str | None = None,
    hook_timeline: list[dict] | None = None,
    audio_track_role: str | None = None,
    n_points: int = 20,
) -> tuple[list[dict[str, float]], list[dict]]:   # (curve, risk_events)
```

Returns the curve **and** a small list of `risk_events` `[{t, severity, reason_vi}]` so synthesis/UI can name the moment, not just plot it.

**Model (deterministic, calibrated):**

1. **Anchor the budget.** Total expected drop = `100 - end_pct`, where `end_pct = clamp(100 * niche_median_retention, 5, 95)` and breakout flattens it slightly (reuse the existing `mid_lift = 1 + 0.08*log(boost)` idea). This keeps the curve calibrated to the cohort — same honesty property the current model has.

2. **Distribute drop by structural risk, not uniformly.** Compute a per-segment **risk weight** and allocate the drop budget proportionally, so dips land on real moments:
   - **Dead air:** transcript silence gaps > ~1.2s where `audio_track_role != "silent"` (i.e., silence that shouldn't be there) → high risk. (Approximate gaps from scene boundaries with no transcript tokens if word-timing unavailable; document the approximation.)
   - **Over-long static scene:** a scene with `pace == "slow"` or `motion in {static}` and `(end-start) >` genre norm → risk rises with excess duration.
   - **Late hook payoff:** if `hook_timeline`/`hook_body_contract` indicates the promise isn't paid until well after the opening window → front-load risk at the payoff gap.
   - **Redundancy:** consecutive scenes of the same `type`+`subject` (e.g., two near-identical talking-head beats) → mid-video lull risk.
   - **First-3s cliff:** always weight the 0–3s region (the FYP scroll-stop) using `face_appears_at` / `first_frame_type` — a weak opening keeps more of the budget at t≤3s.
3. **Smoothness:** convert per-segment risk into a monotonic-ish non-increasing curve (retention can't go up materially; allow tiny re-engagement only on a strong pattern-interrupt scene). Emit `n_points` samples as today so all consumers are unchanged.
4. **Risk events:** surface the top 1–3 highest-allocated drops as `risk_events` with a Vietnamese `reason_vi` ("khoảng lặng ~2s ở 0:06", "cảnh tĩnh dài 0:09–0:15").

Norm tables (genre/class scene-length + pace baselines) can start as small constants in `video_structural.py`; **§7 calibration** tunes them from corpus.

### 4.2 Wire-in

- `video_analyze.py:2173` / `:2786`: call the structural variant when `scenes` present and non-carousel; else fall back to `model_retention_curve` (unchanged). Pass `scenes`, `transcript`, `hook_timeline`, `audio_track_role` from `user_analysis`.
- Set `retention_source = "modeled_structural"` (extend the Literal in `models.py:1414` to `["real","modeled","modeled_structural"]`) so UI/copy can distinguish a structure-driven model from the flat fallback.
- `_summarise_retention_curve()` improvements (`services/extraction.py:233`): when `risk_events` available, summarize the **named** biggest drop ("drop lớn nhất ~0:06: khoảng lặng trước câu chốt") instead of a generic percentage. This is the line that lands in the prompt → diagnosis instantly gets specific.

### 4.3 Synthesis use

In `diagnose_prompts.py`, the structure/`script_structure` section guidance should instruct: *"Nếu có điểm tụt giữ chân (retention drop), nêu đúng mốc thời gian + nguyên nhân cấu trúc + cách sửa khi quay lại"* — turning the curve into a reshootable fix ("cắt 1.5s khoảng lặng trước 0:06"). No new section; enrich the existing structure block.

---

## 5. Honesty / copy rules

- Label remains **modeled** — never present as measured TikTok retention. If surfaced in FE copy, use phrasing like "dự đoán giữ chân theo cấu trúc" (predicted), not "tỉ lệ giữ chân thực tế". JetBrains Mono for numbers.
- Obey `.cursor/rules/copy-rules.mdc` (no forbidden openers/words). House formula: state the drop (data) → name the structural cause (finding) → give the reshoot fix.

---

## 6. Flag + rollout

- `DIAGNOSIS_RETENTION_STRUCTURAL` (bool, default `false`) in `settings.py`. Off → current synthetic curve (no behavior change).
- **Shadow first:** when off, compute both curves and log `[retention_shadow]` with the structural `risk_events` + the delta vs synthetic for 5–10 sessions; eyeball that drops land on plausible moments before flipping on.
- Rollback = flip flag; no migration.

---

## 7. Calibration (ties to the calibration-loop recommendation)

Validate, don't just ship: extend `viral_alignment_backtest.py` to check whether videos whose structural curve predicts an **early/severe** drop actually under-retain/under-break-out in the corpus (proxy: `breakout_multiplier`, `save_rate`/`completion`). Use the result to tune the risk-weight constants per content_class. This is what makes the curve *intelligence* rather than a prettier heuristic — and it's the same loop the hook-effectiveness doc calls out as currently open.

---

## 8. Testing

- **Unit (pure, deterministic):**
  - Dead-air segment → localized dip at that t (assert `risk_events` contains it).
  - Over-long static scene → dip allocated to that window; fast-cut video → flatter mid-curve.
  - End-retention still anchored to `niche_median_retention` (sum-of-drops ≈ budget) — guards calibration.
  - No scenes / carousel → falls back to synthetic `model_retention_curve` (identical output).
  - Monotonic-ish: no point materially exceeds a prior point except sanctioned pattern-interrupt.
- **Summary test:** `_summarise_retention_curve` emits the named biggest-drop line when `risk_events` present.
- No live-Gemini test needed.

---

## 9. Acceptance criteria

1. With structured scenes, the user's retention curve's biggest drop coincides with a real structural risk (dead air / over-long static / late payoff), exposed as a `risk_event` with a VN reason.
2. End-retention stays calibrated to the niche median (curve isn't free to invent optimism/pessimism).
3. Carousels / scene-less rows are unchanged (synthetic fallback).
4. The diagnosis structure section cites the timestamped drop + a reshoot fix.
5. Gated by `DIAGNOSIS_RETENTION_STRUCTURAL`; shadow logs present; zero new Gemini/ED calls; `retention_source="modeled_structural"` set.
6. `pytest`/`ruff` clean; copy passes forbidden-word lint; UI never labels it as measured retention.

---

## 10. Sequencing vs the hook/comment doc

Independent of `diagnosis-grounding-hook-effectiveness-comments-v1.md`; can ship in either order. Together they convert the three "almost-there" pillars (measured hook lift, audience comments, retention) from plumbing/decoration into the substance of a top-tier diagnosis. The shared dependency both lean on for full value is the **calibration loop** (§7) — worth scheduling next.
