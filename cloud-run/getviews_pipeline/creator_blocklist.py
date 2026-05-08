"""News/aggregator handles excluded from video_corpus.

These are NOT creators in the GetViews target audience. They are
Vietnamese media outlets, news aggregators, or platform-owned
showbiz/sports channels that repackage other creators' content.
Their presence in the corpus pollutes niche signal, fakes patterns,
and surfaces irrelevant references in the Pattern grid + daily ritual.

Curate via the discovery query in the Sprint 8.5 PR description.
When adding a handle, group it under the right comment cluster so
the intent is auditable. Borderline cases (a handle that *might* be
a personal creator) should NOT be added unless the account clearly
posts media-style content across multiple unrelated niches.
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

    # ── Sports media outlets ────────────────────────────────────────
    "thethao247.vn", "thethaovavanhoa", "thethao.net206",
    "thethaovacuocsong21", "sportfocusvn", "asiasportvn",
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


__all__ = ["NEWS_AGGREGATOR_HANDLES", "is_blocklisted_handle"]
