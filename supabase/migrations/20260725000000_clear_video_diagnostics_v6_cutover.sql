-- Pre-launch v6 cutover: drop cached on-demand diagnoses built without section-pool JSON.
-- Safe while there are no production users; forces fresh analyze with GETVIEWS_DIAGNOSIS_SECTION_MODE=1.
-- Does not touch answer_sessions / chat history rows.

TRUNCATE public.video_diagnostics;
