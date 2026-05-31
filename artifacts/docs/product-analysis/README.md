# Product analysis — Handoff Marketing / Growth

Bốn tài liệu **độc lập** (mỗi file đủ để đọc một mình): định nghĩa tính năng, hành trình user, **cách một bài phân tích được lắp ghép** (pipeline + block UI + prompt + metadata), skeleton ví dụ, copy rules.

| File | Tính năng | Cơ bản / Chuyên sâu | Credit |
|------|-----------|---------------------|--------|
| [phan-tich-video.md](./phan-tich-video.md) | Mổ video TikTok (Win/Flop) | `depth=basic` / `deep` | 1 / 2 |
| [hoc-video-viral.md](./hoc-video-viral.md) | Học viral: 1 URL (Win) · xu hướng tuần (Pattern) · thẻ công thức (browse) | Basic/Deep cho URL; Pattern không có depth | 1–2 / 0 browse |
| [soi-kenh-doi-thu.md](./soi-kenh-doi-thu.md) | Soi kênh @handle | Nhanh (0) / Sâu (3) | 0 / 3 |
| [viet-kich-ban.md](./viet-kich-ban.md) | Kịch bản 6 cảnh | Không có tier | 3 |

**As-built:** 2026-05 · Nguồn spec rộng: `artifacts/docs/feature-map-v1.md`.

**Prompt nguyên văn:** nhúng đầy đủ trong từng file (mục “Prompt synthesis — nguyên văn”) — không cần mở `gemini.py` hay repo backend. Khi eng đổi prompt production, re-sync section đó từ `diagnose_prompts.py` / `channel_diagnose_prompts.py` / `report_pattern_gemini.py` / `script_generate.py`.
