# EnsembleData dashboard labels ↔ this codebase

Dashboard SKUs (e.g. “User Detailed Info”, “Music Information”) are **EnsembleData product labels**. They do not always equal a single HTTP path in our client.

## Verified in repo

| Dashboard-style label (hypothesis) | What we actually call | Module |
|-----------------------------------|-------------------------|--------|
| Keyword search | `GET …/tt/keyword/search` via `fetch_keyword_search` | `ensemble.py` |
| Hashtag posts | `GET …/tt/hashtag/posts` via `fetch_hashtag_posts` | `ensemble.py` |
| Post info | `GET …/tt/post/info` via `fetch_post_info` | `ensemble.py` |
| Post multi-info | `GET …/tt/post/multi-info` via `fetch_post_multi_info` | `ensemble.py` |
| User posts | `GET …/tt/user/posts` via `fetch_user_posts` | `ensemble.py`, `pipelines.py` |
| User search | `GET …/tt/user/search` via `fetch_user_search` | `ensemble.py`, `pipelines.py` |
| Comments | `GET …/tt/post/comments` via `_ensemble_get` | `comment_radar.py` |

## Not implemented as a standalone “music” HTTP call

Music metadata is read from **`aweme["music"]`** on responses from search/hashtag/post payloads (`corpus_ingest`, `parse_metadata`). If the ED dashboard shows **“Music Information”** units, treat it as **bundled metering** on those routes until ED support maps the SKU → billing rule.

## “User Detailed Info” vs `/tt/user/posts`

This repo does **not** call a separately named “user detailed” endpoint. Creator flows use **`fetch_user_posts`** and **`fetch_post_info`**. If the dashboard attributes **“User Detailed Info (10 units)”** to traffic that correlates with `/tt/user/posts`, map that SKU to **`tt/user/posts`** in your pricing sheet (`ed-pricing-map.md`).

## Action

When ED provides an official SKU → endpoint matrix, paste it here and update `ED_UNIT_*` env defaults accordingly.
