"""Services package — single-direction dependency layer.

Routers → Services → (gemini, ensemble, supabase_client, analysis_core, analysis_guards, ...)
No service module imports from routers/. No service module imports from pipelines.py or
video_analyze.py (those become thin shims that re-export from here).
"""
