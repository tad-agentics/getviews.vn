# `cta_type` + `face_appears_at` silent-skip audit

**Date:** 2026-05-10
**Scope:** Wave 1 PR #3 of the revised implementation plan.
**Purpose:** resolve the state-of-corpus Axis 2 "21% / 70% gap" flags so Wave 2 doesn't build on false expectations.

---

## TL;DR

- **`face_appears_at` 21% null is NOT a bug** — correct data absence. Pipeline faithfully null-tracks what Gemini emits, and Gemini correctly withholds the field when no face appears in the hook window.
- **`cta_type` 70% null is mostly correct** — most video transcripts genuinely lack explicit CTAs. Sampled 15 null-cta rows; narrative uses of CTA-adjacent words dominate.
- **`cta_type` 59% of populated → 'other'** IS a real classifier-coverage gap. Regex expanded 2026-05-10 to catch VN shop-pressure + try-it + DM + external-channel patterns seen in live samples.

---

## `face_appears_at` — pipeline is correct

Live-DB cross-tab of null-rate by `first_frame_type` (n=1,548):

| first_frame_type | total | null | populated | % populated |
|---|---|---|---|---|
| `face_with_text` | 573 | 2 | 571 | **99.7%** |
| `face` | 316 | 0 | 316 | **100%** |
| `action` | 213 | 54 | 159 | 75% |
| `other` | 182 | 117 | 65 | 36% |
| `product` | 146 | 69 | 77 | 53% |
| `text_only` | 67 | 39 | 28 | 42% |
| `screen_recording` | 51 | 43 | 8 | **16%** |

Nulls cluster exactly where face is genuinely unlikely (screen_recording 16%, text_only 42%, product 53%, other 36%). Face-forward frame types sit at 99.7%–100% populated. Zero rows tagged `first_frame_type='face_to_camera'` with a null timestamp.

**Conclusion:** the 21% headline number is misleading — the pipeline is accurate. No fix needed.

---

## `cta_type` — three distinct buckets to the 70%+30% shape

### 1. 70% null (1,091 of 1,548 rows)

- `analysis_json->>'cta'` IS NULL AND `cta_type` IS NULL.
- Sampled 15 null-cta rows with CTA-adjacent vocabulary in the transcript (via regex: `lưu lại|theo dõi|follow|comment|...`). Read each manually.
- **~13 of 15 are narrative uses**, not CTAs: "đã chia sẻ MacBook bị bạc màu" (news narrative), "theo dõi lại đường chuyền" (match commentary), "chia sẻ với các bạn cái nước sốt" (content phrasing), "3 người đăng ký tham dự" (describing past event), etc.
- **~2 of 15 could plausibly be CTAs Gemini missed** — not a widespread extractor bug.

**Conclusion:** 70% null is mostly real. News, commentary, dance, faceless, and story-format videos genuinely don't prompt the viewer to act. The 15-bucket `content_format` taxonomy lock (see `classify_format` docstring) already acknowledges this content class exists.

### 2. Of the 30% with a `cta` field, 59% bucket to `other`

Sampled 20 random `cta_type='other'` rows; ~14 of 20 could route to an **existing** taxonomy bucket if the regex covered them:

| Intended bucket | Live sample CTA phrase missed by old regex |
|---|---|
| `shop_cart` | "tranh thủ đợt flash sale này mà **chốt ngay** combo" |
| `shop_cart` | "mỗi vợ **chốt nhẹ** một hai set" |
| `shop_cart` | "Chốt đi" |
| `shop_cart` | "Mọi người tranh thủ **săn deal** nhé" |
| `try_it` | "Các tình yêu có thể thử **tham khảo** em này nhé" |
| `try_it` | "Hãy lên kênh YT của Hoàng Tốc Độ xem nha" (also `follow`) |
| `try_it` | "Nhanh chân **ghé** hỷ" |
| `try_it` | "Thử **áp dụng** đi" |
| `try_it` | "**Làm liền** bây giờ nha mọi người" |
| `follow` | "Hãy **lên kênh** YT của Hoàng Tốc Độ xem nha" |
| `comment` | "**inbox** để mình tư vấn cho nhé" |
| `comment` | "ai cần thì **nhắn mình** nha" |
| `part2` | "**Video sau** tôi sẽ chia sẻ 20 mindset cực đỉnh" |

The remaining ~6 of 20 were genuinely out-of-taxonomy (Chinese-language CTAs, "hãy gọi cho Phương" phone-call CTAs, external DM requests with no matching bucket).

### 3. Regex expanded — 2026-05-10

`_classify_cta` in `cloud-run/getviews_pipeline/corpus_ingest.py` now covers:

- **shop_cart:** + `chốt ngay|chốt đi|chốt nhẹ|chốt luôn|săn deal|săn sale|săn hàng`
- **try_it:** + `áp dụng|tham khảo|làm liền|ghé|thử áp dụng|nên xem`
- **follow:** + `lên kênh|kênh yt|channel`
- **comment:** + `inbox|nhắn mình|nhắn tin|dm mình`
- **part2:** + `video sau|clip sau|kỳ sau|phần tiếp`

Regression tests in `cloud-run/tests/test_classify_cta.py` pin every new pattern with a live-corpus example.

**Expected impact:** ~70% of currently-'other' cta_type rows (i.e. ~188 of ~269) should now route to a specific bucket on **future ingests**. Existing rows keep their current classification until a targeted reclass runs (out of scope for this PR — can be a future admin trigger mirroring `/batch/reclassify-format`).

---

## What changed in code

| File | Change |
|---|---|
| `cloud-run/getviews_pipeline/corpus_ingest.py` | `_classify_cta` regex expanded (5 buckets) |
| `cloud-run/tests/test_classify_cta.py` | 16 new regression tests, every new pattern pinned |
| `artifacts/docs/cta-face-detect-audit.md` | this doc |

No schema changes, no migration, no Gemini prompt changes. Pure regex expansion.

---

## What did NOT change (and why)

- **`face_appears_at` extraction prompt** — pipeline is already correct, no gap.
- **`cta_type` extraction prompt** — 70% null is mostly accurate content absence, not an extractor miss.
- **cta_type reclass of existing 'other' rows** — out of audit scope. A future admin trigger mirroring `/batch/reclassify-format` can bring old rows forward once the regex settles.
- **Taxonomy expansion** (e.g. adding `phone_call`, `external_link`, `language_other` buckets) — classifier docstring enumerates the 7 canonical buckets; expansion requires same atomic 7-layer refactor as the `content_format` taxonomy lock.

---

## Related

- State-of-corpus Axis 2 (`artifacts/docs/state-of-corpus.md`): section on cta_type + face_appears_at was the prompt for this audit.
- Implementation plan Wave 1 (`artifacts/docs/implementation-plan.md`): this PR closes the `cta-face-detect-silent-skip-audit` scope item.
