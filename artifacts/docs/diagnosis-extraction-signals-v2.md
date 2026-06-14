# Design — Missing extraction signals (info-density · loop-ability · hook forensics · audio dynamics) (v1)

**Status:** Proposed (ready for implementation in Cursor)
**Owner:** —
**Surface:** Cloud Run Python — extraction (`models.py` schema, `prompts.py` extraction prompt, `gemini.py analyze_video`) + deterministic post-processing (`video_structural.py`) + ASR (`services/asr_vietnamese.py`)
**Related:** `diagnosis-retention-curve-structural-v1.md` (consumes these), `diagnosis-calibration-loop-v1.md` (validates these), `corpus-ingest-criteria-v1.md`
**Cost note:** **This is the one priority that adds cost** — but it tiers cleanly from ~0 to "optional add-on." Do Tier 1 first.

---

## 1. Problem

The extraction layer is rich (`Scene{type,framing,pace,motion,overlay_style,subject}`, `HookTimelineEvent`, `audio_track_role`, `sound_layering`) — but four signals a top-tier analyst relies on are missing, and they're exactly the ones that make advice *behavioral* rather than descriptive:

- **#8 Information density / second** — only categorical `PaceType` exists; no words/sec or new-info/sec. Superstars front-load value; we can't measure whether they do.
- **#12 Loop-ability & share/save triggers** — no detection of seamless end→start loops (rewatch driver), "tag a friend"/save-worthy reference value (share/save drivers). These move the algorithm.
- **#5 Sub-second hook forensics** — `HookTimelineEvent` exists but lacks the quantified layer: opening-frame visual energy, **text-on-screen vs first-spoken-word timing**, pattern-interrupt.
- **#6 Audio dynamics** — `audio_track_role`/`sound_layering` exist, but no beat↔cut sync or voice-energy/prosody arc. TikTok is audio-first.

**Goal:** add these signals so the diagnosis can say "you deliver your first claim at 0:06 — top performers front-load by 0:02," "your cuts ignore the beat," "the end doesn't loop." Tier the work so most of the value lands at ~0 cost.

---

## 2. Two unlocks that make this cheap (verified)

1. **ffmpeg is already available** — `asr_vietnamese.py:51 _extract_wav_16k_mono()` + `:26 _ffprobe_duration_sec()` shell out to ffmpeg/ffprobe. Audio extraction needs no new system dep.
2. **ASR already returns word-level timestamps** — `asr_vietnamese.py:164-171` parses `words[].start_time/end_time` (GCP STT, vi-VN, **video paths only**; carousels skip STT). This single fact unlocks info-density, dead-air gaps, and text-vs-speech timing **without any DSP library**.

The clip is downloaded locally during extraction (`services/extraction.py:558 video_path: Path`), so Tier-3 audio DSP is feasible too — but it needs a new numpy/librosa dependency + CPU, so it's staged last.

---

## 3. Design — three tiers by cost/confidence

### Tier 1 — Deterministic, ~0 cost, no new deps (DO FIRST)

Compute in `video_structural.py` from data already extracted (scenes + ASR word timing). No new Gemini/ED calls. These also directly feed the **structural retention curve** (`diagnosis-retention-curve-structural-v1.md` §4.1) — same inputs, so build them together.

- **Information density** (`compute_information_density(scenes, asr_words, duration) -> dict`):
  - `words_per_sec` overall + a per-third arc (front/mid/back) from ASR word timestamps (fallback: `len(transcript.split())/duration` when word timing absent).
  - `time_to_first_value_sec` — first content-bearing word after the hook window (proxy for front-loading); the headline number.
  - `dead_air_ratio` — Σ silence gaps >1.2s where `audio_track_role != "silent"`, ÷ duration.
- **Loop-ability** (`compute_loopability(scenes, caption, audio_track_role) -> dict`):
  - `loop_score` from first-scene vs last-scene similarity (`type`+`subject`+`framing` match) + whether the closing line echoes the hook (caption/transcript) + continuous `audio_track_role`.
  - `redundancy_runs` — count of consecutive same-`type`+`subject` scenes (mid-video lull driver).

Persist as **optional** columns / nested dict on the analysis JSON (mirror the existing Optional-Scene-enrichment pattern in `models.py:293-309` so old corpus rows still validate). Surface in the structure section + retention curve.

### Tier 2 — Gemini-extracted, ~0 extra API cost (schema + prompt only)

Add **optional** fields to the existing extraction schema (`models.py` `HookAnalysis`/`VideoAnalysis`) and a few lines to `VIDEO_EXTRACTION_PROMPT` (`prompts.py:259`). Same `analyze_video` call — only output tokens grow slightly; rides the HI-13 batch discount nightly. All Optional → backward compatible.

- **Hook forensics:** `opening_visual_energy: Literal["high","medium","low"] | None`, `text_speech_sync: Literal["simultaneous","text_first","speech_first","none"] | None` (does the on-screen text land with the first spoken word?), `pattern_interrupt: bool | None` (abrupt visual/audio break that re-captures attention).
- **Share/save triggers:** `share_trigger: Literal["tag_prompt","relatable","controversy","none"] | None` ("tag bạn bè"/"gửi cho…"), `save_worthiness: Literal["reference","tutorial_step","none"] | None`.

Prompt must keep these **descriptive and conservative** (the model marks `none`/null when unsure — don't manufacture signals), consistent with the existing extraction discipline.

### Tier 3 — Audio DSP, NEW dependency + CPU, optional / batch-only (LAST)

Needs numpy + a light onset/beat library (or hand-rolled RMS + onset via numpy on the ffmpeg-extracted wav). Adds Cloud Run CPU time, so **batch-only + flag-gated**; never on the live latency path.

- **Beat↔cut sync** (`compute_beat_sync(wav_path, scenes) -> {cut_on_beat_ratio, tempo_bpm}`): detect beats, measure what fraction of scene-cut timestamps fall near a beat.
- **Voice-energy arc** (`compute_voice_energy(wav_path) -> {energy_arc, low_energy_spans}`): RMS energy over time → flag monotone/low-energy spans (retention risk; feeds the curve).

Gate behind `EXTRACTION_AUDIO_DSP` (default false). Justify with calibration (§5) before broad enablement — this is the only tier where payoff is uncertain.

---

## 4. Schema / migration

- Tier 1 + Tier 3 outputs: store on the analysis JSON (nested dicts) and/or new **nullable** `video_corpus` columns if they need to be queryable for benchmarks (e.g. `time_to_first_value_sec`, `loop_score`, `cut_on_beat_ratio`). Follow the destructive-migration / dual-write (MCP + local SQL) rules; all additive + nullable so no backfill blocks ship.
- Tier 2: Optional Pydantic fields only — no migration unless columns are wanted for cohort stats later.

---

## 5. Validation via the calibration loop (don't add signals blindly)

Adding signals without checking they predict outcomes is how reports bloat. Once `diagnosis-calibration-loop-v1.md` Loop B exists, each new signal gets a `signal_predictive_rho` vs `breakout_multiplier`. **Promote a signal into the diagnosis only after it shows non-trivial predictive correlation** on a healthy sample; otherwise keep it shadow/telemetry. This is the guardrail that keeps "more signals" from becoming "noisier reports."

---

## 6. Flag + rollout

- `EXTRACTION_SIGNALS_V2` (bool) gates Tier 1 + Tier 2 emission into the diagnosis (compute always, surface when on — shadow-first).
- `EXTRACTION_AUDIO_DSP` (bool, default false) gates Tier 3 entirely.
- Backfill Tier 1/2 lazily on the live diagnosis path; corpus gets them on the next nightly extraction (no mass re-extract — old rows simply lack the fields, which all consumers must treat as Optional).

---

## 7. Copy rules

New diagnosis lines Vietnamese, JetBrains Mono for numbers (`words_per_sec`, `time_to_first_value`), `.cursor/rules/copy-rules.mdc` compliant, house formula (data → finding → fix), e.g. "giá trị đầu tiên xuất hiện ở 0:06 — top ngách mở giá trị trước 0:02; dồn câu chốt lên sớm."

---

## 8. Testing

- **Tier 1 (pure, deterministic):** density arc from synthetic ASR words; `time_to_first_value` ignores hook filler; dead-air ratio excludes legit `silent` tracks; loop_score high when first≈last scene + hook echo; redundancy run counting. Fallback path when ASR word timing absent.
- **Tier 2:** schema accepts the new Optional fields and old JSON (without them) still validates (`model_validate` round-trip).
- **Tier 3:** beat-sync ratio on a click-track fixture with known cuts; energy arc flags an injected silent span. Keep DSP behind the flag in CI.
- No live-Gemini test needed for Tier 1; Tier 2 is schema-level.

---

## 9. Acceptance criteria

1. Tier 1 signals computed deterministically from existing scenes + ASR word timing, no new API calls, feeding both the structure section and the retention curve.
2. Tier 2 fields extracted in the same `analyze_video` call, all Optional, old corpus rows still validate.
3. Tier 3 is batch-only + flag-off by default; adds no live latency.
4. New signals are surfaced in the diagnosis **only** after passing the calibration predictive-ρ check (or explicitly shadow until then).
5. Additive nullable migration (dual-write), `pytest`/`ruff` clean, copy lint clean.

---

## 10. Sequencing (relative to the other three docs)

- **Tier 1 pairs with the retention-curve doc** — same inputs, build once.
- **Tier 2** is a cheap follow-on (schema + prompt).
- **Tier 3** waits until the calibration loop can prove beat-sync/voice-energy actually predict outcomes — it's the only piece with real added cost and uncertain payoff.
- Net ordering across all four priorities: (1) hook/comment grounding → (2) structural retention curve **+ Tier 1 signals** → (3) calibration loop → (4) Tier 2 then, if validated, Tier 3.
