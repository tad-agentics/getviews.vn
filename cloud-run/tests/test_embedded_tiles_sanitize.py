"""Embedded reference tiles must resolve from the synthesis pool with content proximity."""

from __future__ import annotations

from getviews_pipeline.gemini import (
    EMBED_CONTRACT_VERSION,
    _sanitize_diagnosis_embedded_tiles,
    _validate_diagnosis_vi_citations,
    count_valid_embedded_tiles,
    repair_diagnosis_vi_embedded_tiles,
)


def _slim(aid: str, desc: str, *, proximity: int, source: str = "corpus") -> dict:
    return {
        "aweme_id": aid,
        "desc": desc,
        "content_proximity_score": proximity,
        "source": source,
        "thumbnail_url": f"https://thumb/{aid}.jpg",
        "tiktok_url": f"https://tiktok.com/@x/video/{aid}",
        "views": 68_000,
    }


def test_sanitize_drops_off_topic_embedded_tiles() -> None:
    refs = [
        _slim("111", "đồng hồ nam luxury", proximity=3),
        _slim("222", "mặt trông bị quá chưa", proximity=0),
    ]
    allowed = {"111", "222"}
    diag_vi = {
        "sections": [
            {
                "section_id": "diagnosis",
                "text_vi": "prose",
                "embedded_tiles": [{"aweme_id": "222"}],
            }
        ]
    }
    _sanitize_diagnosis_embedded_tiles(diag_vi, refs, allowed)
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 1
    assert tiles[0]["aweme_id"] == "111"


def test_sanitize_resolves_on_topic_tile_from_pool() -> None:
    refs = [
        _slim("111", "đồng hồ nam luxury", proximity=2),
        _slim("222", "unrelated viral", proximity=0),
    ]
    allowed = {"111", "222"}
    diag_vi = {
        "sections": [
            {
                "section_id": "niche_pattern",
                "embedded_tiles": [{"aweme_id": "111"}],
            }
        ]
    }
    _sanitize_diagnosis_embedded_tiles(diag_vi, refs, allowed)
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 1
    assert tiles[0]["aweme_id"] == "111"
    assert "đồng hồ" in (tiles[0].get("caption_snippet") or "")


def test_sanitize_keeps_corpus_pool_tile_when_proximity_zero() -> None:
    refs = [_slim("111", "đồng hồ dây da", proximity=0, source="corpus")]
    diag_vi = {
        "sections": [
            {"section_id": "diagnosis", "embedded_tiles": [{"aweme_id": "111"}]}
        ]
    }
    _sanitize_diagnosis_embedded_tiles(diag_vi, refs, {"111"})
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 1
    assert tiles[0]["aweme_id"] == "111"


def test_inject_fallback_tile_when_gemini_omits_embedded_tiles() -> None:
    from getviews_pipeline.gemini import _inject_fallback_embedded_tiles

    refs = [
        _slim("111", "đồng hồ A", proximity=3, source="corpus"),
        _slim("222", "đồng hồ B", proximity=2, source="corpus"),
        _slim("333", "đồng hồ C", proximity=1, source="corpus"),
    ]
    diag_vi = {
        "sections": [
            {"section_id": "hook_analysis", "text_vi": "prose", "embedded_tiles": []},
        ]
    }
    _inject_fallback_embedded_tiles(diag_vi, refs, {"111", "222", "333"})
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 3
    assert [t["aweme_id"] for t in tiles] == ["111", "222", "333"]
    assert all(t.get("narrative_vi") for t in tiles)


def test_sanitize_keeps_live_search_tile_when_proximity_zero() -> None:
    refs = [
        _slim("111", "đồng hồ nam dây da", proximity=0, source="live_search"),
        _slim("222", "unrelated beauty", proximity=0, source="live_search"),
    ]
    diag_vi = {
        "sections": [
            {
                "section_id": "hook_analysis",
                "embedded_tiles": [{"aweme_id": "111"}],
            }
        ]
    }
    _sanitize_diagnosis_embedded_tiles(diag_vi, refs, {"111", "222"})
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 1
    assert tiles[0]["aweme_id"] == "111"


def test_repair_diagnosis_vi_embedded_tiles_injects_when_empty() -> None:
    refs = [_slim("111", "đồng hồ nam luxury", proximity=1)]
    diag_vi = {
        "sections": [
            {"section_id": "diagnosis", "text_vi": "prose", "embedded_tiles": []},
        ]
    }
    n = repair_diagnosis_vi_embedded_tiles(diag_vi, refs)
    assert n >= 1
    assert count_valid_embedded_tiles(diag_vi) >= 1


def test_embed_contract_version_constant() -> None:
    assert EMBED_CONTRACT_VERSION >= 2


def test_sanitize_dedupes_duplicate_aweme_in_one_section() -> None:
    refs = [_slim("111", "caption A", proximity=2)]
    diag_vi = {
        "sections": [
            {
                "section_id": "diagnosis",
                "embedded_tiles": [
                    {"aweme_id": "111", "narrative_vi": "same"},
                    {"aweme_id": "111", "narrative_vi": "same"},
                    {"aweme_id": "111", "narrative_vi": "same"},
                ],
            }
        ]
    }
    _sanitize_diagnosis_embedded_tiles(diag_vi, refs, {"111"})
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 1
    assert tiles[0]["aweme_id"] == "111"


def test_sanitize_dedupes_same_aweme_across_sections() -> None:
    refs = [
        _slim("111", "A", proximity=3),
        _slim("222", "B", proximity=2),
        _slim("333", "C", proximity=1),
    ]
    allowed = {"111", "222", "333"}
    diag_vi = {
        "sections": [
            {
                "section_id": "diagnosis",
                "embedded_tiles": [{"aweme_id": "111"}, {"aweme_id": "222"}],
            },
            {
                "section_id": "hook_analysis",
                "embedded_tiles": [{"aweme_id": "111"}, {"aweme_id": "333"}],
            },
        ]
    }
    _sanitize_diagnosis_embedded_tiles(diag_vi, refs, allowed)
    diag_ids = [t["aweme_id"] for t in diag_vi["sections"][0]["embedded_tiles"]]
    hook_ids = [t["aweme_id"] for t in diag_vi["sections"][1]["embedded_tiles"]]
    assert diag_ids == ["111", "222"]
    assert hook_ids == ["333"]
    assert "111" not in hook_ids


def test_inject_fallback_rotates_peers_across_empty_sections() -> None:
    from getviews_pipeline.gemini import _inject_fallback_embedded_tiles

    refs = [
        _slim("111", "A", proximity=3, source="corpus"),
        _slim("222", "B", proximity=2, source="corpus"),
        _slim("333", "C", proximity=1, source="corpus"),
        _slim("444", "D", proximity=1, source="corpus"),
    ]
    diag_vi = {
        "sections": [
            {"section_id": "diagnosis", "embedded_tiles": []},
            {"section_id": "hook_analysis", "embedded_tiles": []},
        ]
    }
    _inject_fallback_embedded_tiles(diag_vi, refs, {"111", "222", "333", "444"})
    from getviews_pipeline.gemini import _dedupe_embedded_tiles_across_sections

    _dedupe_embedded_tiles_across_sections(diag_vi)
    diag_ids = [t["aweme_id"] for t in diag_vi["sections"][0]["embedded_tiles"]]
    hook_ids = [t["aweme_id"] for t in diag_vi["sections"][1]["embedded_tiles"]]
    assert len(diag_ids) == 3
    assert len(hook_ids) == 1
    assert not set(diag_ids) & set(hook_ids)
    assert set(diag_ids) | set(hook_ids) <= {"111", "222", "333", "444"}


def test_validate_citations_invokes_tile_sanitize() -> None:
    refs = [_slim("111", "match caption keyword đồng hồ", proximity=1)]
    diag_vi = {
        "sections": [
            {
                "section_id": "diagnosis",
                "embedded_tiles": [{"aweme_id": "111", "caption_snippet": "wrong"}],
            }
        ]
    }
    _validate_diagnosis_vi_citations(diag_vi, {"111"}, refs)
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 1
    assert "đồng hồ" in (tiles[0].get("caption_snippet") or "")


# ---------------------------------------------------------------------------
# 2026-06-12 — views floor on embedded reference tiles
# (hook section cited 7.1K/6.6K-view clips against a 534K-view analysed video)
# ---------------------------------------------------------------------------


def _slim_v(aid: str, desc: str, *, proximity: int, views: int) -> dict:
    out = _slim(aid, desc, proximity=proximity)
    out["views"] = views
    return out


def test_views_floor_drops_weak_refs_when_stronger_exists() -> None:
    refs = [
        _slim_v("111", "đồng hồ A", proximity=1, views=300_000),
        _slim_v("222", "đồng hồ B", proximity=1, views=7_100),
        _slim_v("333", "đồng hồ C", proximity=1, views=6_600),
    ]
    diag_vi = {
        "sections": [
            {
                "section_id": "hook_analysis",
                "embedded_tiles": [
                    {"aweme_id": "111"},
                    {"aweme_id": "222"},
                    {"aweme_id": "333"},
                ],
            }
        ]
    }
    _sanitize_diagnosis_embedded_tiles(
        diag_vi, refs, {"111", "222", "333"}, target_views=534_000
    )
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    # Floor = max(0.2 × 534K, pool median 7.1K) = 106.8K → fewer tiles, not weak ones.
    assert [t["aweme_id"] for t in tiles] == ["111"]


def test_views_floor_uses_pool_median_when_target_is_small() -> None:
    refs = [
        _slim_v("111", "A", proximity=1, views=60_000),
        _slim_v("222", "B", proximity=1, views=50_000),
        _slim_v("333", "C", proximity=1, views=3_000),
    ]
    diag_vi = {
        "sections": [
            {
                "section_id": "diagnosis",
                "embedded_tiles": [
                    {"aweme_id": "111"},
                    {"aweme_id": "222"},
                    {"aweme_id": "333"},
                ],
            }
        ]
    }
    # 0.2 × 10K = 2K, but pool median = 50K → the 3K ref is below the niche bar.
    _sanitize_diagnosis_embedded_tiles(
        diag_vi, refs, {"111", "222", "333"}, target_views=10_000
    )
    ids = [t["aweme_id"] for t in diag_vi["sections"][0]["embedded_tiles"]]
    assert ids == ["111", "222"]


def test_views_floor_keeps_pool_when_no_better_candidate() -> None:
    refs = [
        _slim_v("222", "B", proximity=1, views=7_100),
        _slim_v("333", "C", proximity=1, views=6_600),
    ]
    diag_vi = {
        "sections": [
            {
                "section_id": "hook_analysis",
                "embedded_tiles": [{"aweme_id": "222"}, {"aweme_id": "333"}],
            }
        ]
    }
    # Whole pool is weak — no better candidates exist, so nothing is dropped.
    _sanitize_diagnosis_embedded_tiles(
        diag_vi, refs, {"222", "333"}, target_views=534_000
    )
    ids = [t["aweme_id"] for t in diag_vi["sections"][0]["embedded_tiles"]]
    assert ids == ["222", "333"]


def test_views_floor_inactive_without_target_views() -> None:
    refs = [
        _slim_v("111", "A", proximity=1, views=300_000),
        _slim_v("222", "B", proximity=1, views=7_100),
    ]
    diag_vi = {
        "sections": [
            {
                "section_id": "diagnosis",
                "embedded_tiles": [{"aweme_id": "111"}, {"aweme_id": "222"}],
            }
        ]
    }
    _sanitize_diagnosis_embedded_tiles(diag_vi, refs, {"111", "222"})
    ids = [t["aweme_id"] for t in diag_vi["sections"][0]["embedded_tiles"]]
    assert ids == ["111", "222"]


def test_inject_fallback_respects_views_floor() -> None:
    refs = [
        _slim_v("111", "đồng hồ A", proximity=2, views=400_000),
        _slim_v("222", "đồng hồ B", proximity=3, views=7_000),
        _slim_v("333", "đồng hồ C", proximity=1, views=6_000),
    ]
    diag_vi = {
        "sections": [
            {"section_id": "hook_analysis", "text_vi": "prose", "embedded_tiles": []},
        ]
    }
    _sanitize_diagnosis_embedded_tiles(
        diag_vi, refs, {"111", "222", "333"}, target_views=534_000
    )
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    # Fallback inject only draws from the floored pool — the 400K peer, alone.
    assert [t["aweme_id"] for t in tiles] == ["111"]
    assert tiles[0].get("narrative_vi")


def test_repair_passes_target_views_through() -> None:
    refs = [
        _slim_v("111", "A", proximity=1, views=300_000),
        _slim_v("222", "B", proximity=1, views=7_100),
    ]
    diag_vi = {
        "sections": [
            {
                "section_id": "diagnosis",
                "embedded_tiles": [{"aweme_id": "111"}, {"aweme_id": "222"}],
            }
        ]
    }
    n = repair_diagnosis_vi_embedded_tiles(diag_vi, refs, target_views=534_000)
    assert n == 1
    ids = [t["aweme_id"] for t in diag_vi["sections"][0]["embedded_tiles"]]
    assert ids == ["111"]


def test_tile_narrative_needs_regen_legacy_handle_views() -> None:
    from getviews_pipeline.diagnose_parse import tile_narrative_needs_regen

    assert tile_narrative_needs_regen(
        "Kênh @tuyetmia204 (210.2K view) đang vận hành cực kỳ hiệu quả."
    )
    assert not tile_narrative_needs_regen(
        "Được chọn vì hook dạng câu hỏi giữ chân ngay 3 giây đầu."
    )


def test_fallback_tile_narrative_distinct_prose_on_duplicates() -> None:
    from getviews_pipeline.diagnose_parse import (
        ensure_distinct_tile_narratives,
        fallback_tile_narrative_vi,
    )

    t1 = {"author_handle": "user1", "views": 100000}
    t2 = {"author_handle": "user2", "views": 200000}
    t3 = {"author_handle": "user3", "views": 300000}

    # Verify that different indices generate different phrasings
    narrative_1 = fallback_tile_narrative_vi(t1, "hook_analysis", 0)
    narrative_2 = fallback_tile_narrative_vi(t2, "hook_analysis", 1)
    narrative_3 = fallback_tile_narrative_vi(t3, "hook_analysis", 2)

    # Copy redesigned in 1292db6/28b351b — each index lands on its own
    # opening-seconds angle and the three rotations stay distinct.
    assert "3 giây đầu" in narrative_1
    assert "hook mở màn" in narrative_2
    assert "nhịp mở" in narrative_3
    assert len({narrative_1, narrative_2, narrative_3}) == 3

    assert "Được chọn" in narrative_1 or "Tham chiếu" in narrative_1 or "Lý do tham chiếu" in narrative_1
    assert "đang vận hành cực kỳ hiệu quả" not in narrative_1
    assert "@user1" not in narrative_1

    # Test ensure_distinct_tile_narratives rotates them correctly
    tiles = [
        {"aweme_id": "111", "author_handle": "user1", "views": 100000, "narrative_vi": None},
        {"aweme_id": "222", "author_handle": "user2", "views": 200000, "narrative_vi": None},
        {"aweme_id": "333", "author_handle": "user3", "views": 300000, "narrative_vi": ""},
    ]
    ensure_distinct_tile_narratives(tiles, "hook_analysis")

    assert "3 giây đầu" in tiles[0]["narrative_vi"]
    assert "hook mở màn" in tiles[1]["narrative_vi"]
    assert "nhịp mở" in tiles[2]["narrative_vi"]
    assert len({t["narrative_vi"] for t in tiles}) == 3


# ---------------------------------------------------------------------------
# 2026-06-12 — identical narrative_vi repeated ACROSS sections
# ---------------------------------------------------------------------------


def test_tile_narratives_distinct_across_sections() -> None:
    """Live bug: «Được chọn vì cấu trúc format và nhịp dẫn nhất quán suốt
    clip...» repeated on tiles in different sections — the per-section dedupe
    restarted idx at 0, so featureless tiles in two sections regenerated the
    exact same fallback copy."""
    from getviews_pipeline.diagnose_parse import (
        ensure_distinct_tile_narratives_across_report,
    )

    repeated = (
        "Được chọn vì cấu trúc format và nhịp dẫn nhất quán suốt clip. "
        "Đối chiếu cách mở đầu và giữ chân với clip đang phân tích."
    )
    sections = [
        {
            "section_id": "diagnosis",
            "embedded_tiles": [
                {"aweme_id": "111", "narrative_vi": repeated},
            ],
        },
        {
            "section_id": "niche_pattern",
            "embedded_tiles": [
                {"aweme_id": "222", "narrative_vi": repeated},
                {"aweme_id": "333", "narrative_vi": repeated},
            ],
        },
    ]
    ensure_distinct_tile_narratives_across_report(sections)

    narratives = [
        t["narrative_vi"]
        for sec in sections
        for t in sec["embedded_tiles"]
    ]
    assert all(n and n.strip() for n in narratives)
    assert len(set(narratives)) == 3, narratives


def test_fallback_regen_never_collides_with_other_sections() -> None:
    """Featureless tiles (no hook/format) in different sections must not land
    on the same generic fallback — the bump retry must find a unique combo."""
    from getviews_pipeline.diagnose_parse import (
        ensure_distinct_tile_narratives_across_report,
    )

    sections = [
        {"section_id": "diagnosis", "embedded_tiles": [{"aweme_id": "1", "narrative_vi": ""}]},
        {"section_id": "diagnosis", "embedded_tiles": [{"aweme_id": "2", "narrative_vi": ""}]},
        {"section_id": "diagnosis", "embedded_tiles": [{"aweme_id": "3", "narrative_vi": ""}]},
    ]
    ensure_distinct_tile_narratives_across_report(sections)
    narratives = [sec["embedded_tiles"][0]["narrative_vi"] for sec in sections]
    assert len(set(narratives)) == 3, narratives


def test_three_tiles_in_one_section_never_share_narrative_even_when_gemini_repeats() -> None:
    from getviews_pipeline.diagnose_parse import ensure_distinct_tile_narratives

    same = "Tham chiếu vì clip này giữ chân ổn định hơn median ở cùng ngách."
    tiles = [
        {"aweme_id": "1", "narrative_vi": same},
        {"aweme_id": "2", "narrative_vi": same},
        {"aweme_id": "3", "narrative_vi": same},
    ]
    ensure_distinct_tile_narratives(tiles, "script_structure")
    assert len({t["narrative_vi"] for t in tiles}) == 3
