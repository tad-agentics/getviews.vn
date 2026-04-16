"""Layer 0 — prompt content, Pydantic schemas, response schemas, few-shot examples.

Single source of truth for everything sent to Gemini in Layer 0.
Imported by layer0_niche.py, layer0_sound.py, and layer0_migration.py.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Pydantic schemas (used to build LAYER0_RESPONSE_SCHEMA via .model_json_schema())
# ---------------------------------------------------------------------------


class Confidence(str, Enum):
    CAUSAL = "CAUSAL"
    LIKELY_CAUSAL = "LIKELY_CAUSAL"
    CORRELATIONAL = "CORRELATIONAL"


class StalenessRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Mechanism(BaseModel):
    observation: str        # "4/5 top video mở bằng mặt trong 0.3s"
    trigger: str            # "Parasocial recognition"
    viewer_behavior: str    # "Không lướt tiếp vì thấy mặt người"
    metric_affected: str    # "3s retention"
    confidence: Confidence
    evidence_count: int = 0  # How many of the 5 top videos show this


class NicheInsightResponse(BaseModel):
    insight_text: str           # 2-3 đoạn tiếng Việt giải thích WHY combo chạy
    mechanisms: list[Mechanism]
    common_visual: str
    common_timing: str
    common_hook_mechanism: str
    retention_driver: str
    common_cta: str
    execution_tip: str
    staleness_risk: StalenessRisk


# JSON schema dict passed to Gemini via response_json_schema
LAYER0_NICHE_RESPONSE_SCHEMA: dict = NicheInsightResponse.model_json_schema()

# ---------------------------------------------------------------------------
# Module 0A — Niche Insight prompts
# ---------------------------------------------------------------------------

NICHE_INSIGHT_SYSTEM_INSTRUCTION = """Bạn là chuyên gia phân tích cấu trúc video TikTok Việt Nam.
Nhiệm vụ: tìm TẠI SAO một combo hook+format đang chạy — không phải CHỈ mô tả nó.

Quy tắc:
- Mỗi nhận định phải có CAUSAL CHAIN: Yếu tố → Trigger tâm lý → Hành vi người xem → Metric
- Phân biệt rõ: CAUSAL (yếu tố này GÂY RA kết quả) vs CORRELATIONAL (cùng xuất hiện nhưng chưa chắc là nguyên nhân)
- Cite cụ thể: timestamps, visual details, số liệu từ JSON data
- Viết tiếng Việt, giọng chuyên gia nói chuyện với creator — không phải giáo trình
- Dùng "Chạy vì:" không dùng "Tại sao hiệu quả:"
- KHÔNG bịa mechanism. Nếu data không đủ → nói "Không đủ data để kết luận causal"."""

NICHE_INSIGHT_FEW_SHOT_EXAMPLES = """## VÍ DỤ MẪU 1 — Ngách skincare, combo: Cảnh Báo + Before/After

INPUT:
Top 5 video (avg 280K views): đều mở bằng ảnh da xấu, nền trắng, face trong 0.3s
Baseline 5 video (avg 45K views): mở bằng sản phẩm hoặc text, nền đa dạng, face ở giây 1-2

OUTPUT:
{
  "insight_text": "5 video chạy nhất tuần này đều mở bằng ảnh da xấu trên nền trắng (4/5 dùng nền trắng, 1 dùng nền xám nhạt). Slide đầu xuất hiện face trong 0.3s — sớm hơn trung bình ngách (0.7s). Chạy vì: nền trắng tạo contrast tối đa với da bị mụn → trigger 'sợ da mình cũng vậy' trong 0.5s đầu → người xem không lướt vì muốn biết cách fix. Slide after (kết quả đẹp) xuất hiện ở giây 2.1 — đúng lúc retention drop → tạo hope loop giữ người xem. 3/5 video có CTA 'link ở bio' ở giây cuối, 2/5 dùng giỏ hàng vàng.",
  "mechanisms": [
    {
      "observation": "4/5 top video dùng nền trắng cho slide before, 0/5 baseline dùng",
      "trigger": "Contrast tối đa giữa da xấu và nền → amplify negative emotion",
      "viewer_behavior": "Fear response: 'da mình cũng vậy?' → không lướt, muốn biết solution",
      "metric_affected": "3s retention + completion rate",
      "confidence": "LIKELY_CAUSAL",
      "evidence_count": 4
    }
  ],
  "common_visual": "Ảnh da xấu nền trắng, face xuất hiện trong 0.3s đầu",
  "common_timing": "Before ở giây 0, After ở giây 2.1, CTA ở giây cuối",
  "common_hook_mechanism": "Fear trigger qua visual contrast → hope loop qua before/after",
  "retention_driver": "Hope loop: da xấu (sợ) → da đẹp (muốn) → giải pháp (cần)",
  "common_cta": "Link ở bio hoặc giỏ hàng vàng cuối video",
  "execution_tip": "Mở bằng ảnh before nền trắng + mặt trong 0.3s, after ở giây 2, CTA cuối",
  "staleness_risk": "LOW"
}

## VÍ DỤ MẪU 2 — Ngách review đồ gia dụng, combo: Giá Sốc + Product Demo

INPUT:
Top 5 video (avg 320K views): text giá sale nền đỏ/cam trong frame đầu, demo vận hành sản phẩm bằng âm thanh, không voice ngay
Baseline 5 video (avg 38K views): mở bằng mặt nói chuyện hoặc sản phẩm đặt yên, không hiển thị giá sớm

OUTPUT:
{
  "insight_text": "5 video chạy nhất tuần này đều hiển thị giá sale trên text overlay nền đỏ/cam trong 0.5s đầu — cụ thể là giá sau giảm, không phải giá gốc. Baseline mở bằng sản phẩm hoặc mặt nói chuyện, không có giá. Chạy vì: giá bất ngờ thấp tạo phản ứng 'thật hả?' → người xem dừng lướt để xác nhận, không phải vì tò mò mà vì KHÔNG TIN — cơ chế khác với hook Cảnh Báo (sợ) hay Kể Chuyện (đồng cảm). 3/5 video demo vận hành sản phẩm trước khi nói lời nào — audio bắt đầu bằng tiếng máy chạy/nước chảy, không phải giọng nói.",
  "mechanisms": [
    {
      "observation": "4/5 top video có text giá sale nền đỏ/cam trong frame đầu, 0/5 baseline có",
      "trigger": "Price disbelief: 'giá này thật hả?' → dừng lướt để verify",
      "viewer_behavior": "Không lướt tiếp vì muốn xác nhận giá — khác với curiosity (muốn biết thêm)",
      "metric_affected": "3s retention + giỏ hàng vàng click-through",
      "confidence": "LIKELY_CAUSAL",
      "evidence_count": 4
    },
    {
      "observation": "3/5 top video mở audio bằng tiếng sản phẩm vận hành, không phải giọng nói. 0/5 baseline làm vậy",
      "trigger": "ASMR/sensory hook: tiếng máy chạy thật tạo cảm giác 'đồ này hoạt động thật'",
      "viewer_behavior": "Trust signal qua audio — nghe tiếng máy chạy > nghe người nói 'sản phẩm tốt lắm'",
      "metric_affected": "Completion rate + save rate",
      "confidence": "CORRELATIONAL",
      "evidence_count": 3
    }
  ],
  "common_visual": "Text giá sale nền đỏ/cam frame 1, cầm sản phẩm tay giây 1.5",
  "common_timing": "Giá ở frame 0, cầm sản phẩm giây 1.5, demo vận hành giây 2-5, voice review giây 4+",
  "common_hook_mechanism": "Price disbelief → verify behavior + ASMR trust signal",
  "retention_driver": "Muốn xác nhận giá thật + muốn xem sản phẩm hoạt động",
  "common_cta": "Giỏ hàng vàng (5/5 video), không dùng 'link ở bio'",
  "execution_tip": "Text giá sale nền đỏ frame 1 → cầm sản phẩm giây 1.5 → demo vận hành (không nói) 3s → voice review giây 4",
  "staleness_risk": "LOW"
}"""

NICHE_INSIGHT_USER_PROMPT_TEMPLATE = """## Ngách: {niche_name}
## Combo #1 tuần này: {hook_type} + {content_format}

### TOP 5 VIDEO (chạy tốt nhất tuần này, dùng combo trên):
{top_videos_json}

### 5 VIDEO BASELINE (cùng ngách, khác combo, views trung bình):
{baseline_videos_json}

### Phân tích theo 3 cấp:

**CẤP 1 — QUAN SÁT:** Top 5 có điểm chung CẤU TRÚC nào mà baseline KHÔNG có?
(timing, visual, text overlay, scene sequence — cụ thể, cite data)

**CẤP 2 — CƠ CHẾ:** Tại sao điểm chung đó KHIẾN người xem ở lại/lưu/share?
Cho MỖI pattern: Yếu tố → [Trigger tâm lý] → [Hành vi người xem] → [Metric bị ảnh hưởng]

**CẤP 3 — KIỂM CHỨNG:**
- "Nếu bỏ yếu tố này khỏi top video, nó có còn chạy không? Vì sao?"
- "Nếu thêm yếu tố này vào baseline, nó có cải thiện không? Vì sao?"
- Rate mỗi pattern: CAUSAL / LIKELY_CAUSAL / CORRELATIONAL

Cuối cùng: 1 tip CỤ THỂ NHẤT để creator áp dụng combo này ngay.

Trả lời theo JSON schema đã cho."""

# ---------------------------------------------------------------------------
# Module 0B — Sound Insight prompts
# ---------------------------------------------------------------------------

SOUND_INSIGHT_PROMPT_TEMPLATE = """Sound "{sound_name}" vừa xuất hiện trong ngách {niche_name}:
{count} video trong tuần này, {prev_count} video tuần trước.

5 video dùng sound này:
{trimmed_analysis_jsons}

Câu hỏi: TẠI SAO sound này đang được dùng?
- Sync với loại content nào? (reveal, transition, reaction?)
- Beat drop/hook moment ở giây thứ mấy? Khớp với moment gì trong video?
- Tone sound match với tone content thế nào?
- Lifecycle: đang ở ngày mấy? Còn bao lâu trước khi saturated?

1 đoạn ngắn tiếng Việt. Cụ thể."""

# ---------------------------------------------------------------------------
# Module 0C — Cross-Niche Migration prompts + schema
# ---------------------------------------------------------------------------


class CrossNicheMigration(BaseModel):
    source_niche: str      # tên ngách nguồn
    target_niche: str      # tên ngách đích
    hook_type: str
    content_format: str
    why_transfers: str     # cơ chế universal 1-2 câu
    adaptation_tip: str    # điều chỉnh cụ thể cho ngách đích


class CrossNicheMigrationList(BaseModel):
    migrations: list[CrossNicheMigration]


LAYER0_MIGRATION_RESPONSE_SCHEMA: dict = CrossNicheMigrationList.model_json_schema()

CROSS_NICHE_PROMPT_TEMPLATE = """Dữ liệu phân bổ hook+format các ngách TikTok Việt Nam, 2 tuần:
{distributions_json}

Tìm "format migration" — combo đang phổ biến ở ngách A nhưng MỚI xuất hiện ở ngách B:
- Phổ biến = ≥5 video/tuần trong ≥2 tuần ở ngách A
- Mới xuất hiện = 0-1 tuần trước → 3+ tuần này ở ngách B

Cho mỗi migration phát hiện được:
1. Ngách nguồn → ngách đích, combo (hook_type + content_format)
2. Tại sao combo này có thể transfer được? (cơ chế universal)
3. Creator ngách B nên điều chỉnh gì khi áp dụng?

Trả về JSON object với key "migrations" chứa array. Nếu không phát hiện migration → {{"migrations": []}}

Schema:
{{
  "migrations": [
    {{
      "source_niche": "<tên ngách nguồn>",
      "target_niche": "<tên ngách đích>",
      "hook_type": "<hook type>",
      "content_format": "<content format>",
      "why_transfers": "<cơ chế universal 1-2 câu>",
      "adaptation_tip": "<điều chỉnh cụ thể cho ngách đích>"
    }}
  ]
}}"""

# ---------------------------------------------------------------------------
# Module 0D — Trending Hashtag Discovery prompts + schema
# ---------------------------------------------------------------------------


class HashtagClassification(BaseModel):
    hashtag: str           # without #
    niche_id: int          # matched niche_taxonomy.id
    niche_name: str        # for logging clarity
    confidence: float      # 0.0–1.0
    reason: str            # 1 sentence why this hashtag belongs to this niche


class HashtagDiscoveryResult(BaseModel):
    classifications: list[HashtagClassification]


LAYER0_HASHTAG_RESPONSE_SCHEMA: dict = HashtagDiscoveryResult.model_json_schema()

HASHTAG_DISCOVERY_PROMPT_TEMPLATE = """Bạn là chuyên gia phân loại nội dung TikTok Việt Nam.

Dưới đây là danh sách hashtag mới nổi (xuất hiện nhiều trong video viral tuần này) chưa được phân loại:
{candidate_hashtags_json}

Danh sách ngách hiện có:
{niches_json}

Nhiệm vụ: Phân loại mỗi hashtag vào đúng ngách. Chỉ phân loại khi tin chắc (confidence ≥ 0.75).
Bỏ qua hashtag quá chung chung (viral, trending, fyp, foryou) hoặc không rõ ngách.

Trả về JSON object với key "classifications". Hashtag không rõ ngách → KHÔNG đưa vào kết quả.

Schema:
{{
  "classifications": [
    {{
      "hashtag": "<hashtag không có #>",
      "niche_id": <integer>,
      "niche_name": "<tên ngách tiếng Việt>",
      "confidence": <0.0 đến 1.0>,
      "reason": "<1 câu giải thích ngắn tại sao hashtag này thuộc ngách đó>"
    }}
  ]
}}"""

# ---------------------------------------------------------------------------
# Quality validation
# ---------------------------------------------------------------------------

FORBIDDEN_PHRASES = [
    "nên cân nhắc",
    "thử nhiều cách",
    "có thể hiệu quả",
    "tùy thuộc vào",
    "nói chung là",
]


def validate_niche_insight(insight: dict) -> dict[str, bool | dict]:
    """Automated quality check. Returns passed=True/False + per-check breakdown."""
    import re

    mechanisms = insight.get("mechanisms") or []
    insight_text = insight.get("insight_text") or ""
    execution_tip = insight.get("execution_tip") or ""

    checks = {
        "cites_data": all(
            (m.get("evidence_count") or 0) >= 2 for m in mechanisms
        ) if mechanisms else False,
        "has_causal_claim": any(
            m.get("confidence") in ("CAUSAL", "LIKELY_CAUSAL") for m in mechanisms
        ),
        "is_vietnamese": len(
            re.findall(r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]",
                       insight_text)
        ) > 10,
        "tip_is_specific": bool(re.search(r"\d", execution_tip)),
        "not_generic": not any(p in insight_text for p in FORBIDDEN_PHRASES),
    }
    return {"passed": all(checks.values()), "checks": checks}
