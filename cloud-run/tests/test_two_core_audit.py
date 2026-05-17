"""Phase 6.1 — Two-core architecture audit.

Verifies:
1. corpus_ingest._download_and_analyze_single_aweme delegates to
   async_run_extraction_core (not gemini.analyze_video directly).
2. douyin_ingest._process_douyin_aweme_for_ingest delegates to
   async_run_extraction_core (not gemini.analyze_video directly).
3. corpus_ingest does NOT import any diagnosis-layer symbols at the module
   level (synthesize_diagnosis_v2, finalize_video_narrative_layer, etc.).
4. run_extraction_core and async_run_extraction_core are importable from
   services.extraction.
5. run_video_diagnosis_core is importable from services.diagnosis.
"""
import ast
import importlib
from pathlib import Path

CLOUD_RUN_ROOT = Path(__file__).parents[1]
PIPELINE_ROOT = CLOUD_RUN_ROOT / "getviews_pipeline"

DIAGNOSIS_SYMBOLS = {
    "synthesize_diagnosis_v2",
    "synthesize_diagnosis_carousel_v2",
    "finalize_video_narrative_layer",
    "build_diagnosis_narrative_prompt",
    "build_carousel_diagnosis_narrative_prompt",
}


def _module_imports(path: Path) -> set[str]:
    """Return all names imported at the module level (excluding docstrings)."""
    tree = ast.parse(path.read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(alias.asname or alias.name)
    return imported


def test_corpus_ingest_no_diagnosis_imports():
    """corpus_ingest must not import diagnosis-layer symbols."""
    imports = _module_imports(PIPELINE_ROOT / "corpus_ingest.py")
    violations = imports & DIAGNOSIS_SYMBOLS
    assert not violations, (
        f"corpus_ingest.py imports diagnosis-layer symbols: {violations}. "
        "Batch must only reach the extraction layer."
    )


def test_douyin_ingest_no_diagnosis_imports():
    """douyin_ingest must not import diagnosis-layer symbols."""
    imports = _module_imports(PIPELINE_ROOT / "douyin_ingest.py")
    violations = imports & DIAGNOSIS_SYMBOLS
    assert not violations, (
        f"douyin_ingest.py imports diagnosis-layer symbols: {violations}. "
        "Batch must only reach the extraction layer."
    )


def test_extraction_core_importable():
    """run_extraction_core and async_run_extraction_core must be importable."""
    mod = importlib.import_module("getviews_pipeline.services.extraction")
    assert callable(getattr(mod, "run_extraction_core", None)), (
        "run_extraction_core not found in services.extraction"
    )
    assert callable(getattr(mod, "async_run_extraction_core", None)), (
        "async_run_extraction_core not found in services.extraction"
    )


def test_diagnosis_core_importable():
    """run_video_diagnosis_core must be importable from services.diagnosis."""
    mod = importlib.import_module("getviews_pipeline.services.diagnosis")
    assert callable(getattr(mod, "run_video_diagnosis_core", None)), (
        "run_video_diagnosis_core not found in services.diagnosis"
    )


def test_corpus_ingest_uses_extraction_core():
    """corpus_ingest._download_and_analyze_single_aweme source must reference
    async_run_extraction_core, not call gemini.analyze_video directly.
    """
    corpus_src = (PIPELINE_ROOT / "corpus_ingest.py").read_text()
    assert "async_run_extraction_core" in corpus_src, (
        "corpus_ingest.py must delegate to async_run_extraction_core"
    )
    # gemini.analyze_video should not appear in corpus_ingest (only via core)
    assert "gemini.analyze_video" not in corpus_src, (
        "corpus_ingest.py must not call gemini.analyze_video directly"
    )


def test_douyin_ingest_uses_extraction_core():
    """douyin_ingest must delegate to async_run_extraction_core."""
    douyin_src = (PIPELINE_ROOT / "douyin_ingest.py").read_text()
    assert "async_run_extraction_core" in douyin_src, (
        "douyin_ingest.py must delegate to async_run_extraction_core"
    )
    assert "gemini.analyze_video" not in douyin_src, (
        "douyin_ingest.py must not call gemini.analyze_video directly"
    )


def test_finish_analysis_reachable_via_core():
    """_finish_analysis must exist in analysis_core — reachable via run_extraction_core."""
    ac_src = (PIPELINE_ROOT / "analysis_core.py").read_text()
    assert "_finish_analysis" in ac_src, (
        "_finish_analysis not found in analysis_core.py — extraction core invariant broken"
    )
    # Both analyze_aweme (video) and _finish_analysis should be in the same module
    assert "analyze_aweme" in ac_src, (
        "analyze_aweme not found in analysis_core.py"
    )
