"""Persona slot extractor for free-text Vietnamese queries.

Lightweight regex-based extraction of audience / persona attributes the user
mentions in their prompt. The synthesis prompt uses these so directions target
the right reader — today the bug is that "18-25 tuổi" is silently dropped from
outputs.

Kept deliberately minimal: no ML, no LLM call. Extend as gaps surface in QA.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Age range in Vietnamese: "18-25 tuổi", "18–25 tuổi", "từ 18 đến 25"
_AGE_RANGE_RE = re.compile(
    r"\b(?P<a>\d{1,2})\s*[-–to/\s]+\s*(?P<b>\d{1,2})\s*tuổi",
    re.IGNORECASE,
)
# Single age: "25 tuổi"
_AGE_SINGLE_RE = re.compile(r"\b(\d{1,2})\s*tuổi", re.IGNORECASE)
# Generational / demographic buckets
_COHORT_RES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bgen\s*z\b", re.IGNORECASE), "gen Z"),
    (re.compile(r"\bgen\s*y\b|millennial", re.IGNORECASE), "millennial"),
    (re.compile(r"\b(tuổi\s*teen|teen|thiếu\s*niên)\b", re.IGNORECASE), "teen"),
    (re.compile(r"\bmẹ\s*bỉm\b|mẹ\s*sữa|bà\s*bầu", re.IGNORECASE), "mẹ bỉm sữa"),
    (re.compile(r"\bsinh\s*viên\b", re.IGNORECASE), "sinh viên"),
    (re.compile(r"\bdân\s*văn\s*phòng\b", re.IGNORECASE), "dân văn phòng"),
]

# Pain points / product attributes that should not be lost in the response.
_PAIN_RES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bda\s*dầu\b", re.IGNORECASE), "da dầu"),
    (re.compile(r"\bda\s*khô\b", re.IGNORECASE), "da khô"),
    (re.compile(r"\bda\s*hỗn\s*hợp\b", re.IGNORECASE), "da hỗn hợp"),
    (re.compile(r"\bda\s*nhạy\s*cảm\b", re.IGNORECASE), "da nhạy cảm"),
    (re.compile(r"\bmụn\b", re.IGNORECASE), "mụn"),
    (re.compile(r"\bthâm\b|nám", re.IGNORECASE), "thâm/nám"),
    (re.compile(r"\blão\s*hóa\b", re.IGNORECASE), "lão hóa"),
    (re.compile(r"\btóc\s*dầu\b", re.IGNORECASE), "tóc dầu"),
    (re.compile(r"\brụng\s*tóc\b", re.IGNORECASE), "rụng tóc"),
    (re.compile(r"\bgiảm\s*cân\b|tăng\s*cân", re.IGNORECASE), "giảm cân"),
]

# Geography / origin hints used by creators to narrow references.
_GEO_RES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bhàn\s*quốc\b|korean|k-?beauty", re.IGNORECASE), "Hàn Quốc"),
    (re.compile(r"\bnhật\s*bản\b|japanese|j-?beauty", re.IGNORECASE), "Nhật Bản"),
    (re.compile(r"\bviệt\s*nam\b|vietnam", re.IGNORECASE), "Việt Nam"),
    (re.compile(r"\bpháp\b|french", re.IGNORECASE), "Pháp"),
    (re.compile(r"\bmỹ\b(?!\s*phẩm)|american", re.IGNORECASE), "Mỹ"),
]


@dataclass(frozen=True)
class PersonaSlots:
    audience_age: str | None = None        # "18-25" | "25" | "gen Z" | None
    audience_cohort: str | None = None     # "gen Z" | "sinh viên" | None
    pain_points: tuple[str, ...] = ()      # ("da dầu", "mụn")
    geography: str | None = None           # "Hàn Quốc" | None

    def asdict(self) -> dict[str, object]:
        return {
            "audience_age": self.audience_age,
            "audience_cohort": self.audience_cohort,
            "pain_points": list(self.pain_points),
            "geography": self.geography,
        }

    def is_empty(self) -> bool:
        return (
            self.audience_age is None
            and self.audience_cohort is None
            and not self.pain_points
            and self.geography is None
        )


def extract_persona_slots(query: str) -> PersonaSlots:
    q = query or ""
    if not q:
        return PersonaSlots()

    # Age
    age: str | None = None
    m_range = _AGE_RANGE_RE.search(q)
    if m_range:
        age = f"{m_range.group('a')}-{m_range.group('b')}"
    else:
        m_single = _AGE_SINGLE_RE.search(q)
        if m_single:
            age = m_single.group(1)

    # Cohort
    cohort: str | None = None
    for pat, label in _COHORT_RES:
        if pat.search(q):
            cohort = label
            break
    # If no explicit age but cohort implies an age bucket, leave age as-is (None)
    # so the prompt doesn't hallucinate a range.

    # Pain points (collect all — there can be multiple, e.g. "da dầu mụn")
    seen: set[str] = set()
    pains: list[str] = []
    for pat, label in _PAIN_RES:
        if pat.search(q) and label not in seen:
            pains.append(label)
            seen.add(label)

    # Geography (first match wins)
    geo: str | None = None
    for pat, label in _GEO_RES:
        if pat.search(q):
            geo = label
            break

    return PersonaSlots(
        audience_age=age,
        audience_cohort=cohort,
        pain_points=tuple(pains),
        geography=geo,
    )


def build_persona_block(slots: PersonaSlots) -> str:
    """Build a Vietnamese prompt block that REQUIRES the model to address slots.

    Empty when nothing was extracted — no prompt noise.
    """
    if slots.is_empty():
        return ""

    lines: list[str] = ["NGỮ CẢNH ĐỐI TƯỢNG (người dùng nhắc tới):"]
    if slots.audience_age:
        lines.append(f"- Độ tuổi: {slots.audience_age}")
    if slots.audience_cohort:
        lines.append(f"- Nhóm: {slots.audience_cohort}")
    if slots.pain_points:
        lines.append(f"- Vấn đề/đặc điểm: {', '.join(slots.pain_points)}")
    if slots.geography:
        lines.append(f"- Xuất xứ sản phẩm/thị trường: {slots.geography}")
    lines.append(
        "BẮT BUỘC: Với mỗi hướng content đề xuất, giải thích ngắn gọn (1 câu) tại sao "
        "hiệu quả với đối tượng trên. Không bỏ sót các đặc điểm trong danh sách."
    )
    return "\n".join(lines)
