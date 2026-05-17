# sprint3-personas-slang

**Plan:** diagnosis-first plan — full 12-section taxonomy coverage  
**Status:** complete (2026-05-17)  
**Scope:** Sprint 3 — §11 six Vietnamese **creator** persona slugs + slang lexicon merge + persona **signals** + v6 `persona` section pool; corpus **dominant_creator_persona** (mode ≥2) on channel context; `VideoAnalysis` fields `creator_persona`, `persona_consistency_signals`, `slang_*`; Gemini + batch ingest merge `merge_lexicon_slang_into_video_analysis_dict`.  
**Acceptance:** Plan § Sprint 3 — persona slugs validate; lexicon enrichment; four `section_id=persona` signals + section emit when salient; tests `test_persona_signals_sprint3.py`; full pytest green.  
**QA:** `artifacts/qa-reports/sprint3-personas-slang-baseline.json`.  
**Note:** `speech_register` in JSON (Pydantic accepts alias `register` from Gemini).
