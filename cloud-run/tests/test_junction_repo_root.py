"""Junction seed SQL must resolve in local dev and Docker (/app) layouts."""

from __future__ import annotations

from pathlib import Path

from getviews_pipeline.junction_content_class import (
    _PR1_MIGRATION,
    _repo_root,
    primary_content_class_id_by_niche_and_format,
)


def test_repo_root_finds_pr1_migration() -> None:
    root = _repo_root()
    assert (root / _PR1_MIGRATION).is_file()


def test_primary_content_class_map_non_empty() -> None:
    m = primary_content_class_id_by_niche_and_format()
    assert len(m) > 40
    assert m.get((4, "tutorial"))  # food + tutorial


def test_docker_layout_parents1_has_migrations(tmp_path: Path, monkeypatch) -> None:
    """Simulate Cloud Run: /app/getviews_pipeline/module.py + /app/supabase/migrations/."""
    pkg = tmp_path / "getviews_pipeline"
    pkg.mkdir()
    mod = pkg / "junction_content_class.py"
    mod.write_text("# stub\n", encoding="utf-8")
    mig_dir = tmp_path / "supabase/migrations"
    mig_dir.mkdir(parents=True)
    (mig_dir / Path(_PR1_MIGRATION).name).write_text("-- stub\n", encoding="utf-8")

    import getviews_pipeline.junction_content_class as jc

    monkeypatch.setattr(jc, "__file__", str(mod))
    assert _repo_root() == tmp_path
