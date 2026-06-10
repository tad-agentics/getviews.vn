"""TD-7 tripwire — live and batch video extraction must stay identical.

Both paths build their Gemini request from the same trio:
``build_video_extraction_system_instruction()`` +
``_configure_extraction_generate_config(VideoAnalysis.model_json_schema())`` +
``build_video_extraction_user_turn_vi(dual_hook_window=…, hook_window_seconds=…,
base_fps_display=…)`` with the supplemental ASR/caption prefix prepended the
same way. Parity today is enforced only by both call sites sharing those
helpers — this test pins the shape of BOTH call sites in source so a
one-sided prompt/config edit fails CI instead of silently forking the corpus
(batch) from live diagnosis (audit 2026-06-10 M-10).
"""

from __future__ import annotations

import re
from pathlib import Path

_SRC = (Path(__file__).resolve().parents[1] / "getviews_pipeline" / "gemini.py").read_text(
    encoding="utf-8"
)

# The invocation fingerprint both paths must contain, in order.
_FINGERPRINT = [
    r"build_video_extraction_system_instruction\(\)",
    r"_configure_extraction_generate_config\(",
    r"VideoAnalysis\.model_json_schema\(\)",
    r'kind="video"',
    r"system_text=sys_inst",
    r"build_video_extraction_user_turn_vi\(",
    r"dual_hook_window=GEMINI_HOOK_WINDOW_DUAL_PART",
    r"float\(GEMINI_HOOK_WINDOW_END_SEC\)",
    r"float\(GEMINI_VIDEO_BASE_FPS\)",
    r'prefix \+ "\\n\\n" \+ user_turn',
]


def _extract_function(name: str) -> str:
    m = re.search(rf"\ndef {name}\(.*?(?=\ndef |\Z)", _SRC, re.DOTALL)
    assert m, f"{name} not found in gemini.py — TD-7 tripwire needs updating"
    return m.group(0)


def _assert_fingerprint(body: str, where: str) -> None:
    pos = 0
    for pat in _FINGERPRINT:
        m = re.search(pat, body[pos:])
        assert m, (
            f"TD-7 parity fingerprint broken in {where}: missing/reordered `{pat}`. "
            "If you changed the extraction prompt/config, change BOTH the live "
            "path (analyze_video upload helper) and "
            "build_video_corpus_batch_jsonl_record in the same commit, then "
            "update this fingerprint."
        )
        pos += m.start()


def test_batch_record_builder_matches_fingerprint() -> None:
    _assert_fingerprint(
        _extract_function("build_video_corpus_batch_jsonl_record"),
        "build_video_corpus_batch_jsonl_record (batch path)",
    )


def test_live_extraction_matches_fingerprint() -> None:
    # The live path's builder trio lives in the upload-and-extract helper —
    # locate it by the unique trio usage outside the batch builder.
    batch_body = _extract_function("build_video_corpus_batch_jsonl_record")
    rest = _SRC.replace(batch_body, "")
    # There must be exactly one other site using the system-instruction builder.
    sites = re.findall(r"build_video_extraction_system_instruction\(\)", rest)
    assert len(sites) == 1, (
        f"expected exactly 1 live call site of "
        f"build_video_extraction_system_instruction outside the batch builder, "
        f"found {len(sites)} — update the TD-7 tripwire for the new shape"
    )
    # Fingerprint the surrounding function.
    idx = rest.find("build_video_extraction_system_instruction()")
    fn_start = rest.rfind("\ndef ", 0, idx)
    next_def = rest.find("\ndef ", idx)
    live_body = rest[fn_start : next_def if next_def != -1 else len(rest)]
    _assert_fingerprint(live_body, "live extraction path")
