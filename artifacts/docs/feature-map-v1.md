# Product Vision V1 — GetViews.vn

**Version:** 2.0 — **FINAL (GTM scope)**  
**Last updated:** 2026-05-22  
**Codebase ref:** `8969f3e`  
**Status:** Product vision **đã chốt** cho launch — lược giản so với as-built; **freeze UI** hai surface browse (Studio gợi ý + Xu hướng công thức/kho); phần còn lại = build/align (video depth, billing, handoff)

> **Pivot SSOT (2026-05-21+, prod defaults ON):** Class-first ingest/browse/benchmark — [`system-design.md`](system-design.md) §9. **`content_class_intelligence`** + tier/stats MVs canonical; legacy `niche_intelligence` refresh **skipped** in prod (bridge only for unmigrated percentile paths).

**Related docs:**

| Doc | Role |
|-----|------|
| [`feature-map.md`](feature-map.md) | Inventory as-built + **Post-V1 backlog** — synced `8969f3e` |
| [`two-axis-niche-model.md`](two-axis-niche-model.md) | Taxonomy SSOT (16 niches × 82 classes, junction, MV chain) |
| [`product-value-audit.md`](product-value-audit.md) | Value → data audit, gaps, PVA backlog |
| [`corpus-gemini-utilization-audit.md`](corpus-gemini-utilization-audit.md) | Extract field tiers, trim rules |
| [`data-utilization-map-v1.md`](data-utilization-map-v1.md) | **FIELD × feature** matrix (F1–F8 + Studio) — pre-implement gate |
| [`system-design.md`](system-design.md) | Architecture, invariants TD-1–TD-7 — **sync §4.12** khi ship depth/cache |
| [`emotional-design-system.md`](emotional-design-system.md) | Persona Minh, tone, authority |
| [`bao-cao-flop-video-kenh-toan-dien-v5.md`](bao-cao-flop-video-kenh-toan-dien-v5.md) | Taxonomy flop (§1.8 Seeding & Ads) — signal engineering reference |

**Maintenance:** Chỉ ghi **trong V1** ở file này. Cắt khỏi V1 → **xóa** khỏi vision doc, **thêm** dòng vào [`feature-map.md`](feature-map.md) § Post-V1 backlog. Khi ship: cập nhật cùng commit (1) vision, (2) `feature-map.md`, (3) [`system-design.md`](system-design.md), (4) [`changelog.md`](changelog.md).

---

## 1. North star V1

> Thay phần lớn thời gian doomscroll bằng **Creator Studio**: **gợi ý quay hôm nay** + **công thức/kho video** đã có sẵn, rồi **khám video/kênh** (cơ bản hoặc chuyên sâu) và **kịch bản** — mọi insight dùng **cùng một lớp extract corpus**, không pipeline rời.

**Ba câu hỏi sản phẩm (GTM):**

1. *Hôm nay nên quay gì?* → **Tab Studio** — khối **Gợi ý hôm nay** (3 tầng, §3.1) + **Tab Xu hướng** — công thức viral + kho video (§3.2)  
2. *Làm như thế nào?* → Script Studio (pill) + video/kênh **Cơ bản**  
3. *Tại sao video trước flop / video kia chạy?* → Video **Chuyên sâu** + kênh **Sâu** (composer pills)  

### 1.1 V1 launch freeze (đã chốt — giữ nguyên UI as-built)

Hai surface **browse** không reshape cho GTM — chỉ fix handoff / billing / depth ở luồng phân tích:

| Surface | Route | **Giữ nguyên V1** | **V1 build** (không đổi layout freeze) |
|---------|-------|-------------------|----------------------------------------|
| **Studio** | `/app` | **Gợi ý hôm nay** — 3 tầng [`HomeSuggestionsToday.tsx`](../../src/routes/_app/home/components/HomeSuggestionsToday.tsx): I Hôm nay quay ngay · II Công thức nền · III Cảm hứng | Composer **4 pill** + Cơ bản/Chuyên sâu; URL-only; §4 |
| **Xu hướng** | `/app/trends` | **Công thức từ video viral trong ngách** [`TrendsPatternGrid`](../../src/routes/_app/trends/TrendsPatternGrid.tsx) + **Kho video** [`ExploreScreen`](../../src/routes/_app/trends/ExploreScreen.tsx) § II | Card → Answer: `depth=basic&mode=win&from=trends` (§4.10) |

**Không yêu cầu V1:** segment TikTok/Douyin riêng trên Xu hướng; duplicate “Hôm nay” trên Trends; reshape F6. Các block phụ (âm thanh, `TrendsDouyinCard`, `TrendsRail`, `CrossNicheBreakoutLane`, thesis hero) — **giữ nếu code đã có**, không block launch → [`feature-map.md`](feature-map.md) § Post-V1.

---

## 2. V1 scope — năm mục tiêu → năm trụ

| # | Mục tiêu kinh doanh | Trụ V1 | Surface chính |
|---|---------------------|--------|----------------|
| 1 | Phân tích video flop/win — **cơ bản + chuyên sâu** | **Video Intelligence** | Tab Studio — pill Khám Video flop / win |
| 2 | Phân tích kênh creator — **cơ bản + chuyên sâu** | **Channel Intelligence** | Tab Studio — pill Khám Kênh |
| 3 | Corpus + công thức ngách — thay doomscroll | **Xu hướng** | Tab Xu hướng — công thức + kho video (§3.2, freeze) |
| 4 | Kịch bản chi tiết để quay | **Script Studio** | Tab Studio — pill Tạo kịch bản |
| 5 | Data extract & utilize **đều** cho mọi feature trên | **Data plane** | Ingest + batch + claim tiers; pre-launch gate §8.6–§8.7 |

```mermaid
flowchart TB
  subgraph data [Tru5_DataPlane]
    EX[1x_Gemini_extract]
    PROM[promoted_columns]
    AGG[batch_aggregates]
  end
  subgraph v1 [V1_Surfaces]
    V[Video_BasicDeep]
    CH[Channel_BasicDeep]
    TR[Xu_huong]
    SC[Script_Studio]
  end
  EX --> PROM --> AGG
  PROM --> V
  PROM --> CH
  AGG --> TR
  PROM --> SC
  TR --> SC
  V --> SC
```

---

## 3. Navigation V1 — Creator Studio (2 tab)

**Platform:** **Creator Studio** (giữ shell / brand hiện tại). V1 **không** tách thành nhiều app — gom dưới **hai tab cấp 1**. Bốn trụ sản phẩm (§2) vẫn giữ; khác ở **cách user điều hướng**.

**Landing mặc định (đã chốt):** Sau đăng nhập / mở app → **Tab Studio** (composer + 4 pill). **Không** mở thẳng Tab Xu hướng hay `/app/trends`. User sang Xu hướng bằng tab cấp 1 (1 tap). Route gốc authenticated: `/app` → shell Studio; Xu hướng: `/app/trends` (hoặc alias tương đương trong layout).

```mermaid
flowchart TB
  open[Mở_app] --> ST
  subgraph cs [Creator_Studio]
    ST[Tab_Studio_default]
    XH[Tab_Xu_huong]
  end
  subgraph pills [Studio_composer_pills]
    P1[Khám_Video_flop]
    P2[Khám_Video_win]
    P3[Khám_Kênh]
    P4[Tạo_kịch_bản]
  end
  subgraph xh [Xu_huong_freeze]
    X1[Cong_thuc_viral]
    X2[Kho_video]
  end
  ST --> pills
  XH --> xh
  pills --> depth[Cơ_bản_·_Chuyên_sâu_trong_composer]
```

### 3.1 Tab Studio (`/app`)

**Trang mặc định sau đăng nhập** — TopBar “Sảnh Sáng Tạo” ([`HomeScreen.tsx`](../../src/routes/_app/home/HomeScreen.tsx)).

#### 3.1.1 Gợi ý hôm nay — **freeze UI (V1)**

Giữ nguyên khối **GỢI Ý HÔM NAY** — 3 tầng, không reshape layout/copy ladder:

| Tầng | Tag | Nội dung | Component |
|------|-----|----------|-----------|
| **I** | HÔM NAY QUAY NGAY | Morning Signal (format đang nổi) + 3 kịch bản ritual | [`MorningSignalStrip`](../../src/routes/_app/home/components/MorningSignalStrip.tsx) (`useClassMorningSignals` → `content_class_intelligence` MV, primary junction; energy toggle [`productionFriction.ts`](../../src/lib/productionFriction.ts)) + [`StudioHero`](../../src/routes/_app/home/components/StudioHero.tsx) (`GET /home/daily-ritual`) |
| **II** | CÔNG THỨC NỀN | Hook/pattern đứng sau gợi ý | [`HooksTable`](../../src/routes/_app/home/components/HooksTable.tsx) embedded (`useTopPatterns`) |
| **III** | CẢM HỨNG | 3 video breakout **trong ngách** (creator khác) | [`BreakoutGrid`](../../src/routes/_app/home/components/BreakoutGrid.tsx) (`useTopBreakouts` — `content_class_id IN` junction) → link `/app/trends` |

*Layout freeze preserved — Wave 3a/3b added sub-blocks inside existing tiers, no reshape.*

Tier III = within-niche teaser → Tab Xu hướng (kho + công thức đầy đủ). **Cross-format** inspiration = `CrossNicheBreakoutLane` on Trends only (§3.2.2) — **không** duplicate ritual trên Trends.

#### 3.1.2 Composer + pills — **V1 build**

Giữ shell composer hiện tại; đổi **pill** thành **4 mục** (thay chip/intent tự do):

| Pill (tiếng Việt) | Job | Route / surface | Ghi chú |
|-------------------|-----|-----------------|--------|
| **Khám Video flop** | Vì sao video flop, fix nhanh | `/app/answer` (video) | Preset `mode=flop` khi submit từ pill này |
| **Khám Video win** | Vì sao video chạy, công thức tái tạo | `/app/answer` (video) | Preset `mode=win` |
| **Khám Kênh** | Soi kênh @handle | `/app/channel` | F4 Chuyên sâu / F5 Nhanh — §5 |
| **Tạo kịch bản** | Kịch bản đủ quay | `/app/script` | F7 |

**Composer (luôn visible trong Tab Studio):**

- Input theo pill: URL TikTok (video flop/win), `@handle` (kênh), hoặc flow script (kịch bản) — **không** câu hỏi tự do / follow-up (§4.10.1).
- **Hai nút Cơ bản / Chuyên sâu** trong composer — user chọn `analysis_depth` **trước** khi khám **video hoặc kênh** (§4.11.2, §10 billing).
- Pill flop/win **chỉ đặt framing** (`report.mode`); depth **độc lập** qua nút composer.

### 3.2 Tab Xu hướng (`/app/trends`)

Tab riêng — **không** gộp pill Studio. TopBar as-built: “Xu Hướng Tuần Này” ([`ExploreScreen.tsx`](../../src/routes/_app/trends/ExploreScreen.tsx)).

#### 3.2.1 Hai khối chính — **freeze UI (V1)**

| # | Tiêu đề user-facing | Phần | Component | Data |
|---|---------------------|------|-----------|------|
| **1** | **Công thức từ video viral trong ngách** | Phần I — Pattern | [`TrendsPatternGrid`](../../src/routes/_app/trends/TrendsPatternGrid.tsx) + `PatternModal` | `useTopPatterns`, `video_patterns` |
| **2** | **Kho video** (kicker `II — KHO VIDEO`) | Tìm trong corpus + filter | `ExploreScreen` grid + `ExploreCorpusVideoModal` | `video_corpus`, `applyVideoCorpusNicheFilter` (`content_class_id IN` junction), `useContentClassIntelligence` (thin banner) |

**CTA V1 (build, không đổi 2 khối trên):** tap tile / breakout / “Giải mã” → `/app/answer?q=…&depth=basic&mode=win&from=trends` (§4.10).

#### 3.2.2 Phụ trên trang — giữ as-built, không gate launch

| Block | V1 |
|-------|-----|
| `TrendsNichePills`, `TrendsPatternThesisHero` | ✅ Giữ |
| `TrendingSoundsSection`, `TrendsDouyinCard` | ✅ Giữ — **không** bắt buộc QA segment Douyin |
| `CrossNicheBreakoutLane` | ✅ Shipped (Wave 3b) — cap 3, `content_class_id NOT IN` junction; distinct from Home Tier III |
| `TrendsRail` (desktop) | ✅ Giữ — `ingest_loop_niche_id` within-niche list; may overlap Home Tier III data |
| Segment cấp 1 **TikTok \| Douyin** | ❌ **Không** ship requirement — Post-V1 |

**Ritual “hôm nay quay gì”** chỉ ở **Studio §3.1.1** — không thêm block ritual trên Xu hướng cho V1.

### 3.3 Map trụ sản phẩm → navigation

| Trụ (§2) | Tab | Điểm vào |
|----------|-----|----------|
| Video Intelligence | **Studio** | Pill Khám Video flop · Khám Video win |
| Channel Intelligence | **Studio** | Pill Khám Kênh |
| Script Studio | **Studio** | Pill Tạo kịch bản |
| Xu hướng | **Xu hướng** | Công thức + Kho video (§3.2.1) |
| Data plane | — | `/batch/*`, ingest (không user-facing) |

---

## 4. Trụ 1 — Video Intelligence (flop / win)

### 4.0 Nguyên tắc: cùng V6 (salient), khác số block

**Cơ bản và Chuyên sâu dùng chung một kiến trúc** — không tách prompt legacy vs v6, không extract lần hai:

```mermaid
flowchart LR
  extract[1x_Gemini_extract]
  manifest[build_signal_manifest]
  pick[select_sections_to_emit]
  synth[synthesize_diagnosis_v6]
  render[DiagnosisSectionRenderer]
  extract --> manifest --> pick --> synth --> render
```

| Lớp | Cơ bản & Chuyên sâu |
|-----|---------------------|
| Extract | Cùng `analysis_json` + promoted columns (corpus hoặc on-demand) |
| Signals | Cùng `build_signal_manifest` — **Chuyên sâu** đưa nhiều signal hơn vào synthesis (§4.8) |
| Synthesis | Cùng `synthesize_diagnosis_v6_section_pool` + schema `diagnosis_vi` |
| UI | Cùng `VideoBody` — render theo `sections[]` trong payload |

**Hai trục độc lập (V1):** Win vs Flop **không** fork pipeline; **Cơ bản vs Chuyên sâu** cũng không. Kết hợp tạo bốn ô sản phẩm (§4.1).

| Trục | Field | Ai set | Ảnh hưởng |
|------|--------|--------|-----------|
| **Depth** | `analysis_depth` ∈ `basic` \| `deep` | User (default theo entry §4.10) | Whitelist §4.2, cap signal 3/5 (§4.8), billing 1×/2× (§10), **cache** `(video_id, analysis_depth)` |
| **Framing** | `report.mode` `win` \| `flop` + `performance_tier` `hit` \| `flop` \| `average` \| `unknown` | Query heuristics ([`report_video.py`](../../cloud-run/getviews_pipeline/report_video.py)) + corpus refine | Title `diagnosis`, `extract_video_errors` mode, FE chrome [`VideoBody.tsx`](../../src/components/v2/answer/video/VideoBody.tsx), salience signal Win (§4.8.3 `tier_gate=hit`) |

**Khác biệt depth (V1):** `analysis_depth` điều khiển **danh sách `section_id` đưa vào `SECTIONS_TO_EMIT`** trước khi gọi Gemini.

- **Cơ bản** ≈ V6 “đủ dùng hàng ngày” — **whitelist** ~5 khối (Win & Flop **cùng** whitelist).  
- **Chuyên sâu** = mọi block applicable + `boost_attribution` khi có signal §4.7.

**Không pipeline Win riêng** — cùng `extract` → `build_signal_manifest` → `select_sections_to_emit` → `synthesize_diagnosis_v6`. Chi tiết JTBD Win: §4.9.

Code hiện tại ([`diagnose_sections.py`](../../cloud-run/getviews_pipeline/diagnose_sections.py)): một đường, độ dài **đã biến thiên** theo salience ≈ Chuyên sâu, chưa có `analysis_depth` product param. Cache as-built: **một row / `video_id`** ([`video_analyze.py`](../../cloud-run/getviews_pipeline/video_analyze.py) L1551–1556) — V1: §4.12.

### 4.1 Định nghĩa hai mức depth + ma trận Win/Flop

#### 4.1.1 Depth (Cơ bản vs Chuyên sâu)

| | **Cơ bản** | **Chuyên sâu** |
|---|------------|----------------|
| **Use case (chung)** | Verdict + hook + ngách + bước tiếp — thay doomscroll / FYP stop | Brief, agency, video phức tạp (commerce, sound, editing…) |
| **Cấu trúc báo cáo** | **V6** — cùng section components | **V6** — nhiều block hơn |
| **Section policy** | Whitelist sau `applies()` (§4.2) | Full [`select_sections_to_emit`](../../cloud-run/getviews_pipeline/diagnose_sections.py) |
| **Số block điển hình** | ~3–5 (`diagnosis` + `next_video` luôn có) | ~5–12 |
| **Extract** | Cùng 1 lần | Cùng 1 lần — **không** re-extract khi đổi depth |
| **Cache key (V1)** | `(video_id, analysis_depth=basic)` | `(video_id, analysis_depth=deep)` — **không** share payload |
| **Billing (§10)** | **1×** `decrement_credit` | **2×** |
| **Trạng thái code** | 🔨 V1 build | ◐ Partial ≈ default hôm nay |

#### 4.1.2 Ma trận sản phẩm (depth × framing)

| | **Cơ bản** | **Chuyên sâu** |
|---|------------|----------------|
| **Win** (`mode=win` / tier `hit`) | **JTBD Xu hướng:** “vì sao chạy + quay tiếp” — default entry Trends (§4.10) | Brief viral, agency, công thức tái tạo (sound, editing, persona…) |
| **Flop** (`mode=flop` / tier `flop`) | Paste “vì sao flop” — verdict + hook + fix nhanh | Audit đầy đủ + `boost_attribution` (§4.7) khi suspect ads/seeding |

**Ghi chú:** `performance_tier` do metric (views vs ngách, channel context); `report.mode` có thể lệch tier khi user hỏi “vì sao flop” về video views cao — BE ưu tiên query `mode` khi explicit (§4.10).

### 4.2 Whitelist Cơ bản (đã chốt)

**Áp dụng cho cả Win và Flop** — cùng `BASIC_SECTION_ALLOWLIST`; khác **copy** trong section `diagnosis` / CTA (theo `report.mode` + `performance_tier`), không khác whitelist.

**Compliance:** giữ trong whitelist khi `applies()` (an toàn pháp lý). *Tùy chọn V1.1:* ẩn `compliance` khỏi Win Basic khi không flag — chỉ nếu product muốn rút gọn doomscroll hơn nữa (§15).

Sau khi chạy `select_sections_to_emit` như hiện tại, **giữ lại** (theo `display_order`):

| `section_id` | Luôn / có điều kiện | Lý do V1 |
|--------------|---------------------|----------|
| `diagnosis` | Luôn (`always_emit`) | Verdict Win/Flop + fix — Q3 core |
| `compliance` | Khi `applies` (flags / manifest) | Rủi ro pháp lý — không ẩn ở bản rẻ |
| `hook_analysis` | Khi salience ≥ 0.7 | Pay-signal hook |
| `niche_pattern` | Khi có `reference_videos` | Benchmark ngách + refs |
| `next_video` | Luôn (`always_emit`) | Cầu nối Q1 → Script Studio |

**Không có trong Cơ bản** (chỉ Chuyên sâu): `distribution`, `boost_attribution`, `douyin_origin`, `channel_pattern`, `commerce`, `metadata`, `editing`, `sound`, `persona`, `script_structure`.

**Upsell UX (đề xuất):** sau Cơ bản, hiển thị teaser các section bị khóa (“Âm thanh”, “Editing”, “Douyin”…) từ manifest — không synthesize sẵn cho đến khi user chọn Chuyên sâu.

**Implementation sketch:**

```python
# diagnose_sections.py — V1
BASIC_SECTION_ALLOWLIST = frozenset({
    "diagnosis", "compliance", "hook_analysis", "niche_pattern", "next_video",
})

def select_sections_to_emit(manifest, ctx, *, depth: str = "basic") -> list[str]:
    full = _select_sections_full(manifest, ctx)  # logic hiện tại
    if depth == "deep":
        return full
    return [s for s in full if s in BASIC_SECTION_ALLOWLIST]
```

### 4.3 Chuyên sâu — full pool + signal dày

- Gọi `select_sections_to_emit(..., depth="deep")` → **không** lọc whitelist.  
- Mỗi section trong [`SECTION_POOL`](../../cloud-run/getviews_pipeline/diagnose_sections.py) vẫn phải pass `applies()` + ngưỡng salience riêng (vd. `editing` ≥ 0.4, `hook_analysis` ≥ 0.7).  
- **Độ dày nội dung:** không chỉ thêm section — xem **§4.8** (signal backlog + `manifest_for_prompt` khi `depth=deep`).  
- **Tùy chọn V1:** `GETVIEWS_DEEP_RELAX_SALIENCE=1` hạ `SECTION_EMIT_THRESHOLD` 0.5→0.45 **chỉ** khi deep.  
- Thin niche: vẫn áp dụng `claim_tiers` + `ConfidenceStrip` — deep không được phép bịa số.

### 4.4 Feature IDs

| ID | Tên | Tier | Trạng thái | Evidence (as-built) |
|----|-----|------|------------|---------------------|
| **F1** | Phân tích video Chuyên sâu | Deep | ◐ Partial | `build_video_report` → v6; hiện = default single depth |
| **F2** | Phân tích video Cơ bản | Basic | 🔨 V1 build | Whitelist §4.2 + `analysis_depth` + cache partition |

### 4.5 Luồng người dùng

Chi tiết entry, query params, UI: **§4.10–§4.11**.

```mermaid
flowchart TD
  tabXH[Tab_Xu_huong_CTA] -->|depth=basic_mode=win| answer[/app/answer]
  studio[Tab_Studio_pills] --> picker[Nut_Co_ban_Chuyen_sau]
  studio --> answer
  picker -->|basic_or_deep| answer
  answer --> basicReport[Bao_cao_Co_ban]
  basicReport --> upsell[CTA_Chuyen_sau_+_teaser]
  upsell -->|2x_credit| deepReport[Bao_cao_Chuyen_sau]
```

1. **Tab Xu hướng** (TikTok) → CTA card → Answer `basic` + `win` (§4.11.4).  
2. **Tab Studio** → pill flop/win/kênh + nút **Cơ bản** / **Chuyên sâu** trong composer trước submit.  
3. **Cơ bản** → V6 whitelist; CTA “Phân tích chuyên sâu” + teaser manifest (§4.2).  
4. **Chuyên sâu** → cùng `AnswerScreen` / `VideoBody`, full pool — **phiên mới** cùng URL (`depth=deep`), không phải follow-up turn.

**V1 — không follow-up:** Một phiên video = **một báo cáo**; không hỏi thêm trong Answer sau khi có kết quả. Chi tiết §4.10.1.

### 4.6 Data contract (Trụ 5)

| Field / aggregate | Cơ bản | Chuyên sâu |
|-------------------|--------|------------|
| `build_signal_manifest` (full) | ✓ tính; prompt cap 3/section | ✓ tính + emit full; cap 5/section (§4.8) |
| `analysis_depth` | `basic` | `deep` |
| `source_entry` | `trends` \| `trends_douyin` \| `composer` \| `evidence` | echo trong `answer_turns.payload` |
| `hook_effectiveness`, refs, `performance_tier` | ✓ trong whitelist sections | ✓ |
| `embedded_tiles` | ✓ trong `niche_pattern` khi có refs | ✓ + section khác |
| Sections: sound, editing, commerce, douyin, … | manifest có, **không synthesize** | synthesize khi `applies` |
| On-demand extract | khi chưa corpus | khi chưa corpus |
| Đổi depth (basic→deep) | **không** re-extract; cache miss deep → **synthesis-only** (manifest đã có) | |
| Cache `video_diagnostics` | row `(video_id, basic)` | row `(video_id, deep)` — §4.12 |
| `boost_attribution`, `reference_eligible` | đọc khi có; không section riêng | section + lọc ref (§4.7) |
| Win signals (§4.8.3) | salience cao khi `tier=hit`; vẫn tính trong manifest | synthesize nếu section emit |

### 4.7 Boost attribution & corpus reference hygiene (V5 §1.8)

**Vấn đề:** Báo cáo flop V5 mô tả Seeding / Spark Ads / seeding mồi là “con dao hai lưỡi”. Pipeline hiện tại **không** phân biệt view organic vs view đẩy trả phí → benchmark và chẩn đoán có thể lệch.

**Ràng buộc V1 (đã chốt):**

| Không làm | Lý do |
|-----------|--------|
| TikTok OAuth / Analytics / Ads API | Ngoài scope sản phẩm |
| UI khai báo “đã chạy ads/seeding” | Không đưa trách nhiệm lên user |
| Khẳng định **100%** (“chắc chắn đã chạy ads”, “đã seeding”) | Không có cờ promoted; inference có thể sai |

**Chỉ làm:** inference **tự động** từ dữ liệu đã có hoặc sẽ thu thập thêm trong batch (EnsembleData stats, corpus phân vị, optional time-series snapshot).

#### 4.7.0 Ngôn ngữ nhận định (copy contract)

**Được phép:** nhận định **có căn cứ số đo**, dùng *“có dấu hiệu”* / *“khó coi là viral organic thuần”* / *“nhiều khả năng view đến từ ads hoặc seeding vì …”* — kèm views, comments, ER, so với median/p90 ngách.

**Không được:** tuyệt đối hóa; bịa metric chỉ có trên TikTok Analytics (FYP %, organic sau campaign, demographics Ads).

| `evidence_strength` | Điều kiện (M1/M3) | Cách nói (ví dụ) |
|---------------------|-------------------|------------------|
| `weak` | `suspect_low` | *“View cao hơn trung vị ngách nhưng ER thấp hơn p25 — cần xem thêm hook/format.”* |
| `medium` | `suspect_medium` | *“Video **có dấu hiệu** được đẩy view (ads/seeding) để đạt mức này: ~{views} view, ER {er}% (median ngách ~{med}%), comment/view thấp bất thường.”* |
| `strong` | `suspect_medium` **và** (comments = 0 với views ≥ max(10k, p75 views ngách) **hoặc** ER &lt; p10 với views ≥ p90) | *“~100k view nhưng **0 comment** — pattern khớp view đẩy trả phí hơn viral organic; benchmark ngách thường ~{med_comments} comment ở mức view tương đương.”* |

**Ví dụ ✅ (synthesis / `claim` trong signal):**

- *“Video **có dấu hiệu chạy ads hoặc seeding** để đạt ~{views_fmt} view: ER chỉ ~{er}% (ngách ~{med_er}%), {comments} comment — tương tác không theo quy mô view.”*  
- *“Breakout ~{breakout}× so với TB kênh nhưng ER dưới p25 ngách — **khó** giải thích bằng FYP organic thuần.”*

**Ví dụ ❌:** *“Chắc chắn đã chạy Spark Ads.”* · *“Organic giảm 50% sau dừng ads.”* (không có data) · nhận định ads **không** kèm số.

Mỗi signal `boost_*` export `evidence_strength` + `claim`; synthesis **bắt buộc** giữ số từ manifest.

#### 4.7.1 Hai mục tiêu (chỉ phương pháp tự động)

| # | Mục tiêu | Deliverable khả thi |
|---|----------|---------------------|
| G1 | Giải thích **khi metric user** giống pattern boost/seeding (lợi/hại theo V5, có số đo) | Section `boost_attribution` (Chuyên sâu) + `signals/boost.py` |
| G2 | Peer benchmark **organic-shaped** | `reference_eligible` + lọc ref pool / MV / channel picks |

#### 4.7.2 Phương pháp tự động — in scope V1

| # | Phương pháp | Input (đã có / thêm) | Output | Phase |
|---|-------------|----------------------|--------|-------|
| **M1** | **Cross-section heuristic** | `views`, `likes`, `comments`, `engagement_rate`, `breakout_multiplier` vs phân vị cohort (post-pivot: **`content_class_intelligence`** / class-tier where available; legacy `niche_intelligence` bridge until M1 migrates) | `boost_attribution`: `organic_confident` · `suspect_low` · `suspect_medium` | **P0** |
| **M2** | **Reference hygiene** | `reference_eligible = false` khi `suspect_medium`; sort ref: proximity → ER **nếu** ER ≥ median ngách; breakout chỉ khi pass ER guard | G2 | **P0** |
| **M3** | **Live video (on diagnose)** | Cùng rule M1 trên `user_stats` + `niche_meta` percentiles | Signal vào manifest; có thể emit `boost_attribution` | **P1** |
| **M4** | **Stats time-series** | `video_corpus.stats_history` JSONB: snapshot lúc ingest + batch re-fetch T+6h, T+24h (ED `fetch_post_info`) | `distribution_shape`: `spike_then_flat` → tăng salience suspect (gợi ý seeding/ads backfire **pattern**) | **P1** |
| **M5** | **Comment shape** (optional) | Sample comments qua ED ([`comment-sentiment.md`](features/comment-sentiment.md)) — công thức, spike 1h đầu | `seeding_pattern_suspect` — chỉ khi M5 ship | **P2** |

**M1 — quy tắc batch (sau `/batch/analytics`, Chủ nhật):**

- `suspect_medium` khi **cả hai**: (a) `views` ≥ p90 ngách **và** (b) `engagement_rate` &lt; p25 **hoặc** `comments/views` &lt; p10.  
- `suspect_low` khi chỉ (a) hoặc chỉ (b).  
- `organic_confident` khi `views` &lt; p75 **và** ER ≥ p50 (hoặc mặc định `unknown` nếu thiếu sample ngách).  
- **`evidence_strength`:** `strong` khi `suspect_medium` + (`comments == 0` và views ≥ max(10k, p75 views ngách) **hoặc** ER &lt; p10); else `medium` / `weak` theo bảng §4.7.0.

**M4 — spike_then_flat (không cần OAuth):** views tăng ≥2× giữa t0→t+6h nhưng ER hoặc comments/view **giảm** ≥30% tại t+24h so với t+6h → flag shape; copy được: *“có dấu hiệu đẩy view sớm rồi tương tác không theo”* — không gọi “ads poisoning đã xác nhận”.

**Ngoài scope V1 (không ghi vào backlog product):** FYP %, organic traffic sau campaign, demographics Ads, cờ promoted chính thức. `promotion_type` trong Gemini = **commerce content**, không thay M1–M4.

#### 4.7.3 Schema data plane (F8)

| Column | Type | Ý nghĩa |
|--------|------|---------|
| `boost_attribution` | `text` | `unknown` · `organic_confident` · `suspect_low` · `suspect_medium` |
| `reference_eligible` | `boolean` | `false` iff `suspect_medium` (mặc định `true`) |
| `stats_history` | `jsonb` | `[{ "at": ISO, "views", "likes", "comments", "shares" }, …]` — phục vụ M4 |
| `distribution_shape` | `text` nullable | `null` · `spike_then_flat` · … (chỉ set khi M4 đủ điểm) |

Không field request-body / không cột `user_declared_*`.

#### 4.7.4 V6 — section & signals (Chuyên sâu only)

| `section_id` | `applies()` |
|--------------|-------------|
| `boost_attribution` | Video user `suspect_medium` (M3) **hoặc** manifest có signal `boost_*` / `distribution_shape` |

| Signal id | Kích hoạt | `claim` (theo §4.7.0) |
|-----------|-----------|------------------------|
| `boost_views_er_mismatch` | M1 / M3 | Nhận định *có dấu hiệu* ads/seeding + views, ER, comments vs ngách |
| `boost_breakout_low_engagement` | breakout cao + ER thấp | *“Breakout view nhưng ER không theo — khó coi organic thuần”* + số |
| `distribution_spike_then_flat` | M4 | Spike view sớm + tương tác phẳng; timestamps từ `stats_history` |
| `boost_tradeoff_education` | `evidence_strength ≥ medium` | Lợi/hại V5 §1.8 (mồi, poisoning tệp) — **gắn** nhận định phía trên, không tách “nếu có thể” khi đã `medium+` |
| `seeding_comment_pattern` | M5 | *“Có dấu hiệu seeding ảo”* + mẫu comment (khi có radar) |

**Không ship:** `*_confirmed`, `user_declared_*`, metric Analytics không có trong manifest.

**Prompt synthesis (`boost_attribution`):** Ưu tiên câu mở = nhận định có số (vd. views/comment/ER); block `recommendations` = hành động (tách benchmark, chỉnh hook, không dừng ads đột ngột nếu đang poison — checklist, không bịa % organic).

**Cơ bản:** không synthesize `boost_attribution`. Upsell teaser: *“Chuyên sâu: kiểm tra phân phối bất thường & benchmark đã lọc outlier”*.

#### 4.7.5 Reference selection — G2

| Call site | Sửa V1 |
|-----------|---------|
| `fetch_corpus_reference_pool` | Filter `reference_eligible = true`; order ER desc nhưng pick qua proximity + ER ≥ `median_er` |
| `_select_by_proximity_then_er` | Deprioritize / skip `suspect_medium` rows còn sót |
| `select_top_performers` | Sort `breakout_multiplier` với ER guard, không raw `views` |
| `niche_intelligence` MV | Aggregate từ `reference_eligible = true` — **bridge**; canonical aggregates → class MVs post-pivot |
| Home / ticker | Ưu tiên breakout **và** `reference_eligible` (thin corpus → disclaimer như hiện) |

Video user `suspect_medium`: narrative nói refs là **corpus organic-shaped**; so sánh format/hook, không gọi peer là “viral mẫu mực” nếu peer bị loại.

#### 4.7.6 Thứ tự build

| Phase | Scope |
|-------|--------|
| **P0** | M1 + M2: columns, nightly job, ref pool + channel sort |
| **P1** | M3 + M4: `stats_history` cron re-fetch, `boost_attribution` section + signals |
| **P2** | M5 nếu comment-sentiment ship |

#### 4.7.7 Acceptance (bổ sung §13)

- [ ] `reference_eligible` backfill + ref pool không pick `suspect_medium` (trừ thin corpus &lt; 5 — disclaimer)  
- [ ] `boost_attribution` chỉ Chuyên sâu; chỉ khi M3/M4 fire  
- [ ] Claim boost: *“có dấu hiệu”* + ≥2 số đo vs ngách; **không** “chắc chắn / 100%”; **không** metric Analytics giả  
- [ ] Channel top performers: không sort thuần `views` (P0)  

### 4.8 Signal layer — làm dày Chuyên sâu (V5 taxonomy)

**Bản chất Chuyên sâu:** cùng extract 1 lần, cùng [`build_signal_manifest`](../../cloud-run/getviews_pipeline/signals/registry.py) — khác ở (1) **nhiều section** được synthesize (§4.2) và (2) **nhiều signal/section** vào prompt + **signal backlog** dưới đây. Map taxonomy: [`bao-cao-flop-video-kenh-toan-dien-v5.md`](bao-cao-flop-video-kenh-toan-dien-v5.md).

#### 4.8.1 Basic vs Deep — tại tầng signal

| Knob | Cơ bản | Chuyên sâu (đề xuất V1) |
|------|--------|-------------------------|
| `build_signal_manifest` | Tính **đủ** (mọi extractor) | Giống Cơ bản |
| `select_sections_to_emit` | Whitelist §4.2 | Full pool + `boost_attribution` (§4.7) |
| `manifest_for_prompt` | Top **3** signal/section (`MAX_SIGNALS_PER_SECTION_IN_PROMPT`) | Top **5** khi `analysis_depth=deep` |
| `SECTION_EMIT_THRESHOLD` | 0.5 | 0.5 (hoặc 0.45 nếu `GETVIEWS_DEEP_RELAX_SALIENCE`) |
| Corpus trong `ctx` | `niche_meta`, `hook_effectiveness`, refs đã lọc §4.7 | Giống + percentiles p10/p25/p50/p90 cho M1/M3 |

```python
# signals/salience.py — V1
MAX_SIGNALS_PER_SECTION_IN_PROMPT_BASIC = 3
MAX_SIGNALS_PER_SECTION_IN_PROMPT_DEEP = 5

def manifest_for_prompt(manifest, *, depth: str = "basic") -> dict[str, list[Signal]]:
    cap = MAX_SIGNALS_PER_SECTION_IN_PROMPT_DEEP if depth == "deep" else MAX_SIGNALS_PER_SECTION_IN_PROMPT_BASIC
    return {sid: lst[:cap] for sid, lst in manifest.items()}
```

**Upsell Cơ bản:** UI đọc full manifest (không qua cap) để teaser *“+N finding trong Âm thanh / Editing…”* — không gọi synthesis.

#### 4.8.2 Đã ship — extractors → `section_id` (as-built)

Nguồn: [`signals/registry.py`](../../cloud-run/getviews_pipeline/signals/registry.py) `_EXTRACTORS`. Mỗi dòng = `signal.id` đã có code.

| `section_id` | Signal IDs (shipped) | Ghi chú |
|--------------|----------------------|---------|
| `diagnosis` | `diagnosis_baseline`, `hook_dialect_*`, `trigger_*` | Triggers: share/save archetype, sự thật trần trụi |
| `compliance` | `compliance_restricted_phrase`, `compliance_price_anchor_*`, `compliance_ad_law_disclosure_missing`, `compliance_shadowban_cheo_signature`, `compliance_hit`, `hook_gia_soc_price_anchor_risk` | §10 V5 |
| `hook_analysis` | `hook_first_frame_non_product`, `hook_type_niche_mismatch`, `hook_layering_single`, `hook_body_contract_violated` | §3 V5 — cần corpus `hook_distribution` |
| `distribution` | `caption_thin`, `hashtag_generic_cluster`, `sound_original`, `engagement_*`, `context_golden_hour_miss`, `context_tuong_tac_cheo_heuristic` | §1.5–1.7 một phần |
| `niche_pattern` | `niche_reference_anchor` | + `reference_videos` tiles |
| `douyin_origin` | `douyin_origin_peer`, `douyin_migration_poor_fit` | §Douyin |
| `channel_pattern` | `channel_baseline_available`, `channel_pattern_break_risk` | §2 kênh (sample ≥2–3) |
| `commerce` | `commerce_conversion_objective`, `commerce_verbal_cta_missing`, `commerce_price_tier_hook_mismatch`, `commerce_disclosure_*`, `commerce_creator_type_inconsistent`, `commerce_promotion_detected`, `commerce_cta_missing`, `commerce_performance_conversion_override` | §0 V5 |
| `metadata` | `metadata_safe_zone_bottom_risk`, `metadata_business_vpop_cml_friction` | §1.6 một phần |
| `editing` | `editing_color_grading_niche_mismatch`, `editing_text_overlay_readability` | §1.3 một phần |
| `sound` | `sound_lifecycle_phase`, `sound_cml_strip_risk`, `sound_dialect_audio_mismatch`, `sound_layering_thin_mukbang` | §1.4 + `trending_sounds` |
| `persona` | `persona_channel_baseline_mismatch`, `persona_authenticity_weak_negative_markers`, `persona_slang_dated`, `persona_dialect_expert_tension` | §1.2 |
| `script_structure` | `script_affiliate_five_phase_gap`, `script_livestream_demo_too_complete` | §1.1 / §1.7 |

**Chưa có section:** `boost_attribution` (§4.7 P1). **Chưa đăng ký extractor:** `signals/boost.py`.

#### 4.8.3 Backlog signal — Chuyên sâu + Win (ưu tiên V1)

Chỉ liệt kê signal **làm được** từ extract + ED + corpus (không OAuth, không user form). Cột **Phase** gắn F8/F1. **`tier_gate`:** `hit` = salience cao chỉ khi `performance_tier=hit` (Win path); `any` = flop/win.

**Win — Phase W0 (trước S1, §4.9):**

| Phase | `signal.id` | `section_id` | `tier_gate` | JTBD / Data |
|-------|-------------|--------------|-------------|-------------|
| **W0** | `win_er_above_niche_p75` | `diagnosis` | `hit` | ER / comment rate ≥ p75 ngách — “vì sao tương tác theo view” |
| **W0** | `win_hook_aligns_niche_top` | `hook_analysis` | `hit` | `hook_type` ∈ top `hook_distribution` |
| **W0** | `win_breakout_vs_channel` | `channel_pattern` | `hit` | `breakout_multiplier` vs median kênh (deep section; basic teaser) |
| **W0** | `win_format_in_growth` | `niche_pattern` | `hit` | `content_format` trong bucket Growth `format_distribution` |
| **W0** | `win_replicable_cta` | `next_video` | `hit` | CTA + format lặp lại được (extract + corpus) |

Flop-tier video: các signal `win_*` salience &lt; 0.5 hoặc không export — không synthesize “cơ chế thắng” trên video flop.

**Flop / shared backlog:**

| Phase | `signal.id` (đề xuất) | `section_id` | `tier_gate` | V5 / JTBD | Data |
|-------|------------------------|--------------|-------------|-----------|------|
| **P0** | `boost_views_er_mismatch` | `boost_attribution` | `any` | §1.8 Ads/seeding | `user_stats` + `niche_meta` percentiles (§4.7 M3) |
| **P0** | `boost_breakout_low_engagement` | `boost_attribution` | `any` | §1.8 | `breakout_multiplier`, ER vs ngách |
| **P0** | `niche_format_underrepresented` | `niche_pattern` | `any` | Format gap | `content_format` vs `format_distribution` |
| **P0** | `niche_hook_percentile_gap` | `hook_analysis` | `any` | Hook vs ngách | `hook_type` vs `hook_distribution` + sample ≥30 |
| **P1** | `distribution_spike_then_flat` | `boost_attribution` | `any` | Seeding backfire | `stats_history` (§4.7 M4) |
| **P1** | `boost_tradeoff_education` | `boost_attribution` | `any` | Lợi/hại ads | `evidence_strength` ≥ medium (§4.7.0) |
| **P1** | `hook_vague_specificity` | `hook_analysis` | `any` | Vague hook | `hook_phrase` / transcript |
| **P1** | `hook_pacing_cut_frequency` | `hook_analysis` | `any` | Pacing / cut | `transitions_per_second` vs ngách |
| **P1** | `commerce_silent_cta` | `commerce` | `any` | Silent CTA | `verbal_cta_present` + overlays |
| **P1** | `commerce_price_tier_structure` | `commerce` | `any` | Price tier | `commerce_intent.price_tier` |
| **P1** | `metadata_hashtag_volume_gap` | `metadata` | `any` | Hashtag §1.6 | `hashtag_count` vs ngách |
| **P1** | `metadata_caption_density` | `metadata` | `any` | Caption | caption len vs `pct_has_caption_text` |
| **P1** | `editing_cut_pace_outlier` | `editing` | `any` | Cut frequency | `transitions_per_second` p25/p75 |
| **P1** | `editing_broll_ratio_low` | `editing` | `any` | B-roll §1.3 | `scenes[]` mix |
| **P1** | `sound_trending_mismatch` | `sound` | `any` | Sound trend | `sound_id` vs `trending_sounds` |
| **P1** | `sound_no_audio_hook_window` | `sound` | `any` | Audio hook §1.4 | transcript 0–3s |
| **P1** | `persona_tone_distribution_gap` | `persona` | `any` | Tone mismatch | `tone` vs `tone_distribution` |
| **P1** | `script_zero_value_stretch` | `script_structure` | `any` | Zero-value pacing | `scenes` vs `video_duration` |
| **P1** | `engagement_comment_hook_missing` | `distribution` | `any` | Comment hook §1.7 | Transcript thiếu CTA hỏi |
| **P1** | `engagement_save_trigger_weak` | `diagnosis` | `hit` | Save architecture | `trigger_save_archetype` + proxy |
| **P2** | `seeding_comment_pattern` | `boost_attribution` | `any` | Seeding ảo | Comment radar (§4.7 M5) |
| **P2** | `distribution_posted_at_ritual_hint` | `distribution` | `any` | Audience offline | `posted_at` vs heatmap |
| **P2** | `channel_video_vs_eligible_peers` | `channel_pattern` | `any` | Video vs kênh | vs **reference_eligible** peers |

**Không backlog V1** (cần Analytics / không đo được): FYP %, retention 3s thật, cart CTR, shadowban xác nhận, demographics post-ads.

#### 4.8.4 Corpus utilization — bắt buộc cho signal mới

Mở rộng `build_diagnosis_ctx` / batch để `niche_meta` luôn có (khi `claim_tiers` đủ):

| Key trong `niche_meta` | Dùng cho signal |
|------------------------|-----------------|
| `hook_distribution`, `sample_size` | `hook_type_niche_mismatch`, `niche_hook_percentile_gap` |
| `format_distribution` | `niche_format_underrepresented` |
| `tone_distribution` | `persona_tone_distribution_gap` |
| `median_er`, `p25_er`, `p90_views` (computed) | `boost_*`, `context_tuong_tac_cheo_heuristic` |
| `avg_transitions_per_second`, `avg_hashtag_count`, `pct_has_caption_text` | editing / metadata backlog |
| `reference_eligible` filter trên refs | `niche_reference_anchor` không anchor video ads-skew |

Refresh: tái dùng class-tier percentiles (`content_class_intelligence` / `corpus_context.py`) where available; legacy `niche_intelligence` rows for unmigrated paths — không query full corpus mỗi request.

#### 4.8.5 Thứ tự implement (gắn §11)

*Pre-two-axis plan — depth/cache items still 🔨; W0/S1 boost still open.*

| Sprint | Deliverable |
|--------|-------------|
| **W0 (F2 Win)** | `signals/performance.py` hoặc `signals/win.py`: 2 signal P0 `win_er_*`, `win_hook_*`; salience `tier_gate=hit`; unit tests |
| **S1 (F8 P0)** | §4.7 M1/M2 + `niche_meta` percentiles + 2 signal `niche_*` |
| **S2 (F1 P1)** | `signals/boost.py`, `boost_attribution`, `manifest_for_prompt(depth)` cap=5, `analysis_depth` + cache composite (§4.12) |
| **S3 (F1 P1)** | Backlog §4.8.3 **P1** + Win W0 còn lại (`win_breakout_*`, `win_format_*`) |
| **S4 (F8 P2)** | M5 comment + timing hint |

#### 4.8.6 Acceptance (bổ sung §13)

- [ ] `analysis_depth=deep` → `manifest_for_prompt` cap **5**/section; basic cap **3**  
- [ ] ≥**8** signal backlog P0/P1 có test unit trong `cloud-run/tests/test_*_signals*.py`  
- [ ] Signal mới có `taxonomy_ref` + `evidence[]` với số từ ctx (không bịa)  
- [ ] Deep report trung bình ≥**2** signal/section trong prompt so với basic (sample 10 video QA)  

### 4.9 Video Win — JTBD & quyết định kiến trúc

**JTBD:** User thấy video nổi (Xu hướng / FYP / đối thủ) → **chắt lọc insight một lần đọc** (“vì sao chạy”, “công thức gì”, “quay tiếp thế nào”) — thay doomscroll xem đi xem lại.

**Quyết định V1 (đã chốt):**

| Câu hỏi | Trả lời |
|---------|---------|
| Pipeline Win riêng? | **Không** — cùng V6 §4.0 |
| Cơ bản / Chuyên sâu cho Win? | **Có** — cùng whitelist §4.2; default **Cơ bản** từ Xu hướng |
| Cache | `(video_id, analysis_depth)` — **không** nhân theo `performance_tier` (§4.12) |
| Signal Win | §4.8.3 **W0** — `tier_gate=hit` |

**Pipeline (một đường):** `extract` → tier refine → `build_signal_manifest` → `select_sections_to_emit(depth)` → `synthesize_diagnosis_v6` → `VideoBody`.

**Win vs Flop trong code (không fork):**

| Knob | Flop | Win (`tier` ≈ `hit`) |
|------|------|----------------------|
| `extract_video_errors` | `extraction_mode=flop` | `extraction_mode=win` |
| Title `diagnosis` | “VẤN ĐỀ CHÍNH” | “CƠ CHẾ CHẠY ĐÚNG” |
| FE chrome | `FlopDiagnosisStrip`, view scenarios | Lessons, breakout chip, `goWinScript` |
| Signals | flop-heavy §4.8.2 | + `win_*` §4.8.3 W0 |

**Entry as-built vs V1 target:** §4.10.

### 4.10 Entry points & navigation contract

**Shell:** §3 — Tab **Studio** (gợi ý 3 tầng + 4 pill) · Tab **Xu hướng** (công thức + kho).

| Entry | Route / handoff V1 | Default `depth` | Default `mode` | `source_entry` |
|-------|-------------------|-----------------|----------------|----------------|
| Studio pill **Khám Video win** | `/app/answer?q={url}` | nút composer (default `basic`) | `win` (từ pill) | `composer` |
| Studio pill **Khám Video flop** | `/app/answer?q={url}` | nút composer (default `basic`) | `flop` (từ pill) | `composer` |
| Studio pill **Khám Kênh** | `/app/channel` | nút composer | — | `composer` |
| Studio pill **Tạo kịch bản** | `/app/script` | — | — | `composer` |
| Tab Xu hướng (TikTok) — “Giải mã video này” | `/app/answer?q={url}&depth=basic&mode=win&from=trends` | `basic` (fixed) | `win` | `trends` |
| Tab Xu hướng (Douyin) — card tương tự | handoff video nếu có URL VN map | `basic` | `win` | `trends_douyin` |
| Evidence tile, IdeaBlock, SceneIntel | `prefillUrl` → `?q=` | inherit pill + composer | inherit pill | `evidence` |

**As-built gap (cần implement):**

| File | Hiện tại | V1 |
|------|----------|-----|
| [`AnswerScreen.tsx`](../../src/routes/_app/answer/AnswerScreen.tsx) | `prefillUrl` / `initialPrompt`; composer follow-up + TimelineRail | `depth`/`mode`/`from`; **ẩn** follow-up §4.10.1; URL-only submit từ pill video |
| [`intent-router.ts`](../../src/routes/_app/intent-router.ts) | Nhiều intent (pattern, timing, …) | V1 Studio: chỉ `video_diagnosis` + route kênh/script theo pill |
| [`ExploreScreen.tsx`](../../src/routes/_app/trends/ExploreScreen.tsx) ~L1170 | `navigate(..., { prefillUrl })` | Full query: `depth=basic&mode=win&from=trends` |
| `TrendsRail`, `PatternModal`, `GenericEvidenceGrid`, `SceneIntelligencePanel`, `IdeaBlock` | `prefillUrl` only | Align với bảng trên |

**Query param contract:**

| Param | Values | Default nếu omit | Ghi chú |
|-------|--------|------------------|---------|
| `depth` | `basic` \| `deep` | `basic` | Invalid → `basic` |
| `mode` | `win` \| `flop` | BE: `detect_mode_from_query` → `is_flop_mode` | Explicit `mode` ưu tiên heuristic |
| `from` | `trends` \| `trends_douyin` \| `composer` \| `evidence` | `composer` | Analytics; không đổi pipeline |
| `studio_pill` | `video_flop` \| `video_win` \| `channel` \| `script` | theo pill §3.1 | FE routing / analytics |
| `q` | URL hoặc aweme_id | — | Existing |

**UI labels (tiếng Việt):** “Cơ bản” / “Chuyên sâu” — không English trong product.

#### 4.10.1 V1 — một lượt, không follow-up

| | V1 | As-built (Post-V1 → `feature-map.md`) |
|---|-----|----------------------------------------|
| **Answer session** | **1 turn** = `video_diagnosis` → `VideoBody` xong | Turn 2+: pattern, timing, ideas, generic, creators, script… qua `append_turn` |
| **Composer Studio** | Pill video: **chỉ URL TikTok** (hoặc aweme_id); pill kênh → `/app/channel` | Câu hỏi tự do → `intent-router` → research / `/api/chat` |
| **UI Answer** | Không composer follow-up; không **TimelineRail** multi-turn | `AnswerScreen` input sau báo cáo |
| **Upsell Chuyên sâu** | Mở lại cùng URL, `depth=deep` (credit mới) | — |
| **History** | Xem session cũ (`history_union`) | Tạo session text/chat mới từ composer |

**Implement gợi ý:** FE — sau `ReportV1` video, ẩn input / chỉ CTA Deep + Script + Xu hướng; BE — có thể từ chối `append_turn` khi session đã có `format=video_diagnosis` (optional guard).

### 4.11 UI/UX — Video Intelligence

Tham chiếu [`artifacts/uiux-reference/`](../../artifacts/uiux-reference/) + [`VideoBody.tsx`](../../src/components/v2/answer/video/VideoBody.tsx).

#### 4.11.1 Chrome theo framing (Win vs Flop)

| UI | Win | Flop |
|----|-----|------|
| Tier chip | `performance_tier=hit` breakout | Flop / unknown humility |
| Section `diagnosis` | “CƠ CHẾ CHẠY ĐÚNG” | “VẤN ĐỀ CHÍNH” |
| Strip / scenarios | `winLessons`, bright spot | `FlopDiagnosisStrip`, `viewScenarios` |
| Primary CTA | “Quay theo công thức” → Script Studio | Handoff script sửa hook |
| Secondary | “Phân tích chuyên sâu” (nếu đang Basic) | Cùng upsell Deep |

#### 4.11.2 Nút Cơ bản / Chuyên sâu (composer — Tab Studio)

| Element | Spec |
|---------|------|
| Vị trí | **Composer Tab Studio** — luôn visible; áp dụng khi pill **Khám Video flop**, **Khám Video win**, hoặc **Khám Kênh** |
| Không áp dụng | Pill **Tạo kịch bản** (billing script §7); handoff từ Tab Xu hướng (`from=trends` → `depth=basic` cố định, không hỏi lại) |
| UI | Hai **nút** (không modal): **Cơ bản** · **Chuyên sâu** |
| Copy gợi ý | Cơ bản — “Giải mã nhanh · 1 credit” · Chuyên sâu — “Đầy đủ góc · 2 credit” (video); kênh theo §10 |
| Default | Cơ bản |
| Pill flop/win | Chỉ preset `mode`; **không** thay nút depth |

#### 4.11.3 Post–Cơ bản upsell

- Sticky CTA: “Phân tích chuyên sâu (2 credit)” — gọi lại cùng URL, `depth=deep`.  
- Teaser cards: locked sections từ full manifest (Âm thanh, Editing, Douyin, Boost…) — §4.2; **không** synthesize sẵn.

#### 4.11.4 Tab Xu hướng — card CTA

- Context: user ở **Tab Xu hướng** (công thức / kho / rail), không Tab Studio.  
- Label đề xuất: **“Giải mã video này”**.  
- **1 tap** → `/app/answer?...&depth=basic&mode=win&from=trends` — **không** hiện nút Cơ bản/Chuyên sâu (đã default basic).  
- Optional polish: auto-focus **Tab Studio** khi stream bắt đầu (V1.1).

```mermaid
sequenceDiagram
  participant User
  participant Trends
  participant Answer
  participant BE
  User->>Trends: tap breakout card
  Trends->>Answer: q=url depth=basic mode=win
  Answer->>BE: append_turn depth=basic
  BE-->>Answer: VideoReport basic sections
  User->>Answer: tap Chuyen_sau
  Answer->>BE: depth=deep synthesis_only
```

### 4.12 Data & API contract

#### 4.12.1 Persistence layers

```mermaid
flowchart LR
  subgraph hot [Hot_cache_TTL_1h_on_demand]
    VD[video_diagnostics]
  end
  subgraph session [Session_immutable]
    AT[answer_turns.payload]
  end
  VD --> ReadPath[build_video_report_cache_hit]
  AT --> History[history_union]
```

| Store | V1 key | Payload / columns |
|-------|--------|-------------------|
| `video_diagnostics` | **`UNIQUE (video_id, analysis_depth)`** | `cached_response` JSONB (on-demand); granular cols corpus path — migration §4.12.3 |
| `answer_turns` | per turn | `ReportV1` + echo `analysis_depth`, `source_entry`, `mode` |
| `answer_sessions` | optional | `last_analysis_depth` — chỉ nếu resume cần; ưu tiên query params |

#### 4.12.2 As-built vs V1 gap

| Topic | As-built | V1 spec |
|-------|----------|---------|
| Cache lookup | `.eq("video_id", vid)` — **1 row/video** | `.eq("video_id").eq("analysis_depth", depth)` |
| `mode` win↔flop switch | Skip cache → full recompute ([`video_analyze.py`](../../cloud-run/getviews_pipeline/video_analyze.py) L1551–1556) | **V1 đề xuất giữ (D9)** — đơn giản; cost khi user đổi mode |
| Extract | 1× / video | Không re-extract khi basic→deep |
| Basic → Deep | — | Cache miss `deep` → synthesis-only (manifest + extract đã có) |

#### 4.12.3 Migration sketch (F8 — implement sau doc approve)

```sql
-- V1: partition diagnosis cache by depth
ALTER TABLE public.video_diagnostics
  ADD COLUMN IF NOT EXISTS analysis_depth text NOT NULL DEFAULT 'deep'
    CHECK (analysis_depth IN ('basic', 'deep'));

-- Backfill existing rows as 'deep' (current behavior ≈ full pool)
-- Then add unique constraint (may require dedupe if multiple rows per video_id):
CREATE UNIQUE INDEX IF NOT EXISTS video_diagnostics_video_id_depth_key
  ON public.video_diagnostics (video_id, analysis_depth);
```

On-demand upsert: always set `analysis_depth` from request. Corpus path: write **both** rows when user upgrades basic→deep (deep synthesis pass).

#### 4.12.4 API surface (BE)

| Surface | Parameters | Default |
|---------|------------|---------|
| `build_video_report` / `append_turn` (turn 1 only V1) | `analysis_depth`, `mode?`, `source_entry?` | `basic`, heuristic mode, `composer`; turn 2+ Post-V1 §4.10.1 |
| `run_video_diagnosis` / `/stream` | same | Video diagnosis (answer path) |
| `manifest_for_prompt` | `depth` | cap 3 / 5 |
| `select_sections_to_emit` | `depth` | whitelist if `basic` |
| Billing | `decrement_credit` | ×1 basic, ×2 deep (§10) |

#### 4.12.5 Acceptance Win + depth (→ §13)

- [ ] Không `/stream` pipeline thứ hai cho Win  
- [ ] `hit` vs `flop`: khác title + FE mode; **cùng** `diagnosis_vi` schema  
- [ ] Xu hướng: 1 tap → `depth=basic`, `mode=win`  
- [ ] `basic` sections ⊆ `deep` sections (cùng URL)  
- [ ] Cache basic/deep không trả nhầm payload  

---

## 5. Trụ 2 — Channel Intelligence

### 5.1 Định nghĩa hai mức

| | **Cơ bản (Nhanh)** | **Chuyên sâu (Sâu)** |
|---|-------------------|----------------------|
| **Use case** | “Kênh @x đang thế nào?” trước khi follow | Audit kênh mình / đối thủ cho brief |
| **Input** | `@handle` | `@handle` + optional `video_url`, `force_refresh` |
| **Output** | Median views, 1 breakout gần nhất, hook dominant, link 1 video corpus | Score card v2, peers, narrative SSE, trajectory + **channel findings** V5 §2 (§5.3) |
| **Cache** | Corpus rollup only (no full SSE) | `channel_diagnoses` **7 ngày** |
| **Billing (đề xuất V1)** | Free hoặc 1 credit | **3**× `decrement_credit` (align FE + BE — hiện **lệch**) |
| **Trạng thái code** | **V1 build** (card + ED light) | **Shipped** — `POST /channel/diagnose` |

**Known issue (pre-V1 launch):** `ChannelScreen.tsx` `CREDIT_COST = 3` nhưng BE chỉ gọi `decrement_credit` **1 lần** — phải align trước GTM ([`product-value-audit.md`](product-value-audit.md) §Code accuracy).

### 5.2 Feature IDs

| ID | Tên | Tier | Trạng thái | Evidence |
|----|-----|------|------------|----------|
| **F4** | Soi kênh Sâu | Deep | Shipped | `video.py` `/channel/diagnose`, `channel_diagnose.py` |
| **F5** | Soi kênh Nhanh | Basic | **V1 build** | `creator_velocity` + corpus top videos |

### 5.3 V5 Phần 2 (Channel) → Soi kênh Chuyên sâu (F4)

**Có thể bổ sung** — taxonomy [`bao-cao-flop-video-kenh-toan-dien-v5.md`](bao-cao-flop-video-kenh-toan-dien-v5.md) **Phần 2** map trực tiếp vào **F4** (`POST /channel/diagnose`). Khác video (§4.8): channel **không** dùng `build_signal_manifest` / V6 sections; dùng **SSE narrative** (`verdict`, `what_worked`, `what_falling`, …) + **`score_card` deterministic** ([`channel_diagnose.py`](../../cloud-run/getviews_pipeline/channel_diagnose.py), [`channel_diagnose_prompts.py`](../../cloud-run/getviews_pipeline/channel_diagnose_prompts.py)).

**Ràng buộc giống §4.7:** không TikTok OAuth, không user khai báo. Nhận định kiểu *“có dấu hiệu … vì …”* + số từ ED/corpus — không “chắc chắn shadowban” / không FYP %.

#### 5.3.1 Đã có (as-built) vs V5 §2

| V5 §2 | F4 hôm nay | Độ phủ |
|-------|------------|--------|
| **2.2 Niche inconsistency** | `derive_channel_persona`, `channel_pattern.formats`, trajectory `bursty` / `stagnant` | **Một phần** — format mix + inflection, chưa entropy “tạp nham” |
| **2.2 Audience mismatch** | `decline_from_peak`, `what_falling`, so sánh recent vs peak | **Một phần** — không đo Following traffic |
| **2.3 Format saturation** | `competitive_landscape` + peers + `video_patterns` / corpus | **Một phần** — qua peer gap, chưa % format trùng top 20 ngách |
| **2.5 Persona / signature** | `channel_persona`, `score_card.category_label`, cadence | **Một phần** — chưa profile-visit proxy |
| **2.5 Slang staleness** | — | **Chưa** — cần aggregate `persona_slang_dated` từ corpus extract |
| **2.4 Compliance (kênh)** | — (video-level `compliance` signals) | **Chưa ở tầng kênh** |
| **2.1 Shadowban / bot / device** | — | **Chưa** — chỉ proxy view ceiling |
| **2.3 Mega Sale cannibalization** | — | **Chưa** — cần lịch sale + view dip theo tuần |
| **Audit flow Vòng 0–4** | trajectory + score card | **Một phần** — chưa map “kẹt 300 = Vòng 1” |

#### 5.3.2 Cơ chế bổ sung (không đổi UX shell)

Hai lớp — giống tinh thần “dày signal” video nhưng implement khác:

| Lớp | Cách làm F4 | Consumer |
|-----|-------------|----------|
| **A — Deterministic `channel_findings[]`** | Python trước Gemini: rule + số → inject `<<<CHANNEL FINDINGS>>>` trong prompt | `verdict`, `what_falling`, `recommendations` |
| **B — Section SSE mới (tùy chọn)** | Parser thêm `=== account_health ===`, `=== policy_risk ===` khi có finding | FE `SectionRenderer` |

**Không** fork sang V6 `VideoBody` — channel giữ memo SSE.

#### 5.3.3 Backlog finding — Chuyên sâu kênh (V1)

Mỗi dòng = một entry trong `channel_findings[]` (`id`, `taxonomy_ref`, `strength`, `claim`, `evidence`, `section_hint`).

| Phase | `finding.id` | V5 | Data / rule |
|-------|--------------|-----|-------------|
| **P0** | `channel_view_ceiling_300` | §2.1 shadowban *proxy* | ≥3 video 90d: views ≤300 **và** ER không bù → *“có dấu hiệu trần phân phối ~300 view”* — **không** gọi shadowban chắc |
| **P0** | `channel_format_entropy_high` | §2.2 niche inconsistency | Shannon trên `content_format` share > ngưỡng; so `format_distribution` ngách |
| **P0** | `channel_recent_vs_peak_er_drop` | §2.2 audience mismatch | `recent_avg` views + ER proxy vs `peak` window |
| **P0** | `channel_peer_format_saturation` | §2.3 format saturation | Top 20 corpus 7d cùng `content_format` ≥70% → saturated |
| **P1** | `channel_compliance_aggregate` | §2.4 | Roll-up `compliance_*` từ `analysis_json` N video gần nhất trên corpus |
| **P1** | `channel_restricted_keyword_exposure` | §2.4 OCR/audio | Đếm video có `compliance_restricted_phrase` / OCR flags |
| **P1** | `channel_ad_law_disclosure_gap` | §2.4 VN 2025 | % video `brand_deal`/`affiliate` thiếu disclosure signal |
| **P1** | `channel_copyright_mute_risk` | §2.4 copyright | `sound_cml_strip_risk` aggregate trên kênh |
| **P1** | `channel_posting_cadence_vs_peer` | Macro cadence | `posts_per_week` vs `niche_channel_benchmarks` (đã có score card) |
| **P1** | `channel_best_hour_underused` | §1.5 timing (kênh) | `best_hour_ratio` từ `compute_posting_cadence` — đã có, đưa vào findings |
| **P1** | `channel_boost_outlier_share` | §1.8 (kênh) | % video handle trên corpus `suspect_medium` (§4.7 M1) |
| **P2** | `channel_mega_sale_dip` | §2.3 cannibalization | View 7d overlap sale calendar (static ICT dates) + dip ≥40% |
| **P2** | `channel_persona_drift` | §2.5 cross-niche drift | `content_class` đổi >1 lần trong 90d |
| **P2** | `channel_slang_staleness` | §2.5 slang | Aggregate `persona_slang_dated` từ batch extract |

**Copy (§4.7.0):** ví dụ P0 — *“3/5 video gần nhất kẹt dưới ~300 view dù hook/format không đồng đều yếu — **có dấu hiệu** trần phân phối tài khoản; nên kiểm tra Account Status trong app TikTok, GetViews không đọc được FYP %.”*

#### 5.3.4 Map finding → narrative sections

| `section_hint` | Finding types | Ghi chú prompt |
|----------------|---------------|----------------|
| `verdict` | ceiling, format entropy, trajectory | Mở memo — 1 finding mạnh nhất |
| `what_falling` | mismatch, saturation, compliance aggregate | Bắt buộc trừ `breakout` / `new_account` |
| `what_worked` | cadence OK, hashtag winners | Giữ logic trajectory hiện tại |
| `competitive_landscape` | saturation, peer format gap | Đã có peer block |
| `recommendations` | mọi `strength ≥ medium` | Block `--- NGỪNG LÀM ---` gắn compliance / format scatter |
| `account_health` (mới) | `channel_view_ceiling_300`, boost share | Chỉ khi P0 firing |
| `policy_risk` (mới) | compliance roll-up | Chỉ khi ≥1 video flag |

#### 5.3.5 Data & reuse từ Trụ 1 / F8

| Nguồn | Dùng cho channel finding |
|-------|---------------------------|
| ED `fetch_user_posts` | views, likes, comments, `posted_at`, captions |
| `video_corpus` by handle | `content_format`, `analysis_json`, `boost_attribution` (§4.7) |
| `niche_channel_benchmarks` | percentile band (score card — giữ) |
| `video_patterns` / top corpus 7d | format saturation |
| Video `compliance` / `persona` signals | aggregate P1 — **không** re-extract |

**F5 Nhanh:** chỉ surface 1–2 finding P0 trên card (ceiling hoặc format entropy), không full SSE.

#### 5.3.6 Thứ tự build & acceptance

| Sprint | Deliverable |
|--------|-------------|
| **C1** | `build_channel_findings()` + inject prompt; 4 finding P0 |
| **C2** | P1 compliance + cadence + boost share; optional SSE `account_health` / `policy_risk` |
| **C3** | P2 sale calendar + persona drift |

- [ ] F4 prompt luôn nhận `<<<CHANNEL FINDINGS>>>` khi ≥1 finding  
- [ ] Finding P0 có số (video count, view threshold, format %)  
- [ ] Không câu “FYP = 0%” / “chắc chắn shadowban” trong channel memo  
- [ ] §4.7 `reference_eligible` áp dụng cho `select_niche_peer_*` (§4.7.5) — peer channel không ads-skew  

### 5.5 Triết lý salience cho kênh (không phải “dùng V6”)

**Chốt product:** Mục tiêu là **triết lý salience** — chỉ surface insight khi có bằng chứng đủ mạnh, xếp hạng, cap vào prompt, gate section theo context — **không** phải reuse stack V6 (`SECTION_POOL`, `VideoBody`, synthesis từng section).

**Câu trả lời ngắn:** Pipeline kênh hôm nay **cứng** (memo + trajectory cố định). **Nên** thêm lớp salience riêng: `channel_findings[]` → gate → `<<<CHANNEL FINDINGS>>>` (§5.3). **Giữ** một lần Gemini + SSE memo hiện tại.

**Triết lý salience (dùng chung video & kênh, implementation khác):**

1. **Tính** mọi candidate finding (rule + số).  
2. **Xếp hạng** `salience` / `evidence_strength`.  
3. **Gate** — chỉ emit section/block khi có finding vượt ngưỡng (kênh: thêm rule `trajectory`).  
4. **Cap** — top N finding vào LLM, không nhồi hết.  
5. **Copy** — claim gắn evidence; không khẳng định 100% (§4.7.0).

#### 5.5.1 As-built — hai pipeline khác nhau

| | **Video V6** (`/stream`, `build_video_report`) | **Channel F4** (`/channel/diagnose`) |
|---|-----------------------------------------------|--------------------------------------|
| Đơn vị phân tích | 1 video + refs | Cả kênh (N video ED + corpus) |
| Deterministic | `performance_tier`, refs, retention modeled | `classify_trajectory` (6 shape), `compute_score_card`, `build_channel_pattern`, tile rules theo trajectory |
| “Signal” | `build_signal_manifest` → ~40+ extractors, salience/section | **Không có manifest** — chỉ 2 signal `channel_*` trong video path; channel endpoint **không** gọi registry |
| LLM | `synthesize_diagnosis_v6_section_pool` — **theo section** đã chọn | **Một** `GenerateContent` memo dài — system prompt ~150 dòng quy định `=== verdict ===`, `=== what_falling ===`, … |
| Output | `diagnosis_vi.sections[]` + `findings[]` JSON | Parse `=== section_id ===` từ prose; thứ tự cứng `order = [verdict, what_worked, …]` |
| FE | `DiagnosisSectionRenderer` / `VideoBody` | `SectionRenderer` memo + `ScoreCard` SSE |
| Biến thiên độ dài | `select_sections_to_emit` + salience | Chủ yếu **trajectory** (bỏ `what_falling` nếu breakout) + có/không `video_url` |

→ Kênh = **memo tư vấn một lần**, cứng ở **tên section + framing trajectory**, không phải salience-driven section pool.

#### 5.5.2 Vì sao salience ≠ port V6

| Lý do | Chi tiết |
|-------|----------|
| **UX khác** | Creator đọc “bức tranh kênh” liền mạch — tách 8 block V6 giống video làm vỡ narrative |
| **Chi phí / coherence** | 8× Gemini section ≈ 8× token + rủi ro mâu thuẫn giữa section |
| **Primitive kênh** | `TrajectoryShape` + inflection + format table — không map 1:1 `hook_analysis` / `sound` |
| **Data aggregate** | Channel finding = roll-up N video — không phải `user_analysis` một lần extract |
| **Đã ship** | Cache `channel_diagnoses`, SSE `score_card`, tests `test_channel_diagnose_*` — rewrite rủi ro cao |

#### 5.5.3 Nên làm gì thay vì full restructure (đề xuất V1)

Áp dụng **cùng triết lý salience**, **khác implementation**:

```mermaid
flowchart LR
  videos[ED_posts_+_corpus]
  det[Deterministic: trajectory score_card pattern]
  findings[build_channel_findings salience]
  pick[select_channel_sections_to_emit]
  ctx[build_channel_diagnosis_context]
  llm[One memo Gemini]
  parse[parse === sections ===]
  videos --> det --> findings --> pick --> ctx --> llm --> parse
```

| Bước salience | Video (hiện tại) | Kênh V1 (đề xuất) |
|---------------|------------------|-------------------|
| Candidate pool | `build_signal_manifest` | `build_channel_findings()` — `taxonomy_ref` V5 §2 |
| Gate | `applies()` + ngưỡng salience/section | `evidence_strength` + trajectory (vd. skip `what_falling` khi breakout) |
| Cap vào LLM | `manifest_for_prompt` 3/5 | `<<<CHANNEL FINDINGS>>>` top N |
| Render | V6 sections + `VideoBody` | **Memo SSE** — findings chỉ là input prompt |
| Mở rộng | Thêm extractor → `section_id` | Thêm rule → `finding.id`; optional block `account_health` |

**Chia sẻ code (surgical):**

- Dataclass `Evidence` / `Signal` (hoặc alias `ChannelFinding`) — cùng file `signals/base.py`
- Copy contract §4.7.0 (“có dấu hiệu” + số)
- Aggregate video `compliance_*`, `persona_*`, `boost_*` từ corpus theo `creator_handle` → channel findings (không re-run extract)

**Không bắt buộc chia sẻ:** `SECTION_POOL`, `VideoBody`, per-section v6 synthesis — chỉ **pattern** salience + optional dataclass `Evidence`.

#### 5.5.4 Phạm vi V1

**§5.3 C1–C3** = đủ để kênh Chuyên sâu “salience-native” theo V5 Phần 2. Chỉ xem xét đổi UI/render (block giống video) nếu product yêu cầu riêng — ngoài phạm vi triết lý salience.

---

## 6. Trụ 3 — Xu hướng (browse corpus)

Surface: **Tab Xu hướng** (§3.2) — **freeze** hai khối **Công thức** + **Kho video**. “Hôm nay quay gì” = **Studio §3.1.1**, không duplicate trên Trends.

### 6.1 Scope V1 (đã chốt)

| Khối | Job | Ship |
|------|-----|------|
| **Công thức viral** | “Công thức nào video hit trong ngách đang dùng?” | ✅ **Giữ nguyên** UI + `PatternModal` |
| **Kho video** | Tìm/lọc corpus, xem tile, mở modal | ✅ **Giữ nguyên** filter/search |
| **Handoff phân tích** | 1 tap → video Win Cơ bản | 🔨 Query `depth`/`mode`/`from` §4.10 |
| Segment TikTok/Douyin, ritual Trends, reshape layout | — | ❌ Post-V1 |

### 6.2 Feature ID

| ID | Tên | Trạng thái | Ghi chú |
|----|-----|------------|---------|
| **F6** | Xu hướng | ✅ **UI freeze** · 🔨 **handoff** | `/app/trends`; §3.2.1 |

### 6.3 Freshness SLA (copy honesty)

| Signal | Cadence | Copy gợi ý |
|--------|---------|--------------|
| `daily_ritual` (Studio tier I) | Daily cron | “Cập nhật sáng nay” trên Studio |
| Pattern / corpus counts | Nightly batch | “Tính đêm qua” trên Xu hướng |
| Douyin card (nếu hiện) | Batch | Không claim realtime FYP |

### 6.4 Luồng vàng GTM

```mermaid
flowchart LR
  studio[Tab_Studio_Goi_y_hom_nay] --> script[Script_Studio]
  studio --> trends[Tab_Xu_huong]
  trends --> congthuc[Cong_thuc_viral]
  trends --> kho[Kho_video]
  congthuc --> f2[F2_Win_Co_ban]
  kho --> f2
  f2 --> upsell[Chuyen_sau_2_credit]
```

1. **Studio** — tier I ritual → script; tier III → Xu hướng.  
2. **Xu hướng** — chọn pattern hoặc video kho → **Giải mã** / tile CTA → F2 (`basic`+`win`, 1 credit).  
3. Upsell **Chuyên sâu** trong `VideoBody` hoặc composer pill flop/win.

---

## 7. Trụ 4 — Script Studio

Kịch bản **đủ quay** — không chỉ hook one-liner.

### 7.1 Output contract V1

| Thành phần | Mô tả |
|------------|--------|
| Hook đọc được | Câu mở từ ritual / generate |
| Shot list | N scene + timing; chip scene intel khi có |
| Meta | Duration, sound gợi ý, CTA |
| Export | Draft + shoot mode (`/app/script/shoot/:draftId`) |

### 7.2 Feature ID

| ID | Tên | Trạng thái | Evidence |
|----|-----|------------|----------|
| **F7** | Script Studio (golden path) | **Partial** | `script.py`, `useScriptSceneIntelligence`, ritual `scriptPrefillFromRitual` |

### 7.3 Billing

| Hành động | Credit |
|-----------|--------|
| Mở draft từ ritual (prefill) | Free |
| Generate / shot list sâu | **3×** `decrement_credit` (`answer_session.py` script kind) |

---

## 8. Trụ 5 — Data plane (điều kiện tiên quyết)

Mọi feature F1–F7 **phải** đọc từ cùng extract contract — không fork prompt ingest vs live (TD-7).

### 8.1 Pipeline layers

```
EnsembleData metadata
  → Gemini 1× extract (VideoAnalysis / CarouselAnalysis)
  → video_corpus.analysis_json + ~25 promoted columns
  → nightly: analytics, pattern-decks, layer0, sound-aggregate, trend-velocity, morning-ritual, scene-intelligence
  → on-demand: diagnosis / channel / script synthesis
```

### 8.2 Utilization matrix V1

**Chi tiết đầy đủ (FIELD × feature, legend, orphans, depth split):** [`data-utilization-map-v1.md`](data-utilization-map-v1.md) — **bắt buộc sign-off trước Wave 1 implement.**

| Feature | Bắt buộc đọc (tóm tắt) |
|---------|----------------|
| F2 Video Cơ bản (Win default Trends) | Full manifest; synthesize whitelist §4.2; Win signals W0 khi `tier=hit`; cache `(video_id, basic)` |
| F1 Video Chuyên sâu | Same manifest; full sections + §4.8.3 P0–P1 + `boost_attribution` §4.7; cache `(video_id, deep)` |
| F1/F2 reference peers | `fetch_corpus_reference_pool` + proximity pick; chỉ `reference_eligible = true` (§4.7.5) |
| F5 Channel Nhanh | `creator_velocity`, corpus top videos by handle |
| F4 Channel Sâu | + `channel_diagnoses`, peers, `video_patterns`, `channel_findings` §5.3 |
| F6 Xu hướng | `video_patterns`, `hook_effectiveness`, `video_corpus` (kho); `douyin_*` chỉ nếu block phụ hiện |
| F7 Script | `hook_phrase`, `scenes[]`, `scene_intelligence`, ritual grounding JSON |
| STU Studio | `daily_ritual`, `hook_effectiveness`, breakout corpus — §3.1 |
| F8 Batch | Promoted cols, MV, `claim_tiers`, M1/M2 — cột **BAT** trong map |

### 8.3 Claim gating (không marketing claim rỗng)

Dùng [`claim_tiers.py`](../../cloud-run/getviews_pipeline/claim_tiers.py) + [`artifacts/sql/corpus-health.sql`](../sql/corpus-health.sql):

| Tier | Videos/30d | Cho phép claim |
|------|------------|----------------|
| `reference_pool` | ≥5 | Show refs |
| `basic_citation` | ≥20 | Generic niche talk |
| `niche_norms` | ≥30 | % hook benchmarks |
| `hook_effectiveness` | ≥50 | Hook leaderboard |
| `trend_delta` | ≥100 | Week-over-week delta |

UI: `ConfidenceStrip` / humility khi dưới ngưỡng — **đã có** trên pattern/diagnostic; áp dụng nhất quán F6.

### 8.4 Feature ID

| ID | Tên | Trạng thái |
|----|-----|------------|
| **F8** | Data plane + cron SLA + utilization gates | **Partial** — crons live; HI-11 route ✅ prod; ablation/search_vector open |

### 8.5 V1 data investments (ưu tiên)

1. Corpus depth per niche (ingest + analytics)  
2. Signal fire-rate ablation trước mọi prompt trim (`key_messages` only trim-safe)  
3. `search_vector` + `subject_matter` proximity  
4. **HI-11 `route` mode** — ✅ **Shipped prod** (2026-05-17+); rollback = `NICHE_RESOLVER_MODE=shadow` ([`two-axis-niche-cutover-runbook.md`](two-axis-niche-cutover-runbook.md); historical PR1–PR6 → [`archive/two-axis-niche-cutover-pr1-pr6.md`](archive/two-axis-niche-cutover-pr1-pr6.md))  
5. **Boost attribution P0–P1** (§4.7): heuristic + `reference_eligible` + optional `stats_history`  
6. **`video_diagnostics` composite key** `(video_id, analysis_depth)` — §4.12.3  

### 8.6 Pre-launch — mua kho (không so sánh on-demand vs batch)

**Bối cảnh:** Pre-launch **chưa có traffic** — `diagnosed_7d` thấp là bình thường; **không** dùng tỷ lệ diagnosis/corpus để kết luận “lãng phí extract” hay cắt feature V1.

**Mục tiêu batch ingest trước launch:**

```text
Batch extract ($)  →  corpus + MV (patterns, hooks, rituals)
                              ↓
Launch            →  User thấy: ngách có N video, công thức Y, hook Z (tin được)
                              ↓
Sau launch        →  Diagnosis tận dụng blob đã có (corpus-hit → synthesis, không extract lại)
```

**Hai track tách biệt (không trộn):**

| Track | Câu hỏi | Quyết định |
|-------|---------|------------|
| **A — Product / GTM** | Surface nào ship V1? | `feature-map-v1` scope + freeze §1.1 — **không** kỳ vọng giảm `video_extraction` |
| **B — Corpus / cost** | Trả bao nhiêu $/ngày cho kho? | Ingest volume, hero niches, optional HI-13/HI-15 — §8.8 |

**North star pre-launch:** Mỗi đô extract phải **hiện** trên Xu hướng, Studio, hoặc câu chuyện launch — không cần chờ user diagnosis.

**Hai trục taxonomy (data, không nhầm §4 “hai mức depth”):**

| Trục | Bảng | Vai trò pre-launch |
|------|------|-------------------|
| Creator niche (UX) | `creator_niches` (**16 active**) | Pill Studio/Xu hướng, ritual, pattern filter — taxonomy v2: `comedy` (5) restored, `art_craft` (17) added, `pets_home` (13) retired |
| Content class (granular) | `content_classifications` (**82**: 77 video + 5 carousel) + junction | **Canonical cohort** — prod defaults ON: `CORPUS_SCORE_COHORT=class`, `CORPUS_INGEST_LOOP=class`, class-first browse; class **82** `ai_tool_workflow_tutorial`; diagnosis peers `(class, creator_tier)` |

Chi tiết FIELD × feature: [`data-utilization-map-v1.md`](data-utilization-map-v1.md). Cutover ops: [`two-axis-niche-cutover-runbook.md`](two-axis-niche-cutover-runbook.md). Taxonomy tables: [`two-axis-niche-model.md`](two-axis-niche-model.md).

### 8.7 Pre-launch utilization gate (tối đa giá trị trên cùng budget)

**Ba tầng utilize** — không cần traffic thật; dogfood staging + `corpus-health.sql`.

#### Tầng 1 — Surface kho trên UI (P0 launch)

| Surface | ID | Data batch đã trả | Gate pre-launch |
|---------|-----|-------------------|-----------------|
| **Xu hướng — Công thức** | F6 | `video_patterns` | Mỗi **ngách hero** ≥ 1 pattern có mechanism + ví dụ; không card rỗng |
| **Xu hướng — Kho** | F6 | `video_corpus` promote cols | Filter/search; `ConfidenceStrip` đúng tier §8.3 |
| **Studio — Gợi ý** | STU | `daily_ritual`, `content_class_intelligence`, breakout | Cron `morning-ritual` OK; tier I = Morning Signal + ritual; tier III = within-niche breakouts; preview tier I–III trên staging |
| **Hook / format chips** | F6/STU | `hook_effectiveness`, `content_class_hook_effectiveness`, `content_class_intelligence` | Thin → copy khiêm tốn; **`content_class_intelligence`** primary; `niche_intelligence` bridge only (MV refresh off in prod) |

#### Tầng 2 — Aggregate từ corpus (Gemini **rẻ** hơn vision — tận dụng blob)

Chạy / verify nightly (F8 BAT) — **không** tăng `video_extraction`:

- `hook_effectiveness` refresh  
- `video_patterns` / pattern-deck synth  
- `content_class_intelligence` + tier MV refresh (canonical); `niche_intelligence` refresh **skipped** in prod  
- `scene_intelligence` (F7 demo)
- `daily_ritual` seed (demo accounts nếu cần screenshot launch)

#### Tầng 3 — Launch story = data contract

- Số video/ngách: query `video_corpus` thật — **không** số marketing cố định (§13, `corpus-health`)  
- 1–2 công thức hero có hook mẫu từ `video_patterns`  
- ≥1 demo **Answer corpus-hit** (URL đã trong kho) — chứng minh synthesis scale **sau** launch, không cần mass on-demand pre-launch

**P0 fields** (mỗi field phải có đường BAT/F6/STU — chi tiết ô trong utilization map):

| Nhóm field | Phục vụ launch |
|------------|----------------|
| `hook_type`, `hook_phrase`, `views`, `engagement_rate`, `content_format` | Kho + patterns + STU |
| `content_context.subject_matter` | Ritual + pattern naming |
| `niche_classification` / `content_class_id` / `inferred_creator_niche_id` | Pill + filter (shadow OK) |
| MV: `hook_effectiveness`, `video_patterns`, **`content_class_intelligence`** (+ tier/stats MVs) | F6 + claim tiers; `niche_intelligence` bridge only (refresh skipped) |

**P1 defer** (vẫn trong full extract / TD-7; **không** block launch UI):

- `persona_consistency_signals`, `key_messages` — § utilization map §8 orphans  
- Phần lớn field chỉ **F1 audit** (sound/editing/douyin…) — giá trị tăng **sau** khi có diagnosis traffic  

**Ngách hero (chốt trước launch):** 5–8 `creator_niche_id` — ingest **đủ sâu** (đạt `niche_norms` / `hook_effectiveness` §8.3); ngách phụ breadth tùy budget §8.8.

**SQL gate:** [`artifacts/sql/corpus-health.sql`](../sql/corpus-health.sql) — chạy trước GTM; map tier → copy `ConfidenceStrip` / humility.

### 8.8 Ingest policy (cost) — tách khỏi feature scope

Giảm cost **ngoài** cắt V1 feature: chủ yếu **ít video ingest hơn** hoặc profile rẻ hơn cho ngách non-hero.

| Lever | Env / code | Ghi chú |
|-------|------------|---------|
| Volume/ngách | `BATCH_VIDEOS_PER_NICHE`, `BATCH_PRIORITY_NICHE_IDS` | Ưu tiên hero; breadth sau |
| Daily cap | `GEMINI_DAILY_USD_MAX` + enforce batch pod | Baseline extract ~**$20–32/ngày** (sync `video_extraction`; HI-13 batch API khi bật) — cập nhật `system-design.md` §17 khi ship |
| Hook window | `GEMINI_HOOK_WINDOW_DUAL_PART=false` | Tiết kiệm vision sub-call |
| Batch API | HI-13 `video_extraction_batch` | Giảm $/video khi model hỗ trợ — không đổi schema |
| Lite profile (tương lai) | Breadth ngách phụ | Hook + format + `subject_matter` — **không** block hero full extract |

**Không kỳ vọng:** trim schema V1 alone giảm bill đáng kể (~1–3% theo [`corpus-gemini-utilization-audit.md`](corpus-gemini-utilization-audit.md)).

**RECOMMENDATION pre-launch:** Giữ ingest đủ sâu **ngách hero**; maximize **tầng 1–2** §8.7 thay vì cắt F6/STU UI.

---

## 9. Ma trận feature V1 (tổng hợp)

| ID | Feature | Trụ | Basic/Deep | Ship | Route / entry |
|----|---------|-----|------------|------|----------------|
| **STU** | Studio — Gợi ý hôm nay (3 tầng) | — | — | ✅ UI · ◐ data | `/app` — Morning Signal + ritual + breakouts (§3.1.1) |
| F1 | Phân tích video Chuyên sâu | 1 | Deep | ◐ | `/app/answer` + `analysis_depth=deep` (🔨 not in code) |
| F2 | Phân tích video Cơ bản (Win doomscroll) | 1 | Basic | 🔨 | `/app/answer?depth=basic`; Trends: `mode=win&from=trends` (§4.10) |
| F4 | Soi kênh Sâu | 2 | Deep | ✅ | `/app/channel` — `POST /channel/diagnose` |
| F5 | Soi kênh Nhanh | 2 | Basic | 🔨 | Xu hướng card / channel |
| F6 | Xu hướng (công thức + kho) | 3 | — | ✅ UI · 🔨 handoff | `/app/trends` §3.2.1 + `CrossNicheBreakoutLane` |
| F7 | Script Studio | 4 | — | ◐ | `/app/script` |
| F8 | Data plane | 5 | — | ◐ | batch + claim tiers; HI-11 route ✅ prod |

Legend: **✅ shipped** = in prod code today · **◐ partial** = surface live, spec gap remains · **🔨 V1 build** = in vision, not in code

---

## 10. Billing V1 (đề xuất — cần sign-off)

| Hành động | `decrement_credit` | Ghi chú |
|-----------|-------------------|---------|
| Video **Cơ bản** (primary, `depth=basic`) | **1×** | Cùng RPC; ít section → ít token |
| Video **Chuyên sâu** (primary, `depth=deep`) | **2×** | Gọi RPC 2 lần hoặc `decrement_credit` mở rộng — product chọn |
| Channel Sâu | **3×** (đề xuất) | Fix FE/BE mismatch |
| Channel Nhanh | 0 hoặc 1× | Product decision |
| Script generate sâu | 3× | As-built |
| Ritual / Xu hướng browse | Free | Top-of-funnel |

**Ví credit (đã chốt tên):** một loại **credit** thông thường — `profiles.credits_remaining` (đổi từ `deep_credits_remaining`). Phân tích **Cơ bản / Chuyên sâu** chỉ khác **số lần** trừ (1× / 2×), không phải loại tiền riêng.

Tất cả trừ qua RPC `decrement_credit` → `credits_remaining`.

---

## 11. Thứ tự build đề xuất

| Phase | Features | Lý do |
|-------|----------|--------|
| **0** | F8 — corpus health, cron SLA, **§8.7 pre-launch gate**, channel billing fix, **§4.7 P0**, **§4.12.3** migration `analysis_depth` | Ref pool + cache partition + hero niche depth |
| **1a** | **F2 Win path:** §4.10 handoff (6 navigate sites), §4.11 depth picker + upsell, `analysis_depth` BE, **W0** win signals | Đóng JTBD doomscroll trước F6 reshape |
| **1b** | F2/F1 depth parity; §4.8 S1–S2 (`boost.py`, cap=5) | Basic → Deep upsell |
| **1c** | F4 — §5.3 C1 (`channel_findings` P0) | Channel deep |
| **2** | F6 — handoff query only (§4.10); **không** reshape Xu hướng UI | Align sau 1a |
| **3** | F7 — Script golden path | Q2 “làm thế nào” |
| **4** | Polish F1, F4 + GTM copy | Monetize Q3 |

Map PVA backlog: [`product-value-audit.md`](product-value-audit.md) §PVA-001–020.

---

## 12. Mapping as-built → V1 (cho dev)

| V1 surface | Giữ | Đổi / thêm |
|------------|-----|------------|
| Video | `build_video_report`, `VideoBody` | §4.2–§4.12 |
| Kênh | `/channel/diagnose` | F5 peek; fix 3 vs 1 credit (D2) |
| Xu hướng | `TrendsPatternGrid` + Kho video §3.2.1 + `CrossNicheBreakoutLane` | **Giữ UI**; CTA → `from=trends` §4.10 (🔨 wiring) |
| Studio home | `HomeSuggestionsToday` 3 tầng §3.1.1 | **Giữ UI** — Morning Signal + within-niche breakouts shipped |
| Studio shell | App layout, composer | 4 pill §3.1.2; Cơ bản/Chuyên sâu |
| Script | `script.py`, scene intel | Golden path từ F6 / `goWinScript` |
| Data | `/batch/*`, `video_diagnostics` | §4.12 migration; §4.7 M1–M4 |

**FE files (handoff audit):** `AnswerScreen`, `ExploreScreen`, `TrendsRail`, `CrossNicheBreakoutLane`, `PatternModal`, `GenericEvidenceGrid`, `SceneIntelligencePanel`, `IdeaBlock` — §4.10.

**BE files:** `diagnose_sections.py`, `gemini.py`, `signals/salience.py`, `report_video.py`, `video_analyze.py`, `answer_session.py` — §15.

**Giữ as-built (không productize V1):** `history_union` (đọc cũ); admin/batch. **Không V1:** follow-up turns, text intents từ composer → `feature-map.md` § Post-V1.

---

## 13. Acceptance criteria V1 (launch gate)

### 13A — Shipped (verified as-built `8969f3e`)

- [x] Mở app → **Tab Studio** mặc định; **Gợi ý hôm nay** 3 tầng render (§3.1.1)  
- [x] Tab Xu hướng → **Công thức viral** + **Kho video** (§3.2.1) không regress layout  
- [x] Studio tier I → Morning Signal + ritual/script; tier III within-niche breakouts → `/app/trends`  
- [x] Cross-niche lane on Trends (`CrossNicheBreakoutLane`, Wave 3b)  
- [x] Class-first browse + junction filter (Phase C; `applyVideoCorpusNicheFilter`)  
- [x] HI-11 `route` in prod; taxonomy v2 migrated (**16 × 82**)  
- [x] TD-7: batch ingest và on-demand extract cùng contract (wave sign-off baseline)  
- [x] `peer_percentile` UI — `FlopDiagnosisStrip` reads payload (`VideoBody.tsx`)  
- [x] **§8.7:** Studio tier I–III render on staging (`daily_ritual` + Morning Signal + breakout); cron nightly SLA  

### 13B — Launch gate still open

- [ ] Mọi video card → **Cơ bản** hoặc **Chuyên sâu**; cùng V6 UI; Cơ bản ⊆ sections Chuyên sâu  
- [ ] Cache `(video_id, analysis_depth)` tách biệt; basic ⊆ deep sections; không serve nhầm depth  
- [ ] Composer **4 pill** + Cơ bản/Chuyên sâu picker (§3.1.2)  
- [ ] §4.9–§4.12 Win: Xu hướng 1 tap → `depth=basic` + `mode=win` + `from=trends` (query params **not wired** in Explore navigate paths yet)  
- [ ] §4.8 W0: ≥2 signal `win_*` + test; salience `tier_gate=hit`  
- [ ] Mọi handle → **Nhanh** hoặc **Sâu**; billing đúng spec §10  
- [ ] Kho / pattern tile → Answer handoff §4.10 (không paste URL thủ công)  
- [ ] Ritual Studio tier I → **Script Studio** ≤2 tap  
- [ ] `corpus-health` chạy — không copy “46k” nếu DB chưa đạt tier  
- [ ] **§8.7:** 5–8 ngách hero đạt tier tối thiểu `reference_pool` (≥5 video/30d); ưu tiên `niche_norms` / `hook_effectiveness` cho ngách launch  
- [ ] **§8.7:** Xu hướng — mỗi ngách hero có ≥1 `video_patterns` card không rỗng; Kho + `ConfidenceStrip` khớp tier  
- [ ] **§8.7:** ≥1 URL corpus-hit → Answer Cơ bản (demo) — chứng minh synthesis path, không yêu cầu mass on-demand pre-launch  
- [ ] Channel FE/BE credit aligned  
- [ ] §4.7: reference peers `reference_eligible`; boost section chỉ Chuyên sâu; không claim ads poisoning từ heuristic alone  
- [ ] §4.8: deep `manifest_for_prompt` cap 5; ≥8 signal backlog P0/P1 có test  
- [ ] §5.3: F4 có `channel_findings` P0; memo không claim FYP/shadowban chắc chắn  
- [ ] §4.10.1: Answer video **1 turn** — không composer follow-up; không pattern/timing/ideas từ Studio  

---

## 14. Open decisions (Tech Lead)

| # | Câu hỏi | Options |
|---|---------|---------|
| D1 | ~~Video Cơ bản credit~~ | **Đã chốt:** 1× basic / 2× deep (§10) — implement RPC |
| D2 | Channel Sâu charge | A) 3× RPC B) 1× như BE hiện tại C) 3× single RPC mới |
| D3 | ~~Shell + landing~~ | **Đã chốt:** 2 tab Studio + Xu hướng; **landing = `/app`** (Gợi ý hôm nay + composer) |
| D11 | ~~Xu hướng scope~~ | **Đã chốt (§3.2.1):** freeze Công thức + Kho video; không segment TikTok/Douyin bắt buộc |
| D4 | Đổi tên route `/app/trends` → `/app/xu-huong`? | SEO/i18n vs redirect cost |
| D5 | ~~Boost — user khai báo hay OAuth?~~ | **Đã chốt:** chỉ M1–M4 tự động (§4.7) |
| D6 | `reference_eligible=false` khi `suspect_medium` | **Đề xuất:** A) Auto loại ref + MV aggregates (§4.7.5) |
| D7 | ~~Xu hướng → video handoff~~ | **Spec chốt:** `depth=basic` + `mode=win` + `from=trends` (§4.10) — **🔨 FE wiring open** (Explore navigate chưa pass query params) |
| D8 | Cache composite migration | **Đề xuất:** A) `UNIQUE (video_id, analysis_depth)` + backfill `deep` (§4.12.3) B) defer — ship depth without DB partition |
| D9 | `mode` win↔flop đổi cache | **Đề xuất V1:** A) Giữ full recompute khi `mode` override (as-built) B) Cache chỉ theo depth; mode = prompt slice (V1.1) |
| D10 | Compliance trên Win Basic | **Đề xuất:** A) Giữ khi `applies` (§4.2) B) V1.1 bỏ khỏi whitelist Win |
| D12 | ~~Two-axis cutover~~ | **Done (2026-05-22):** HI-11 `route` prod; taxonomy v2 **16 × 82**; class MV browse; Waves 3a/3b UI under freeze |

---

## 15. Implementation traceability (Video Win + depth)

Bảng ownership — **spec only**; ticket sau khi §14 sign-off.

| Layer | File / area | V1 change |
|-------|-------------|-----------|
| **Two-axis FE (✅ shipped)** | [`corpusNicheFilter.ts`](../../src/lib/corpusNicheFilter.ts), [`useClassMorningSignals.ts`](../../src/hooks/useClassMorningSignals.ts), [`useCrossNicheBreakouts.ts`](../../src/hooks/useCrossNicheBreakouts.ts), [`useTopBreakouts.ts`](../../src/hooks/useTopBreakouts.ts) | Class-first browse; Morning Signal; cross-niche + within-niche breakouts |
| BE pipeline | [`diagnose_sections.py`](../../cloud-run/getviews_pipeline/diagnose_sections.py) | `BASIC_SECTION_ALLOWLIST`, `select_sections_to_emit(..., depth=)` — 🔨 |
| BE synthesis | [`gemini.py`](../../cloud-run/getviews_pipeline/gemini.py) | Pass `depth` → `manifest_for_prompt` cap 3/5 |
| BE salience | [`signals/salience.py`](../../cloud-run/getviews_pipeline/signals/) (hoặc mới) | `manifest_for_prompt(depth)` |
| BE Win signals | [`signals/performance.py`](../../cloud-run/getviews_pipeline/signals/performance.py) hoặc `signals/win.py` | W0: `win_er_*`, `win_hook_*`; `tier_gate=hit` |
| BE report | [`report_video.py`](../../cloud-run/getviews_pipeline/report_video.py), [`answer_session.py`](../../cloud-run/getviews_pipeline/answer_session.py) | `analysis_depth`, `source_entry`, `mode` |
| BE cache | [`video_analyze.py`](../../cloud-run/getviews_pipeline/video_analyze.py) | Read/write `(video_id, analysis_depth)`; synthesis-only upgrade |
| DB | `*_video_diagnostics_analysis_depth.sql`, `20260727000000_rename_deep_credits_to_credits.sql` | Cache partition; `credits_remaining` / `credits_granted` |
| FE routes | [`AnswerScreen.tsx`](../../src/routes/_app/answer/AnswerScreen.tsx), [`intent-router.ts`](../../src/routes/_app/intent-router.ts) | `depth`/`mode`/`from`; **no follow-up** §4.10.1 |
| FE Studio home | [`HomeSuggestionsToday.tsx`](../../src/routes/_app/home/components/HomeSuggestionsToday.tsx) | **Freeze** — no layout reshape |
| FE trends | [`ExploreScreen.tsx`](../../src/routes/_app/trends/ExploreScreen.tsx), [`TrendsPatternGrid.tsx`](../../src/routes/_app/trends/TrendsPatternGrid.tsx) | **Freeze** UI; handoff query §4.10 |
| FE UI | `DepthPicker` (mới hoặc inline composer), [`VideoBody.tsx`](../../src/components/v2/answer/video/VideoBody.tsx) | Teasers, Deep CTA §4.11; `FlopDiagnosisStrip` + `peer_percentile` ✅ |
| Types | [`api-types.ts`](../../src/lib/api-types.ts), [`report_types.py`](../../cloud-run/getviews_pipeline/report_types.py) | `analysis_depth`, `source_entry` |
| Docs sync | [`system-design.md`](system-design.md), [`feature-map.md`](feature-map.md) | Mirror §4.12 khi ship |

**Doc dependencies (post–v1.8 approve):**

1. [`system-design.md`](system-design.md) — video diagnosis: `analysis_depth`, cache composite, Trends handoff  
2. [`feature-map.md`](feature-map.md) — `/app/answer` query params  
3. Optional: [`product-value-audit.md`](product-value-audit.md) — PVA Win JTBD one-liner  

---

## 16. Doc self-review (vision V1)

- [x] Pipeline Win riêng? → **Không** (§4.9)  
- [x] Xu hướng freeze? → **Công thức + Kho video** giữ nguyên (§3.2.1)  
- [x] Studio freeze? → **Gợi ý hôm nay** 3 tầng (§3.1.1) — Morning Signal + within/cross-niche distinction documented  
- [x] Two-axis browse shipped under UI freeze? → **Yes** (class MV, junction filter, CrossNiche lane)  
- [x] Cross-niche ≠ Home Tier III? → **Yes** (§3.1.1, §3.2.2)  
- [x] Handoff spec? → **`depth=basic` + `mode=win`** (§4.10) — **FE wiring still 🔨**  
- [x] Cache key V1? → **`(video_id, analysis_depth)`** (§4.12) — **migration not shipped**  
- [x] Pre-launch cost ≠ cắt feature? → **§8.6–§8.8** — utilize kho; ingest policy tách track A/B  
- [ ] Video depth / composer 4 pill — still 🔨 (§3.1.2, §13B)  
- [ ] Human sign-off §14 D2, D4, D6, D8–D10 trước implement video depth  
- [ ] Chốt danh sách **ngách hero** + chạy `corpus-health` theo §8.7 trước GTM  

---

*Document owner: Product / Tech Lead. **v2.0 FINAL** — browse surfaces frozen; build focus = video depth, billing, composer pills, handoff. Deferred: [`feature-map.md`](feature-map.md) § Post-V1. Next: [`build-plan.md`](../plans/build-plan.md) từ §11.*
