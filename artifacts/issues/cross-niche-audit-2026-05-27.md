# Cross-niche audit — ingest 27/05/2026 ICT

**Scope:** 60 videos from nightly ingest (03:00–07:30 ICT) where HI-11 route changed **creator_niche** (planned loop class primary niche ≠ final class primary niche).

| Metric | Count |
|--------|------:|
| Total | 60 |
| gemini_two_axis | 55 |
| hashtag fallback | 5 |
| Pet cute → lifestyle final | 9 |

**Files:** `cross-niche-audit-2026-05-27.csv` (same folder) — open in Sheets for manual spot-check.

**SQL filter:** `content_class_id <> ingest_loop_content_class_id` AND primary creator_niche differs between planned vs final class.

**Note:** High conf (0.85–0.95) but `class_assignment_tier = low_conf` on all Gemini rows — tier reflects corpus policy, not model uncertainty alone.
