"""§6 Sound — lifecycle, CML eligibility, dialect vs hook, layering (diagnosis-first Sprint 6)."""

from __future__ import annotations

from typing import Any

from getviews_pipeline.layer0_sound import normalize_lifecycle_phase
from getviews_pipeline.signals.base import Evidence, Signal

_LIFECYCLE_SALIENCE = {
    "emerging": 0.65,
    "parody": 0.6,
    "decline": 0.55,
    "growth": 0.55,
    "peak": 0.52,
}

_RADAR_TO_PHASE = {
    "accelerating": "growth",
    "peaking": "peak",
    "cooling": "decline",
}


def _ua(ctx: dict) -> dict[str, Any]:
    ua = ctx.get("user_analysis") or {}
    return ua if isinstance(ua, dict) else {}


def _us(ctx: dict) -> dict[str, Any]:
    us = ctx.get("user_stats") or {}
    return us if isinstance(us, dict) else {}


def _effective_lifecycle_phase(ctx: dict) -> tuple[str | None, str]:
    prof = _us(ctx).get("trending_sound_profile")
    if isinstance(prof, dict):
        ph = normalize_lifecycle_phase(prof.get("lifecycle_phase"))
        if ph:
            return ph, "trending_sounds.lifecycle_phase"
    sid = str(_us(ctx).get("sound_id") or "").strip()
    if not sid:
        return None, ""
    nm = ctx.get("niche_meta") or {}
    radar = nm.get("sound_radar") if isinstance(nm, dict) else None
    if not isinstance(radar, dict):
        return None, ""
    for bucket, mapped in _RADAR_TO_PHASE.items():
        for entry in radar.get(bucket) or []:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("sound_id") or "") != sid:
                continue
            if bucket == "accelerating":
                d = entry.get("delta_pct")
                try:
                    dnum = float(d)
                except (TypeError, ValueError):
                    dnum = 0.0
                if dnum >= 999.0 or dnum >= 200.0:
                    return "emerging", f"sound_radar.{bucket}"
            return mapped, f"sound_radar.{bucket}"
    return None, ""


def extract_sound_lifecycle_signal(ctx: dict) -> list[Signal]:
    phase, loc = _effective_lifecycle_phase(ctx)
    if not phase:
        return []
    sal = _LIFECYCLE_SALIENCE.get(phase)
    if sal is None:
        return []
    sid = str(_us(ctx).get("sound_id") or "").strip()
    title = str(_us(ctx).get("music_title") or "").strip()
    if phase in ("emerging", "growth"):
        tail = "cửa sổ cơ hội ngắn"
    elif phase == "peak":
        tail = "mức dùng ổn định trong ngách — an toàn nhưng dễ trùng lặp format"
    elif phase == "decline":
        tail = "xu hướng đang hạ nhiệt"
    else:
        tail = "giai đoạn nhại / biến thể — dễ bão hòa nhanh"
    claim = f"Sound đang ở phase {phase} trong ngách — {tail}."
    if phase in ("emerging", "growth"):
        suggested_fix = (
            "Ra thêm biến thể cùng sound trong 48–72h nếu emerging/growth; "
            "tránh dựa hoàn toàn vào sound đã decline."
        )
    elif phase == "peak":
        suggested_fix = (
            "Tách biệt bằng hook hoặc staging cá nhân — sound đang bão hòa, cần điểm nhấn riêng."
        )
    else:
        suggested_fix = "Chuẩn bị sound/template kế tiếp — xu hướng đang hạ nhiệt."
    return [
        Signal(
            id="sound_lifecycle_phase",
            section_id="sound",
            taxonomy_ref="§6",
            salience=sal,
            claim=claim,
            evidence=[
                Evidence(
                    type="niche_norms_pct",
                    quote=f"lifecycle={phase} sound_id={sid or 'n/a'} title={title or 'n/a'}",
                    location=loc,
                ),
            ],
            suggested_fix=suggested_fix,
        )
    ]


def extract_cml_eligibility_signal(ctx: dict) -> list[Signal]:
    if not _us(ctx).get("account_commercial_heuristic"):
        return []
    prof = _us(ctx).get("trending_sound_profile")
    if not isinstance(prof, dict):
        return []
    raw = prof.get("commercial_music_library_eligible")
    if raw is None:
        return []
    eligible = bool(raw)
    if eligible:
        return []
    sid = str(_us(ctx).get("sound_id") or "").strip()
    return [
        Signal(
            id="sound_cml_strip_risk",
            section_id="sound",
            taxonomy_ref="§6",
            salience=0.85,
            claim=(
                "Tài khoản mang tính thương mại nhưng sound không nằm diện CML-safe — "
                "rủi ro mute/strip khi scale."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"commercial_music_library_eligible=false sound_id={sid or 'n/a'}",
                    location="trending_sounds",
                ),
            ],
            suggested_fix="Đổi sang nhạc CML hoặc original có giấy phép rõ ràng trước khi chạy ads.",
        )
    ]


def extract_dialect_audio_consistency_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    hook = ua.get("hook_analysis") or {}
    dialect_spoken = ""
    if isinstance(hook, dict):
        dialect_spoken = str(hook.get("dialect_detected") or "").strip().lower()
    audio_d = str(ua.get("sound_dialect_audio") or "").strip().lower()
    if not dialect_spoken or dialect_spoken in ("none", ""):
        return []
    if not audio_d or audio_d in ("none", ""):
        return []
    if dialect_spoken.replace("-", "_") == audio_d.replace("-", "_"):
        return []
    return [
        Signal(
            id="sound_dialect_audio_mismatch",
            section_id="sound",
            taxonomy_ref="§6",
            salience=0.55,
            claim=(
                f"Giọng thoại ({dialect_spoken}) và màu âm nhạc nền ({audio_d}) không đồng phục — "
                f"dễ làm khán giả đọc sai vùng miền/độ authentic."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"dialect_detected={dialect_spoken} sound_dialect_audio={audio_d}",
                    location="hook_analysis+sound_dialect_audio",
                ),
            ],
            suggested_fix="Chọn BGM trung tính hoặc cùng vùng miền với thoại chính.",
        )
    ]


def extract_sound_layering_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    fmt = str(ctx.get("content_format") or "").lower()
    topics = " ".join(str(x).lower() for x in (ua.get("topics") or []))
    mukbangish = fmt == "mukbang" or "asmr" in topics or "mukbang" in topics
    if not mukbangish:
        return []
    layering = str(ua.get("sound_layering") or "").strip().lower()
    if layering != "thin":
        return []
    return [
        Signal(
            id="sound_layering_thin_mukbang",
            section_id="sound",
            taxonomy_ref="§6",
            salience=0.5,
            claim=(
                "Format mukbang/ASMR nhưng mix âm thanh mỏng (thiếu tách lớp BGM–SFX–lời) "
                "— dễ giảm immersion."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"content_format={fmt} sound_layering={layering}",
                    location="ctx.content_format+sound_layering",
                ),
            ],
            suggested_fix="Tách track: hạ BGM dưới lời; giữ SFX ăn uống rõ có nhịp.",
        )
    ]


def extract_sound_trending_mismatch_signal(ctx: dict) -> list[Signal]:
    """P1 — sound_id không nằm radar trending ngách."""
    sid = str(_us(ctx).get("sound_id") or "").strip()
    if not sid:
        return []
    nm = ctx.get("niche_meta") or {}
    radar = nm.get("sound_radar") if isinstance(nm, dict) else None
    if not isinstance(radar, dict):
        return []
    trending_ids: set[str] = set()
    for bucket in ("accelerating", "peaking", "cooling"):
        for entry in radar.get(bucket) or []:
            if isinstance(entry, dict):
                eid = str(entry.get("sound_id") or "").strip()
                if eid:
                    trending_ids.add(eid)
    if len(trending_ids) < 2:
        return []
    if sid in trending_ids:
        return []
    return [
        Signal(
            id="sound_trending_mismatch",
            section_id="sound",
            taxonomy_ref="§6",
            salience=0.57,
            claim=(
                f"Sound `{sid[:12]}…` không khớp {len(trending_ids)} sound đang "
                "tích lũy trong radar ngách — có thể bỏ lỡ sóng FYP."
            ),
            evidence=[
                Evidence(
                    type="niche_norms_pct",
                    quote=f"sound_id={sid} radar_ids={len(trending_ids)}",
                    location="user_stats.sound_id+niche_meta.sound_radar",
                )
            ],
            suggested_fix="Thử 1 trong sound accelerating/peaking của ngách hoặc biến thể hook riêng.",
        )
    ]


def extract_sound_no_audio_hook_window_signal(ctx: dict) -> list[Signal]:
    """P1 — không có thoại / first_word trong cửa sổ hook 0–3s."""
    ua = _ua(ctx)
    ha = ua.get("hook_analysis") if isinstance(ua.get("hook_analysis"), dict) else {}
    timeline = ha.get("hook_timeline") if isinstance(ha.get("hook_timeline"), list) else []
    has_first_word = False
    for ev in timeline:
        if not isinstance(ev, dict):
            continue
        if str(ev.get("event") or "").lower().replace("-", "_") != "first_word":
            continue
        try:
            t = float(ev.get("t") or 99)
        except (TypeError, ValueError):
            continue
        if 0.0 <= t <= 3.0:
            has_first_word = True
            break
    if has_first_word:
        return []
    tr = str(ua.get("audio_transcript") or "").strip()
    return [
        Signal(
            id="sound_no_audio_hook_window",
            section_id="sound",
            taxonomy_ref="§6",
            salience=0.66,
            claim=(
                "Cửa sổ hook 0–3s không có thoại rõ (first_word) — "
                "viewer tắt tiếng khó bắt promise."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"hook_timeline_first_word=false transcript_len={len(tr)}",
                    location="user_analysis.hook_analysis+audio_transcript",
                )
            ],
            suggested_fix="Mở bằng 1 câu thoại ngắn ≤8 từ hoặc text overlay promise rõ trước giây 3.",
        )
    ]


def extract_sound_signals(ctx: dict) -> list[Signal]:
    out: list[Signal] = []
    for fn in (
        extract_sound_lifecycle_signal,
        extract_cml_eligibility_signal,
        extract_dialect_audio_consistency_signal,
        extract_sound_layering_signal,
        extract_sound_trending_mismatch_signal,
        extract_sound_no_audio_hook_window_signal,
    ):
        out.extend(fn(ctx))
    return out
