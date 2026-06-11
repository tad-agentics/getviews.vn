# Product analysis — Handoff Marketing / Growth

> **Cập nhật 2026-06-11:** Product **không còn** tier Cơ bản/Chuyên sâu (video) hay Nhanh/Sâu (kênh). Một chất lượng phân tích duy nhất — video **2 credit**, kênh **3 credit**, không nhãn tier trong UI. Các file dưới giữ mô tả **as-built 2026-05** cho marketing handoff lịch sử; SSOT runtime: [`system-design.md`](../system-design.md) + [`changelog.md`](../changelog.md).

Bốn tài liệu **độc lập** (mỗi file đủ để đọc một mình): định nghĩa tính năng, hành trình user, **cách một bài phân tích được lắp ghép** (pipeline + block UI + prompt + metadata), skeleton ví dụ, copy rules.

| File | Tính năng | Credit (2026-06-11) |
|------|-----------|---------------------|
| [phan-tich-video.md](./phan-tich-video.md) | Mổ video TikTok (Win/Flop) | **2** / primary turn |
| [hoc-video-viral.md](./hoc-video-viral.md) | Học viral: URL · Pattern · browse | **2** URL · 0 browse/pattern |
| [soi-kenh-doi-thu.md](./soi-kenh-doi-thu.md) | Soi kênh @handle | **3** (quick-peek 0 credit) |
| [viet-kich-ban.md](./viet-kich-ban.md) | Kịch bản 6 cảnh | **3** |

**As-built (marketing handoff):** 2026-05 · Nguồn spec rộng: `artifacts/docs/feature-map-v1.md`.

**Prompt nguyên văn:** nhúng đầy đủ trong từng file (mục “Prompt synthesis — nguyên văn”) — không cần mở `gemini.py` hay repo backend. Khi eng đổi prompt production, re-sync section đó từ `diagnose_prompts.py` / `channel_diagnose_prompts.py` / `report_pattern_gemini.py` / `script_generate.py`.
