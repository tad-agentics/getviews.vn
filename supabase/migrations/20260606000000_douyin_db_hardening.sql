-- 2026-06-06 — D6a — Kho Douyin · DB hardening pass.
--
-- Audit findings from the post-D5 review (see PR #227 audit notes).
-- Five small DB-only changes; no app code touches the schema beyond what
-- it already does.
--
-- ── 1) HIGH · index for /douyin/patterns read order ────────────────
--
-- ``douyin_patterns_data.fetch_douyin_patterns`` orders
-- ``week_of DESC, niche_id ASC, rank ASC``. Existing
-- ``idx_douyin_patterns_niche_week`` leads on ``niche_id``, so Postgres
-- can't satisfy the leading-column-DESC sort with it and falls back to
-- a sort step. Add a complementary index that matches the read path.
--
-- Keep the original (niche_id, week_of, rank) index — the orchestrator's
-- "give me niche N this week" lookups still benefit from it.

CREATE INDEX IF NOT EXISTS idx_douyin_patterns_week_niche_rank
  ON public.douyin_patterns (week_of DESC, niche_id ASC, rank ASC);


-- ── 2) HIGH · CHECK constraint enforcing eta_weeks_min <= eta_weeks_max
--
-- Pydantic enforces this in ``DouyinAdaptSynth.model_validator`` (D3a),
-- but a manual SQL UPDATE could violate it. Add a defensive CHECK so
-- the FE never has to handle inverted ranges.
--
-- The constraint is permissive on NULL (one or both unset) — D2 ingest
-- lands rows before D3 synth runs, so NULLs are legal.

ALTER TABLE public.douyin_video_corpus
  ADD CONSTRAINT douyin_video_corpus_eta_weeks_ordered_chk
  CHECK (
    eta_weeks_min IS NULL
    OR eta_weeks_max IS NULL
    OR eta_weeks_min <= eta_weeks_max
  );


-- ── 3) LOW · CHECK constraint on sample_video_ids length ───────────
--
-- D5b's ``DouyinPatternEntry`` constrains ``sample_video_ids`` to 2-5
-- entries, but only Pydantic enforces it. Service-role-only writes mean
-- it's unlikely to drift in practice; defense-in-depth nonetheless.

ALTER TABLE public.douyin_patterns
  ADD CONSTRAINT douyin_patterns_sample_video_ids_len_chk
  CHECK (array_length(sample_video_ids, 1) BETWEEN 2 AND 5);


-- ── 4) LOW · harmonize FK cascade behaviour for douyin_patterns.niche_id
--
-- Asymmetry today:
--   • ``douyin_video_corpus.niche_id`` → no ON DELETE clause (= NO
--     ACTION, blocks niche delete when corpus FK exists).
--   • ``douyin_patterns.niche_id``     → ON DELETE CASCADE (silently
--     wipes pattern history).
--
-- Niches are soft-deleted via ``active=FALSE`` in practice; hard deletes
-- are operator-only and should require explicit cleanup of dependent
-- rows. Aligning ``douyin_patterns`` with the corpus's safer default
-- protects pattern history from accidental cascade.
--
-- Postgres has no ALTER ... ALTER FK action; we drop+recreate the FK.

ALTER TABLE public.douyin_patterns
  DROP CONSTRAINT IF EXISTS douyin_patterns_niche_id_fkey;

ALTER TABLE public.douyin_patterns
  ADD CONSTRAINT douyin_patterns_niche_id_fkey
  FOREIGN KEY (niche_id) REFERENCES public.douyin_niche_taxonomy (id);


-- ── 5) Comments documenting the hardened invariants ────────────────

COMMENT ON CONSTRAINT douyin_video_corpus_eta_weeks_ordered_chk
  ON public.douyin_video_corpus IS
  'D6a — defense-in-depth for DouyinAdaptSynth model_validator. Pydantic guards '
  'eta_weeks_min <= eta_weeks_max in the synth, but a manual UPDATE could break it.';

COMMENT ON CONSTRAINT douyin_patterns_sample_video_ids_len_chk
  ON public.douyin_patterns IS
  'D6a — mirror of DouyinPatternEntry.sample_video_ids min_length=2 / max_length=5.';

COMMENT ON CONSTRAINT douyin_patterns_niche_id_fkey
  ON public.douyin_patterns IS
  'D6a — NO ACTION (not CASCADE) so a hard-delete of a niche is BLOCKED if patterns '
  'reference it. Niches are soft-deleted via active=FALSE in practice; this preserves '
  'pattern history through accidental DELETEs.';
