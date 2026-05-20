"""News/aggregator handles excluded from video_corpus, and per-creator
niche overrides for cross-niche creators whose videos the classifier
consistently mislabels.

These are NOT creators in the GetViews target audience (for the blocklist).
They are Vietnamese media outlets, news aggregators, or platform-owned
showbiz/sports channels that repackage other creators' content.
Their presence in the corpus pollutes niche signal, fakes patterns,
and surfaces irrelevant references in the Pattern grid + daily ritual.

Curate via the discovery query in the Sprint 8.5 PR description.
When adding a handle, group it under the right comment cluster so
the intent is auditable. Borderline cases (a handle that *might* be
a personal creator) should NOT be added unless the account clearly
posts media-style content across multiple unrelated niches.

CREATOR_NICHE_OVERRIDE: maps creator handles (lowercase, no @) to the
correct niche_id that should be used regardless of which ingest loop
encountered them. Use this when the Gemini classifier consistently
mislabels a creator because of visual similarity (e.g., talking-head
business coaches tagged as Skincare). The override replaces the
ingest-loop's niche_id for every video from that creator.

niche_id reference (legacy niche_taxonomy):
  2 = Làm đẹp / Skincare   3 = Thời trang Phụ kiện
  4 = Ẩm thực & Ăn uống    5 = Kinh doanh online / Bán hàng
  8 = Gym / Fitness          9 = Công nghệ / Tech
 11 = EduTok VN             13 = Hài / Giải trí
 15 = Tài chính / Đầu tư   16 = Du lịch / Travel
"""

from __future__ import annotations

# Lowercased, no @ prefix. Compared via .lower().lstrip("@") at lookup.
NEWS_AGGREGATOR_HANDLES: frozenset[str] = frozenset({
    # ── theanh28 family — repackages everything ─────────────────────
    "theanh28gaming", "theanh28sport", "theanh28trending",
    "theanh28entertainment", "hanoinews.theanh28",

    # ── vtvcab + vtv — state media tiktok arms ──────────────────────
    "vtvcab", "vtvcab.khampha.onlive", "vtvcab.sports",
    "vtvcab.gaming.onlive", "vtvcab.congnghe.onlive",
    "vtvcab.esports.onlive", "vtvcab.tintuc", "vtvcab.giaitri24h",
    "vtvcab.tieudiem", "vtvcab.trending", "vtvcab.giaitri",
    "vtvcab.thethao", "vtvindex", "yeuthoisuvtv",
    "truyenhinhthanhhoa.ttv", "truyenhinhnghean",

    # ── 24h family — sports + general news aggregator ───────────────
    "24h.sports", "24h.tinmoi", "bongda24h.vn.official",
    "24h_nhieuchuyen", "24hmoney.dautu",

    # ── FPT Play / platform sports news ─────────────────────────────
    "fptplay.sports", "fptplay.bongdaviet",

    # ── Sports media outlets ────────────────────────────────────────
    "thethao247.vn", "thethaovavanhoa", "thethao.net206",
    "thethaovacuocsong21", "bongdavadoisong", "sportfocusvn", "asiasportvn",
    "btsport739taquangbuu", "chuyensports",
    "football.century_", "football_nvc", "minhhuu_football",
    "sinregar_football", "ptfootball", "ducansport",
    "khangsport00", "onlivesports", "onsportsplus",
    "oksportvn", "chusssport.offici", "ilovefootball31299",
    "jogarbolasport", "uniscore.football", "kin.cng.sports.ty",
    "baseline_sport", "mediapickleballvietnam",

    # ── Gaming/esports news (coverage outlets, not creators) ────────
    "kiran.aov.news", "hung_aovnews", "vovgamesport",
    "jettvn", "tethan.news", "freefireesportsvn",
    "freefireesportswc", "tsa.esport_1",

    # ── General news / showbiz aggregators ──────────────────────────
    "28international",
    "znewssocial", "kenh14official", "kenh14disoisaodi",
    "beatvn_official", "news360.k37", ".vni.media",
    "vnexpress_hanoi", "vietnamnet.vn", "tayninh.news",
    "sunseeshowbiz", "muoivove", "vkr_news", "k.news_vn",
    "kenh7.news", "amgland.news", "tintuciran", "tram.tintuc",
    "trm.tin.tc.24h", "tinshowbiz2026", "quayducshowbiz",
    "bhmediacomedy", "xemxe24h", "congnghe24h.gmv",
    "locoloconews", "eva.vnsao",

    # ── Auto / legal / biz news ─────────────────────────────────────
    "autonews.vneconomy", "auto5.vn", "thuvienphapluat.vn",
    "phapluatchinhsach.vn", "aftvmedia", "plxh.vn",
    "vietnameconomynews",
})


CREATOR_NICHE_OVERRIDE: dict[str, int] = {
    # ── Business / F&B coaching misclassified as Skincare ───────────────
    # andypham.academy teaches restaurant operations, HR, and F&B brand
    # management. Gemini tags talking-head + green-screen frames as skincare.
    # Correct bucket: niche_id=5 (Kinh doanh online / Bán hàng).
    "andypham.academy": 5,
    # Curnon — jewelry / fashion brand; thin hashtags often mis-route to skincare.
    "curnon.official": 3,
}


def niche_override_for_handle(handle: str | None) -> int | None:
    """Return the forced niche_id for this creator, or None if no override.

    Call this after the blocklist check and use the result to replace the
    ingest-loop's ``niche_id`` before building the corpus row.
    """
    if not handle or not isinstance(handle, str):
        return None
    normalized = handle.strip().lstrip("@").lower()
    return CREATOR_NICHE_OVERRIDE.get(normalized)


def is_blocklisted_handle(handle: str | None) -> bool:
    """Case-insensitive, @-tolerant blocklist check.

    ``video_corpus.creator_handle`` is stored lowercase without the
    leading @, but be defensive — incoming awemes from EnsembleData
    may carry either form. Falsy / non-string inputs return False.
    """
    if not handle or not isinstance(handle, str):
        return False
    normalized = handle.strip().lstrip("@").lower()
    if not normalized:
        return False
    return normalized in NEWS_AGGREGATOR_HANDLES


__all__ = ["NEWS_AGGREGATOR_HANDLES", "CREATOR_NICHE_OVERRIDE", "is_blocklisted_handle", "niche_override_for_handle"]
