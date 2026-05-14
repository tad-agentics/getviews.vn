-- Phase 2 cleanup: drop legacy /channel/analyze infrastructure.
--
-- channel_formulas — cache table for the old corpus-only channel analysis
-- (GET /channel/analyze). Superseded by channel_diagnoses (Lightreel narrative)
-- which was shipped in the Phase 1 feature branch and has been stable for ≥7 days.
--
-- channel_corpus_stats — RPC called only by channel_analyze.py (now deleted).
-- niche_channel_benchmarks is intentionally KEPT — still called by the new
-- channel_diagnose endpoint.
--
-- Safe to run: channel_diagnose never reads or writes channel_formulas.
-- Rollback: restore from backup or re-run the original create migration.

DROP TABLE IF EXISTS channel_formulas CASCADE;

DROP FUNCTION IF EXISTS channel_corpus_stats(p_handle TEXT, p_niche INTEGER);
