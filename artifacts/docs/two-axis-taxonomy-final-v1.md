# Two-axis taxonomy final — sign-off v1

**Status:** Wave T signed · Outcome A (14 active UX niches) · 2026-05-22  
**Wave T signed:** Tech Lead + PD · evidence below  
**Post-review fixes:** `20260823000003_taxonomy_feedback_fixes.sql` (legacy bridge doc, format_axis rename, lifestyle primary promotion)  
**Source of truth (code):** [`cloud-run/getviews_pipeline/two_axis_taxonomy.py`](../../cloud-run/getviews_pipeline/two_axis_taxonomy.py)  
**Audience:** Tech Lead, PD, backend/frontend agents

---

## T1 — UX creator niches (Outcome A: keep 14 active)

| # | slug | name_vn | Legacy bridge `niche_taxonomy.id` |
|---|------|---------|----------------------------------|
| 1 | beauty | Làm đẹp · Skincare | 2 |
| 2 | fashion | Thời trang · Phụ kiện | 3 |
| 3 | food | Ẩm thực · Ăn uống | 4 |
| 4 | lifestyle | Đời sống · Tâm sự | 27 |
| 6 | family | Nuôi con · Gia đình | 6 |
| 7 | education | Giáo dục · Sự nghiệp | 7 |
| 8 | tech_gaming | Công nghệ · Gaming | 8 |
| 9 | business | Kinh doanh · Tài chính | 5 |
| 10 | wellness | Sức khoẻ · Wellness | **26** |
| 11 | travel | Du lịch · Thể thao | 11 |
| 12 | auto | Ô tô · Xe máy | 12 |
| 14 | gym_fitness | Gym · Fitness | 14 |
| 15 | music_dance | Âm nhạc · Vũ đạo | 28 |
| 16 | real_estate | Bất động sản · Nhà đất | **10** |

**Legacy bridge note:** Representative `niche_taxonomy.id` for Phase C ingest bridge only (`legacyNicheIdForCreatorNiche()` in [`profileNiches.ts`](../../src/lib/profileNiches.ts)). Cohort analytics use `(content_class_id, creator_tier)` — not this column. **Wellness → 26**, **real_estate → 10** (distinct; prior doc typo had both as 10).

**Retirement map (20260728):**

| Retired slug | DB id | Action | Absorbed by |
|--------------|-------|--------|-------------|
| comedy | 5 | `active=false`, picker hidden | lifestyle (4) — skit, parody, react, dance, music_performance |
| pets_home | 13 | `active=false`, picker hidden | lifestyle (4) — pets + home decor junction edges |

Legacy ingest buckets 13/19/20 merged → `niche_taxonomy.id=27` (Đời sống · Tâm sự).

**Copy convention:** Vietnamese labels use middle dot `·` (not `/` or `&`). Slugs remain snake_case English.

**Rubric (VN persona):** 14 buckets cover Shopee affiliate (business), GRWM (beauty/fashion), BĐS tour (real_estate), mẹ bỉm (family), gym (gym_fitness) without overlap paralysis. No new UX niche in v1.

---

## T2 — Content classes (74 video + 5 carousel HI-16 = 79)

### Video classes (ids 1–74)

| # | slug | name_vn | format_axis | topic_axis |
|---|------|---------|-------------|------------|
| 1 | beauty_skincare_routine | Skincare routine | tutorial | beauty |
| 2 | beauty_makeup_tutorial | Makeup tutorial | tutorial | beauty |
| 3 | beauty_product_review | Review mỹ phẩm | review_unboxing | beauty |
| 4 | beauty_haul | Haul mỹ phẩm | review_unboxing | beauty |
| 5 | beauty_problem_solution | Vấn đề da & cách trị | pov_storytelling | beauty |
| 6 | fashion_outfit_styling | Outfit phối đồ | pov_storytelling | fashion |
| 7 | fashion_haul_shopping | Haul thời trang | review_unboxing | fashion |
| 8 | fashion_accessory_review | Phụ kiện review | review_unboxing | fashion |
| 9 | fashion_lookbook_montage | Lookbook montage | montage_highlights | fashion |
| 10 | fashion_thrift_secondhand | Thrift / đồ secondhand | vlog_daily | fashion |
| 11 | food_restaurant_review | Review quán ăn | pov_storytelling | food |
| 12 | food_street_food_vlog | Ăn vặt / street food | vlog_daily | food |
| 13 | food_recipe_tutorial | Công thức nấu ăn | tutorial | food |
| 14 | food_challenge | Food challenge | react_commentary | food |
| 15 | food_drinks_cafe | Đồ uống & cafe | review_unboxing | food |
| 16 | lifestyle_morning_routine | Morning / night routine | vlog_daily | lifestyle |
| 17 | lifestyle_daily_vlog | Daily vlog | vlog_daily | lifestyle |
| 18 | lifestyle_minimalism | Minimalism / dọn dẹp | tutorial | lifestyle |
| 19 | lifestyle_self_improvement | Self-improvement | talking_head_advice | lifestyle |
| 20 | storytelling_relationship | POV tình yêu / quan hệ | pov_storytelling | storytelling |
| 21 | storytelling_workplace | POV công sở | pov_storytelling | storytelling |
| 22 | storytelling_late_night | Tâm sự đêm khuya | pov_storytelling | storytelling |
| 23 | lifestyle_aesthetic | Lifestyle aesthetic | montage_highlights | lifestyle |
| 24 | comedy_skit_scripted | Hài skit kịch bản | skit_scripted | comedy |
| 25 | comedy_parody_satire | Parody / châm biếm | skit_scripted | comedy |
| 26 | comedy_observational | Hài quan sát relatable | pov_storytelling | comedy |
| 27 | comedy_react_response | React / response | react_commentary | comedy |
| 28 | music_cover_singing | Cover hát / âm nhạc | music_performance | music |
| 29 | music_dance_choreography | Dance / choreography | dance_choreography | music |
| 30 | parenting_baby_milestone | Mốc phát triển em bé | vlog_daily | family |
| 31 | parenting_mom_humor | Mẹ bỉm relatable | observational_relatable | family |
| 32 | parenting_dad_content | Bố nuôi con | vlog_daily | family |
| 33 | parenting_tips_advice | Mẹo nuôi dạy | talking_head_advice | family |
| 34 | family_vlog_daily | Family vlog | vlog_daily | family |
| 35 | edu_academic_explain | Giải thích học thuật | talking_head_advice | education |
| 36 | edu_language_lesson | Học ngoại ngữ | tutorial | education |
| 37 | edu_life_skill | Kỹ năng sống | tutorial | education |
| 38 | edu_career_advice | Hướng nghiệp / sự nghiệp | talking_head_advice | education |
| 39 | edu_book_review | Review sách / BookTok | talking_head_advice | education |
| 40 | tech_gadget_unboxing | Mở hộp gadget | review_unboxing | tech |
| 41 | tech_software_tutorial | Hướng dẫn phần mềm | tutorial | tech |
| 42 | gaming_gameplay | Gameplay / highlights | montage_highlights | gaming |
| 43 | gaming_review_commentary | Review game / commentary | talking_head_advice | gaming |
| 44 | gaming_esports_news | Esports / tin tức game | talking_head_advice | gaming |
| 45 | finance_personal_advice | Tài chính cá nhân | talking_head_advice | finance |
| 46 | finance_investment | Đầu tư / chứng khoán | talking_head_advice | finance |
| 47 | finance_business_story | Kinh doanh storytelling | pov_storytelling | finance |
| 48 | mmo_affiliate_education | MMO / Affiliate education | talking_head_advice | business |
| 49 | ecommerce_shopee_review | Review Shopee / gia dụng | review_unboxing | business |
| 50 | ecommerce_live_commerce | Livestream bán hàng | live_commerce | business |
| 51 | real_estate_listing | Listing bất động sản | vlog_daily | real_estate |
| 52 | wellness_mindfulness | Mindfulness / thiền | talking_head_advice | wellness |
| 53 | wellness_sleep_recovery | Giấc ngủ / phục hồi | talking_head_advice | wellness |
| 54 | wellness_nutrition | Dinh dưỡng & supplement | talking_head_advice | wellness |
| 55 | wellness_holistic | Lifestyle holistic | vlog_daily | wellness |
| 56 | fitness_gym_tutorial | Gym workout tutorial | tutorial | fitness |
| 57 | fitness_yoga_pilates | Yoga / Pilates | tutorial | fitness |
| 58 | fitness_calisthenics | Calisthenics / bodyweight | tutorial | fitness |
| 59 | fitness_outdoor_running | Chạy bộ / marathon | vlog_daily | fitness |
| 60 | travel_destination | Điểm đến du lịch | vlog_daily | travel |
| 61 | travel_food_tour | Du lịch ẩm thực | vlog_daily | travel |
| 62 | travel_tips_planning | Mẹo du lịch / lên kế hoạch | talking_head_advice | travel |
| 63 | travel_adventure | Phiêu lưu / outdoor | montage_highlights | travel |
| 64 | sports_event_highlight | Highlight thể thao | montage_highlights | sports |
| 65 | auto_car_review | Review xe ô tô | review_unboxing | auto |
| 66 | auto_moto_culture | Văn hoá moto | vlog_daily | auto |
| 67 | auto_modification | Mod xe / tuning | tutorial | auto |
| 68 | auto_news_industry | Tin tức ngành xe | talking_head_advice | auto |
| 69 | pets_cute_compilation | Pet cute / funny | montage_highlights | pets |
| 70 | pets_care_tips | Mẹo chăm pet | talking_head_advice | pets |
| 71 | pets_training | Huấn luyện pet | tutorial | pets |
| 72 | pets_owner_storytelling | POV chủ pet | pov_storytelling | pets |
| 73 | home_decor_inspiration | Decor / nội thất | montage_highlights | home |
| 74 | home_renovation_diy | Cải tạo / DIY | tutorial | home |

### Carousel classes (ids 75–79, HI-16)

| # | slug | name_vn | format_axis | topic_axis |
|---|------|---------|-------------|------------|
| 75 | carousel_format_tutorial | Carousel hướng dẫn | tutorial_carousel | carousel |
| 76 | carousel_format_listicle | Carousel list / tips | listicle_carousel | carousel |
| 77 | carousel_format_story | Carousel kể chuyện | story_carousel | carousel |
| 78 | carousel_format_comparison | Carousel so sánh | comparison_carousel | carousel |
| 79 | carousel_format_gallery | Carousel gallery | gallery_carousel | carousel |

**Seed:** video ids 1–74 in `20260510000004_two_axis_niche_pr1_schema.sql`; carousel ids 75–79 in `20260516190000_hi16_carousel_format_axis_junction.sql`.

---

## T3 — Niche ↔ class junction (14 active)

The UX axis (`creator_niches`) links to analysis classes (`content_classifications`) via **`creator_niche_content_classes`**. This is an **M:N** graph: one class can appear under multiple niches (cross-bucket browse), and one niche maps to many classes.

| Flag | Meaning |
|------|---------|
| **Primary** (`is_primary = true`) | Canonical home for that class — tie-break when HI-11 routes high-confidence assignments |
| **Secondary** (`is_primary = false`) | Cross-bucket browse edge — valid for corpus filter; does not override primary home |

**Browse / corpus filter:** FE loads **all** junction rows for the user's `creator_niche_id` — primary and secondary — without filtering on `is_primary` ([`corpusNicheFilter.ts`](../../src/lib/corpusNicheFilter.ts)).

**Morning Signal:** [`useClassMorningSignals`](../../src/hooks/useClassMorningSignals.ts) uses `fetchContentClassIdsForCreatorNiche(..., { primaryOnly: true })` so lifestyle creators are not diluted by 20+ secondary classes.

**Ingest (HI-11):** Runtime gate uses `(creator_niche_slug, format_axis)` pairs in `JUNCTION_NICHE_FORMAT_PAIRS` — 50 video + 70 carousel = **120** allowed combinations. The tables below are the **class-level** seed in SQL migrations.

**Carousel (HI-16):** Every active niche links to classes **75–79** (full 14×5 grid). Omitted from per-niche tables below — assume **+75–79** on each row.

**Migration lineage:** PR1 seed → PR6 (`music_dance` 15, `real_estate` 16) → `20260728000000` (comedy/pets_home → lifestyle) → `20260823000002` (Wave 4 secondary edges) → `20260823000003` (format_axis rename + lifestyle primary promotion).

### T3.1 — Known v1 trade-offs (documented exceptions)

| Topic | v1 decision | Wave 4+ backlog |
|-------|-------------|-----------------|
| `music_dance` thin (2 classes) | Canonical home for 28–29; accept thin cohort until corpus grows | Add lip-sync, reaction, artist vlog classes |
| `real_estate` single class | UX niche split from business (persona BĐS); cohort = class 51 only | Project review, market analysis classes |
| Lifestyle junction breadth | Browse = all edges; Morning Signal = **primary only** | Optional sub-lanes if signal quality still weak |
| Comedy / pets / home under lifestyle | 24–27, 69–74 promoted **primary** under lifestyle (20260823000003) | Dedicated UX niche only if density proves need |
| `ecommerce_live_commerce` (50) | Keeps `live_commerce` format_axis — short-form promo clips | Reframe to `ecommerce_live_promo` if ingest mislabels |
| VN gaps (KOS seller, flex, ASMR, duet/trend) | Not in v1 taxonomy | ACQE proposal queue → Wave 4 human approve |
| **Art & Craft (A)** | Gộp lifestyle + `home_*` / DIY classes | §T2.1 — `topic_axis` riêng khi density đủ |
| **Comedy & Skit (B)** | Classes 24–27 primary under lifestyle; UX comedy retired | §T2.1 — restore picker hoặc sub-lane nếu corpus chứng minh |
| **AI / Automation (C)** | Gộp `tech_gaming` / `business` | §T2.1 — class `ai_tool_workflow_*` khi trào lưu ổn định |

### beauty (id 1)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 1–5 | beauty_skincare_routine … beauty_problem_solution | ✓ |

### fashion (id 2)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 6–10 | fashion_outfit_styling … fashion_thrift_secondhand | ✓ |

### food (id 3)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 11–15 | food_restaurant_review … food_drinks_cafe | ✓ |
| 61 | travel_food_tour | secondary — food tour also surfaces under travel |

### lifestyle (id 4) — absorbs retired comedy (5) + pets_home (13)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 16–23 | lifestyle_morning_routine … lifestyle_aesthetic (+ storytelling POV 20–22) | ✓ |
| 24–27 | comedy_skit_scripted … comedy_react_response | ✓ — primary under lifestyle (ex-comedy) |
| 26 | comedy_observational (class slug) | ✓ — `format_axis = pov_storytelling`; not the observational format token |
| 28–29 | music_cover_singing, music_dance_choreography | secondary — canonical home is music_dance (15) |
| 49 | ecommerce_shopee_review | secondary — Wave 4; canonical home is business (9) |
| 69–74 | pets_cute_compilation … home_renovation_diy | ✓ — primary under lifestyle (ex-pets_home) |
| 73 | home_decor_inspiration | ✓ primary lifestyle; also secondary business (9) via Wave 4 |

### family (id 6)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 30–34 | parenting_baby_milestone … family_vlog_daily | ✓ |

### education (id 7)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 35–39 | edu_academic_explain … edu_book_review | ✓ |

### tech_gaming (id 8)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 40–44 | tech_gadget_unboxing … gaming_esports_news | ✓ |

### business (id 9)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 45–50 | finance_personal_advice … ecommerce_live_commerce | ✓ |
| 49 | ecommerce_shopee_review | secondary — Wave 4 affiliate overlap with lifestyle |
| 51 | real_estate_listing | secondary — Wave 4; canonical home is real_estate (16) |
| 73 | home_decor_inspiration | secondary — Wave 4 decor overlap with lifestyle |

### wellness (id 10)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 52–55 | wellness_mindfulness … wellness_holistic | ✓ |
| 57 | fitness_yoga_pilates | secondary — canonical home is gym_fitness (14) |

### travel (id 11)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 60–64 | travel_destination … sports_event_highlight | ✓ |
| 59 | fitness_outdoor_running | secondary — canonical home is gym_fitness (14) |
| 61 | travel_food_tour | secondary — also food (3) |

### auto (id 12)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 65–68 | auto_car_review … auto_news_industry | ✓ |

### gym_fitness (id 14)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 56–59 | fitness_gym_tutorial … fitness_outdoor_running | ✓ |
| 57, 59 | yoga_pilates, outdoor_running | also secondary under wellness (10) and travel (11) respectively |

### music_dance (id 15)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 28–29 | music_cover_singing, music_dance_choreography | ✓ — also secondary under lifestyle (4) for browse |

### real_estate (id 16)

| Class ids | Slugs | Primary |
|-----------|-------|---------|
| 51 | real_estate_listing | ✓ — also secondary under business (9) via Wave 4 |

### Cross-bucket classes (multi-niche)

| Class id | slug | Niches | Notes |
|----------|------|--------|-------|
| 49 | ecommerce_shopee_review | business (primary), lifestyle (secondary) | Shopee affiliate overlap |
| 51 | real_estate_listing | real_estate (primary), business (secondary) | BĐS listing vs finance bucket |
| 57 | fitness_yoga_pilates | gym_fitness (primary), wellness (secondary) | Mind-body crossover |
| 59 | fitness_outdoor_running | gym_fitness (primary), travel (secondary) | Marathon / outdoor culture |
| 61 | travel_food_tour | travel (primary), food (secondary) | Food tour dual home |
| 73 | home_decor_inspiration | lifestyle (primary), business (secondary) | Decor vlog vs affiliate home goods |
| 28–29 | music_* | music_dance (primary), lifestyle (secondary) | Entertainment absorbed into lifestyle browse |

**Junction contract:** 50 video `(creator_niche, format_axis)` pairs + 70 carousel pairs (14×5) = 120 union pairs — see `JUNCTION_NICHE_FORMAT_PAIRS` in `two_axis_taxonomy.py`. CI: `test_hi9_junction_seed.py`.

---

## T4 — Format axis vocabulary (video + carousel)

Canonical enum lives in [`two_axis_taxonomy.py`](../../cloud-run/getviews_pipeline/two_axis_taxonomy.py) (`FORMAT_AXIS_SLUGS`, `FORMAT_AXIS_VI`). **Distinct from class slug** — e.g. class 26 slug `comedy_observational` uses `format_axis = pov_storytelling`; class 31 uses `observational_relatable` (renamed from `comedy_observational` in `20260823000003`).

### Video format_axis (12 values)

| format_axis | Definition (VN) |
|-------------|-----------------|
| `tutorial` | Hướng dẫn từng bước (công thức, form tập, software, DIY) |
| `review_unboxing` | Review / mở hộp / đánh giá sản phẩm hoặc địa điểm |
| `pov_storytelling` | POV kể chuyện / trải nghiệm cá nhân |
| `montage_highlights` | Montage highlight, lookbook nhanh, compilation |
| `vlog_daily` | Vlog đời sống / travel / routine / tour |
| `react_commentary` | Reaction, commentary, challenge ăn uống |
| `talking_head_advice` | Talking head — lời khuyên, tài chính, góc nhìn chuyên gia |
| `music_performance` | Biểu diễn âm nhạc / cover hát |
| `dance_choreography` | Dance / choreography / dance challenge |
| `skit_scripted` | Skit kịch bản / parody có kịch bản |
| `live_commerce` | Livestream bán hàng / anchor giới thiệu deal (short-form promo clips) |
| `observational_relatable` | Hài quan sát / relatable (kể cả mẹ bỉm humor) — **not** class slug |

### Carousel format_axis (5 values, HI-16)

| format_axis | Definition (VN) |
|-------------|-----------------|
| `tutorial_carousel` | Carousel hướng dẫn từng bước slide-by-slide |
| `listicle_carousel` | Carousel list / tips nhiều slide |
| `story_carousel` | Carousel kể chuyện / narrative vuốt |
| `comparison_carousel` | Carousel so sánh / before-after |
| `gallery_carousel` | Carousel gallery / moodboard aesthetic |

**T2 checklist outcomes:**

| Check | Result |
|-------|--------|
| Coverage matrix topic×format | 74 video cells populated; sparse cells intentional (e.g. real_estate × tutorial deferred) |
| Corpus density | Class-first cohort usable; thin classes gated by `claim_tier` |
| Junction sanity | 99,67% valid (22 rows triaged — see `junction-invalid-triage-v1.json`) |
| VN gaps | Shopee review → `ecommerce_shopee_review`; GRWM → beauty/fashion montage; BĐS vs home decor → separate topic axes (`real_estate` vs `home`) |

### T2.1 — Vùng lõm cố ý (intentional sparse cells) & gap nội dung lớn

Ma trận `topic_axis × format_axis` **cố ý không phủ kín** — một số ô trống là quyết định sản phẩm, không phải oversight. Ví dụ đã ghi trong checklist: **`real_estate × tutorial` deferred** (ngách BĐS chưa có class hướng dẫn từng bước riêng).

Dưới đây là **3 mảng nội dung lớn** hiện bị khuyết hoặc gộp chung — **Wave 4+ hoặc sau 2026**, chỉ promote khi ACQE/corpus density chứng minh need (không auto-add junction):

#### A. Nghệ thuật / Thủ công / DIY (Art & Craft)

| | |
|---|---|
| **Thực trạng VN** | Vẽ tranh, handmade, thêu, gốm, đồ họa 3D… phát triển mạnh; Save/Share cao (Minh Save). |
| **v1 mapping** | Gộp tạm vào UX **`lifestyle`** (4) + class `home_decor_inspiration` (73), `home_renovation_diy` (74), `lifestyle_minimalism` (18). |
| **Gap** | Không có **`topic_axis` riêng** cho Art/Craft — cohort benchmark bị dilute với decor nhà / routine đời sống. |
| **Wave 4+ trigger** | User picker demand + ≥N videos/class 30 ngày với hook Save-driven; candidate: `topic_axis = art_craft` + classes `art_process_tutorial`, `craft_handmade_montage`. |

#### B. Vlog hài tình huống / Kịch bản ngắn (Comedy & Skit)

| | |
|---|---|
| **Thực trạng VN** | POV hài đóng vai, skit tình huống (Welax, 1977 Vlog, hài độc thoại) — view volume rất lớn. |
| **v1 mapping** | UX niche **`comedy` retired** → classes **24–27** (`comedy_skit_scripted` … `comedy_react_response`) primary dưới **`lifestyle`** (4). Instructiveness rank ưu tiên nội dung có cấu trúc học hỏi → hài giải trí thuần bị nén. |
| **Gap** | Creator chuyên hài **không có UX bucket riêng**; diagnosis cohort trộn với morning routine / self-improvement. |
| **Wave 4+ trigger** | Corpus share comedy-format ≥X% trong lifestyle junction; hoặc PD quyết restore picker `comedy` nếu persona tách rõ khỏi "Đời sống · Tâm sự". |

#### C. AI & Công nghệ chuyển đổi số (AI / Automation)

| | |
|---|---|
| **Thực trạng VN** | Video hướng dẫn dùng AI (Gemini, ChatGPT, Midjourney) kiếm tiền, tự động hóa workflow — trào lưu tăng nhanh. |
| **v1 mapping** | Gộp vào **`tech_gaming`** (8) — class `tech_software_tutorial` (41) — hoặc **`business`** (9) — `mmo_affiliate_education` (48). |
| **Gap** | "Video thực hành công cụ AI ngắn" **≠** review gadget **≠** khóa MMO/affiliate; hook, CTA, và conversion mechanism khác hẳn. |
| **Wave 4+ trigger** | Distinct class ví dụ `ai_tool_workflow_tutorial` (`topic_axis = ai_automation`, `format_axis = tutorial`); junction `(tech_gaming \| business, …)` sau human approve. |

**Nguyên tắc promote:** Mọi mở rộng trên đi qua **Wave T sign-off → migration → `test_hi9_junction_seed`** — không bypass TD-6.

### T2.2 — Phase 2 resilience (algorithm drift, creative friction, active learning)

Ba hướng cải tiến **đã scaffold** — không auto-promote vào taxonomy prod.

#### 1. Algorithm drift defense (ACQE)

| | |
|---|---|
| **Vấn đề** | Closed enum 79 class + 12 `format_axis` — format mới bị ép vào cell cũ → benchmark lệch. |
| **Không làm** | `content_class_id = unclassified_unknown` trên MV chính (phá cohort stats). |
| **v1 scaffold** | ACQE `_export_taxonomy_drift_candidates()` — gom cluster junction-invalid + breakout cao + `subject_matter` sample → artifact [`taxonomy-drift-candidates.json`](../qa-reports/taxonomy-drift-candidates.json). Alert khi drift_rate ≥ **5%** / 7 ngày. |
| **Wave 4+** | PD review cluster → đề xuất class/junction mới (giống junction proposal queue). |

#### 2. Creative friction — Morning Signal (FE v0)

| | |
|---|---|
| **Vấn đề** | Morning Signal chỉ trả lời “quay gì” bằng velocity — không xét burnout creator. |
| **v1 scaffold** | `productionFriction.ts` — heuristic `format_axis` → `low`/`mid`/`high`. Toggle **Quay nhẹ hôm nay** / **Tràn năng lượng** trên `MorningSignalStrip` — filter trước Max-2-Card. |
| **Wave 4+** | Cột `production_friction` trên `content_classifications` (79 rows) sau PD map. |

#### 3. Active learning — hook caption markers (ACQE)

| | |
|---|---|
| **Vấn đề** | `_HOOK_MARKERS` regex hard-code trong `corpus_instructiveness.py` — teencode VN lạc hậu nhanh. |
| **Không làm** | Auto-append regex vào Python mỗi đêm (không audit, không TD-7 test). |
| **v1 scaffold** | ACQE `_export_hook_marker_candidates()` — Tier-2 caption vs Tier-3 `hook_type` mismatch, phrase lặp ≥3 video → [`hook-marker-candidates.json`](../qa-reports/hook-marker-candidates.json). |
| **Wave 4+** | Human approve → merge markers (DB table hoặc reviewed artifact), không sửa code trực tiếp. |

---

## Sign-off

| Role | Decision | Date |
|------|----------|------|
| Tech Lead | Outcome A — keep 14 active UX niches; exceptions in §T3.1 | 2026-05-22 |
| PD | Label/copy freeze + format_axis rename observational_relatable | 2026-05-22 |

**Wave T signed:** 2026-05-22 — taxonomy frozen for v1; junction-invalid triage queued for Wave 1a/4.

### Evidence artifacts

| Artifact | Purpose |
|----------|---------|
| [`two-axis-taxonomy-audit.json`](../qa-reports/two-axis-taxonomy-audit.json) | Code-truth counts (14 niches, 79 classes, 120 junction pairs); parity checks |
| [`junction-invalid-triage-v1.json`](../qa-reports/junction-invalid-triage-v1.json) | Wave 1a — 22-row decision tree (reclassify vs defer Wave 4) |
| [`20260823000003_taxonomy_feedback_fixes.sql`](../../supabase/migrations/20260823000003_taxonomy_feedback_fixes.sql) | Post-review: wellness bridge, observational_relatable rename, lifestyle primary 24–27/69–74 |
| [`wave-t-baseline.json`](../qa-reports/wave-t-baseline.json) | QA gate baseline — Wave T formal sign-off |

**Wave 4 gate:** Junction expansion only for rows marked `defer_wave4` in triage artifact after human review.
