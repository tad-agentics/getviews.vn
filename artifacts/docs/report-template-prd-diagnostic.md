# Template PRD — `diagnostic`

**Owner:** unassigned · **Status:** spec'd, not implemented · **Created:** 2026-04-22

## Purpose

Serve exactly one intent: `own_flop_no_url` — "my last video flopped and I don't have the link / don't want to paste it."

Today this intent routes to `answer:pattern`, which returns a niche hook leaderboard. The user is asking for diagnosis, not trend analysis. The reply looks off-topic, and we see session abandonment on this branch.

## What the page shows

Reference design: Claude Chat "Report 4: VIDEO DIAGNOSIS" — but **scoped down**. The reference is designed for a specific analysed video (5-part score per video, bar per section). Here we don't have a video row; we only have the user's self-described symptoms plus niche benchmarks.

Required sections, in order:

1. **Confidence strip** — `ConfidenceStrip` primitive. Confidence is always ≤ `"medium"` here because we don't have the video itself.
2. **Framing sentence** — plain-language acknowledgement: "Chưa có link video, mình chẩn đoán dựa trên mô tả + benchmark ngách."
3. **Failure-mode checklist** — 5 fixed categories (Hook, Pacing, CTA, Sound, Caption+Hashtag), each with a confidence-weighted verdict: `likely_issue`, `possible_issue`, `unclear`, or `probably_fine`. No numeric score (we don't have enough signal to score honestly).
4. **Targeted prescriptions** — 2–3 concrete fixes, ordered by likely impact. Each has a 1-line action + expected impact range + effort estimate.
5. **"Paste the link for exact diagnosis" CTA** — bold upsell back to `/app/video` which *can* score properly.
6. **Related questions** — existing shape, query-aware.

The explicit "likely / possible / unclear / probably_fine" gradient avoids the honesty problem where we'd otherwise ship fake 5-part scores for a video we've never seen.

## Data contract

New Pydantic model in `cloud-run/getviews_pipeline/report_types.py`:

```python
DiagnosticVerdict = Literal["likely_issue", "possible_issue", "unclear", "probably_fine"]

class DiagnosticCategory(BaseModel):
    name: str                                     # "Hook (0–3s)" / "Pacing (3–20s)" / "CTA" / "Sound" / "Caption & Hashtag"
    verdict: DiagnosticVerdict
    finding: str = Field(max_length=280)          # Why we think this; quotes the user's description where possible
    fix_preview: str | None = Field(default=None, max_length=240)  # Present only when verdict != probably_fine

class DiagnosticPrescription(BaseModel):
    priority: Literal["P1", "P2", "P3"]
    action: str = Field(max_length=160)
    impact: str = Field(max_length=160)           # "Dự báo: +12–18 điểm retention"
    effort: Literal["low", "medium", "high"]      # Shown as "15 phút" / "30 phút" / "1 giờ" on the client

class DiagnosticPayload(BaseModel):
    confidence: ConfidenceStrip
    framing: str = Field(max_length=240)          # 1 sentence — acknowledges the URL-less constraint
    categories: list[DiagnosticCategory] = Field(min_length=5, max_length=5)  # fixed 5
    prescriptions: list[DiagnosticPrescription] = Field(min_length=1, max_length=3)
    paste_link_cta: dict = Field(default_factory=lambda: {
        "title": "Có link video? Mở /app/video để chẩn đoán chính xác",
        "route": "/app/video",
    })
    sources: list[SourceRow]                      # Niche benchmarks we reasoned against
    related_questions: list[str]
```

Note the `DiagnosticCategory.verdict` enum replaces numeric scoring. The reference design's `score: int` is retired for this template because we don't have grounding.

Add `"diagnostic"` to:
- `ReportV1.kind` Literal union
- `validate_and_store_report` dispatch
- `answer_sessions.format` CHECK constraint (coordinate with lifecycle migration)
- `AnswerSessionFormat` in `src/routes/_app/intent-router.ts`
- `select_builder_for_turn` return set
- `INTENT_DESTINATIONS["own_flop_no_url"] = "answer:diagnostic"`

## Backend builder

New module `cloud-run/getviews_pipeline/report_diagnostic.py`:

```python
def build_diagnostic_report(
    niche_id: int,
    query: str,
    window_days: int = 14,
) -> dict[str, Any]:
    """Live URL-less flop diagnostic. Gemini-heavy because the whole point is
    interpreting the user's description against niche benchmarks."""
```

Flow:
1. Load niche benchmarks (avg hook retention, median pacing tps, top sounds, common CTA types) — mostly reads from `niche_intelligence` + `hook_effectiveness`.
2. Call Gemini with the 5 fixed category labels + user's `query` + the benchmark context. Gemini outputs per-category `verdict` + `finding` + `fix_preview`, plus 2–3 ranked prescriptions.
3. Validate against `DiagnosticPayload`. Fallback: when Gemini fails or budget exhausted, produce a deterministic payload where all 5 categories are `verdict: "unclear"` and prescriptions say "Paste video link for specific diagnosis" — preserves the UX shape without pretending to diagnose.

**Key invariant** (regression-test it): when `query` is empty or near-empty (< 20 chars), the builder still produces a valid payload where all categories are `unclear`, and the prescription section collapses to just the paste-link CTA. We shouldn't invent issues to fill the template.

## Gemini narrative

New module `cloud-run/getviews_pipeline/report_diagnostic_gemini.py`:

- `fill_diagnostic_categories(query, niche_label, benchmarks)` → `{framing, categories, prescriptions}`.
- Prompt must:
  - Quote phrases from the user's query back into each `finding` that references them ("bạn nói 'không ai xem hết video' — khả năng cao pacing chậm so với ngách").
  - Use the 4-level verdict vocabulary, NOT numeric scores.
  - Cite niche benchmarks (e.g. "ngách Skincare: avg retention 68% · median tps 1.4").
  - Never output `probably_fine` for a category without query evidence — default to `unclear`.

Regression test: two different queries → two different `framing` strings AND at least one different category verdict.

## Frontend

New directory `src/components/v2/answer/diagnostic/`:
- `DiagnosticBody.tsx` — top-level component.
- `VerdictBadge.tsx` — 4 variants with distinct token colours:
  - `likely_issue` → `--gv-accent` / `--gv-accent-soft` (red, urgent)
  - `possible_issue` → warning amber (use `--gv-accent-2-soft` or equivalent warm token)
  - `unclear` → neutral grey (`--gv-ink-4` / `--gv-canvas-2`)
  - `probably_fine` → `--gv-pos` / `--gv-pos-soft` (blue, safe)
- `PrescriptionCard.tsx` — priority tag + action line + impact chip + effort chip.
- `PasteLinkCTA.tsx` — brutalist card pointing to `/app/video`.

Reuse:
- `ConfidenceStrip` (existing)
- `ActionCards` primitive (not used here — the paste-link CTA is the only action; we don't need the 3-card grid)
- `RelatedQs` (existing)

Add case to `ContinuationTurn.tsx` switch. Add `"diagnostic"` to `ANSWER_ERROR_CODES`.

**Do not** port the reference design's `ScoreRing` or per-section numeric score. That accuracy is not honest for URL-less diagnosis.

## Copy rules (Vietnamese)

- Framing sentence must explicitly say we don't have the video link: "Chưa có link video — mình chẩn đoán dựa trên mô tả và benchmark ngách."
- Verdict labels: `likely_issue → "Nhiều khả năng lỗi"`, `possible_issue → "Có thể có lỗi"`, `unclear → "Chưa đủ thông tin"`, `probably_fine → "Có vẻ ổn"`.
- Forbidden copy from the existing rules still applies ("bí mật", "công thức vàng", "triệu view", "bùng nổ", "Chào bạn", "Tuyệt vời").
- The paste-link CTA copy: `"Có link video? Mở /app/video để chấm điểm chính xác từng phần."` — deliberately positions `/app/video` as the high-precision alternative, not a duplicate.

## Tests

Backend (`cloud-run/tests/test_report_diagnostic.py`):
- `test_payload_validates_with_all_verdict_types` — each of the 4 verdicts round-trips cleanly.
- `test_empty_query_returns_all_unclear` — the honesty invariant.
- `test_gemini_failure_returns_unclear_categories` — deterministic fallback.
- `test_two_different_queries_produce_different_framings` — query threading (same lesson as batch-3).

Frontend (`src/components/v2/answer/diagnostic/DiagnosticBody.test.tsx`):
- Verdict badge colour per enum value.
- Prescriptions section hidden when empty (all-unclear case).
- Paste-link CTA always renders.

Dispatcher (`cloud-run/tests/test_answer_turn_builder_dispatch.py`, extend):
- `own_flop_no_url` → routes to `diagnostic` on primary and follow-up turns.

## Migration

Combined with the lifecycle template — one CHECK constraint alter to add both literals:

```sql
-- 2026-05-XX_add_lifecycle_and_diagnostic_formats.sql
ALTER TABLE answer_sessions
  DROP CONSTRAINT IF EXISTS answer_sessions_format_check;
ALTER TABLE answer_sessions
  ADD CONSTRAINT answer_sessions_format_check
  CHECK (format IN ('pattern', 'ideas', 'timing', 'generic', 'lifecycle', 'diagnostic'));
```

## Acceptance

- Lands as one PR (can stack on lifecycle PR or ship after).
- CI green: pytest + vitest + typecheck + token-lint.
- `own_flop_no_url` routes to `diagnostic` via `INTENT_DESTINATIONS`.
- Manual smoke: a session with "video tuần trước flop mà mình không còn link, pacing chậm, CTA yếu" renders 5 categories with verdicts that reference "pacing chậm" and "CTA yếu" specifically, plus a visible paste-link CTA.

## Out of scope for v1

- Any image/frame analysis (we have no input media).
- Direct backlink to the user's most recent `/app/video` analysis (v2 — could auto-suggest "is it this one?" from history).
- Per-prescription A/B test tracking (v2 — when we wire prescriptions to a feedback loop).
