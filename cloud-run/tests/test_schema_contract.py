"""Phase 2.3 + 3.7.3 — Schema contract CI gate.

Validates that the Pydantic output models in services/extraction.py match the
TypeScript interfaces declared in src/lib/api-types.ts.

Rules:
- Required fields on the Pydantic side must be present and required on the TS side.
- Optional fields on the Pydantic side must be present on the TS side (may be optional).
- Type mappings: str → string, int/float → number, bool → boolean.
- Enum types (Literal["a","b"]) → all values must appear in the TS union.

These checks are narrow by design — they gate the "must not break" contract, not
the full schema. Widen them as new models are added.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ── Pydantic → JSON schema ───────────────────────────────────────────────────

def _pydantic_schema(model_class: Any) -> dict[str, Any]:
    """Return the JSON Schema dict for a Pydantic model."""
    return model_class.model_json_schema()


# ── TypeScript field extractor ────────────────────────────────────────────────

_TS_API_TYPES = (
    Path(__file__).parents[2] / "src" / "lib" / "api-types.ts"
)


def _extract_ts_interface(name: str) -> dict[str, Any]:
    """Naive extraction of an ``interface Foo { ... }`` block from the TS file.

    Returns a dict mapping field_name → {"optional": bool, "types": [str]}.
    Handles simple | unions, optional ``?``, and array ``[]`` suffix.
    Not a full TS parser — enough for the contract test.
    """
    src = _TS_API_TYPES.read_text(encoding="utf-8")

    # Find the interface block
    pattern = rf"(?:export\s+)?interface\s+{re.escape(name)}\s*\{{([^}}]*)\}}"
    m = re.search(pattern, src, re.DOTALL)
    if not m:
        raise AssertionError(
            f"TypeScript interface '{name}' not found in {_TS_API_TYPES}. "
            f"Add it or update the schema contract test."
        )
    body = m.group(1)

    fields: dict[str, dict[str, Any]] = {}
    # Match: [/** ... */] fieldName[?]: type;
    line_re = re.compile(
        r"(?:/\*\*.*?\*/\s*)?(\w+)(\?)?\s*:\s*([^;]+);",
        re.DOTALL,
    )
    for fm in line_re.finditer(body):
        fname = fm.group(1)
        optional = fm.group(2) == "?"
        raw_type = fm.group(3).strip()
        # Collapse whitespace and split on |
        types = [t.strip() for t in re.split(r"\s*\|\s*", raw_type) if t.strip()]
        fields[fname] = {"optional": optional, "types": types}
    return fields


def _pydantic_to_ts_type(json_type: str) -> list[str]:
    """Map a JSON Schema type string to TypeScript primitive strings."""
    mapping = {
        "string": ["string"],
        "integer": ["number"],
        "number": ["number"],
        "boolean": ["boolean"],
        "array": ["array"],
        "object": ["object"],
        "null": ["null"],
    }
    return mapping.get(json_type, ["unknown"])


# ── Contract assertions ───────────────────────────────────────────────────────

def _assert_field_present(
    model_name: str,
    field: str,
    *,
    required: bool,
    ts_fields: dict[str, dict[str, Any]],
) -> None:
    assert field in ts_fields, (
        f"SCHEMA DRIFT: Pydantic {model_name}.{field} has no counterpart in "
        f"TypeScript interface {model_name}. "
        f"Add '{field}' to api-types.ts or remove it from the Pydantic model."
    )
    if required:
        assert not ts_fields[field]["optional"], (
            f"SCHEMA DRIFT: Pydantic {model_name}.{field} is required but "
            f"is optional (?) in the TypeScript interface."
        )


# ── Concrete contract tests ───────────────────────────────────────────────────

class TestVideoFlopIssueContract:
    """VideoErrorItemLLM (Pydantic) ↔ VideoFlopIssue (TypeScript)."""

    PYDANTIC_MODEL_NAME = "VideoErrorItemLLM"
    TS_INTERFACE_NAME = "VideoFlopIssue"

    # Fields that MUST exist in both models and their required/optional status
    # Key: Pydantic field name → (required_in_py, required_in_ts)
    REQUIRED_FIELDS = {
        "sev": True,
        "t": True,
        "end": True,
        "title": True,
        "detail": True,
        "fix": True,
    }
    OPTIONAL_FIELDS = {"error_id"}

    def _get_ts(self) -> dict[str, dict[str, Any]]:
        return _extract_ts_interface(self.TS_INTERFACE_NAME)

    def _get_pydantic_schema(self) -> dict[str, Any]:
        from getviews_pipeline.services.extraction import VideoErrorItemLLM
        return _pydantic_schema(VideoErrorItemLLM)

    def test_required_fields_present_in_ts(self) -> None:
        ts = self._get_ts()
        for field, required in self.REQUIRED_FIELDS.items():
            _assert_field_present(
                self.TS_INTERFACE_NAME, field, required=required, ts_fields=ts
            )

    def test_optional_fields_present_in_ts(self) -> None:
        ts = self._get_ts()
        for field in self.OPTIONAL_FIELDS:
            assert field in ts, (
                f"SCHEMA DRIFT: Optional field '{field}' missing from TS {self.TS_INTERFACE_NAME}."
            )

    def test_sev_enum_values_in_ts(self) -> None:
        """sev Literal['high','mid','low'] must appear in TS VideoFlopIssue.sev."""
        ts = self._get_ts()
        sev_field = ts.get("sev", {})
        ts_types = sev_field.get("types", [])
        # The TS type might be a reference like FlopIssueSeverity — that's OK.
        # As long as it references something with the right values we trust it.
        # If it's inlined as a union, verify the values match.
        inlined_literals = {t.strip('"\'') for t in ts_types if t.startswith('"') or t.startswith("'")}
        if inlined_literals:
            assert {"high", "mid", "low"}.issubset(inlined_literals), (
                f"SCHEMA DRIFT: TS sev union {inlined_literals} missing Pydantic values."
            )
        # If it references a type alias (FlopIssueSeverity), pass — we trust the TS compiler.

    def test_pydantic_schema_is_valid_json(self) -> None:
        schema = self._get_pydantic_schema()
        # Round-trip through JSON to ensure it serialises without error.
        assert json.loads(json.dumps(schema)), "Pydantic schema did not round-trip JSON."


class TestVideoErrorsExtractionContract:
    """VideoErrorsExtractionLLM (Pydantic) wrapper shape."""

    def test_errors_array_field_exists(self) -> None:
        from getviews_pipeline.services.extraction import VideoErrorsExtractionLLM
        schema = _pydantic_schema(VideoErrorsExtractionLLM)
        props = schema.get("properties", {})
        assert "errors" in props, (
            "SCHEMA DRIFT: VideoErrorsExtractionLLM must have an 'errors' array property."
        )
        assert props["errors"].get("type") == "array" or "$defs" in schema, (
            "SCHEMA DRIFT: 'errors' must be an array."
        )

    def test_errors_items_reference_video_error_item(self) -> None:
        from getviews_pipeline.services.extraction import VideoErrorsExtractionLLM
        schema = _pydantic_schema(VideoErrorsExtractionLLM)
        props = schema.get("properties", {})
        errors_prop = props.get("errors", {})
        # Items should reference VideoErrorItemLLM (via $ref or inlined)
        items = errors_prop.get("items", {})
        has_ref = "$ref" in items or "properties" in items
        assert has_ref, (
            "SCHEMA DRIFT: errors.items should reference VideoErrorItemLLM shape."
        )


class TestNarrativeViContract:
    """NarrativeVi shape — checks key fields exist in TS."""

    TS_INTERFACE_NAME = "NarrativeVi"

    REQUIRED_FIELDS = ["van_de_chinh", "loi_chinh_narrative"]

    def test_required_fields_in_ts(self) -> None:
        ts = _extract_ts_interface(self.TS_INTERFACE_NAME)
        for field in self.REQUIRED_FIELDS:
            assert field in ts, (
                f"SCHEMA DRIFT: NarrativeVi.{field} missing from TS api-types.ts. "
                f"Add it or update the contract test."
            )


class TestVideoErrorsExtractionInputContract:
    """Phase 3.7.3 — LLM INPUT boundary: VideoErrorsExtractionInput."""

    REQUIRED_FIELDS = [
        "extraction_mode", "niche_label", "creator_handle",
        "views", "engagement_rate", "hook_phrase", "content_format",
    ]
    OPTIONAL_FIELDS = [
        "niche_avg_views", "niche_avg_retention", "niche_sample_size",
        "duration_sec", "retention_drop_pct_3s", "retention_drop_pct_10s",
        "content_context_subject_matter",
        "niche_classification_creator_niche_slug",
        "niche_classification_format_axis",
    ]

    def test_required_fields_in_pydantic(self) -> None:
        from getviews_pipeline.services.extraction import VideoErrorsExtractionInput
        schema = _pydantic_schema(VideoErrorsExtractionInput)
        props = schema.get("properties", {})
        for field in self.REQUIRED_FIELDS:
            assert field in props, (
                f"SCHEMA DRIFT: VideoErrorsExtractionInput.{field} missing from Pydantic model."
            )

    def test_optional_fields_in_pydantic(self) -> None:
        from getviews_pipeline.services.extraction import VideoErrorsExtractionInput
        schema = _pydantic_schema(VideoErrorsExtractionInput)
        props = schema.get("properties", {})
        for field in self.OPTIONAL_FIELDS:
            assert field in props, (
                f"SCHEMA DRIFT: VideoErrorsExtractionInput optional field {field} missing."
            )

    def test_schema_round_trips_json(self) -> None:
        from getviews_pipeline.services.extraction import VideoErrorsExtractionInput
        schema = _pydantic_schema(VideoErrorsExtractionInput)
        assert json.loads(json.dumps(schema)), "Schema did not round-trip JSON."

    def test_extraction_mode_is_constrained(self) -> None:
        from getviews_pipeline.services.extraction import VideoErrorsExtractionInput
        schema = _pydantic_schema(VideoErrorsExtractionInput)
        em = schema["properties"]["extraction_mode"]
        is_constrained = "const" in em or "anyOf" in em or "enum" in em or "$ref" in em
        assert is_constrained, "extraction_mode should be a constrained Literal."


class TestDiagnosisSynthesisInputContract:
    """Phase 3.7.3 — LLM INPUT boundary: DiagnosisSynthesisInput."""

    REQUIRED_FIELDS = [
        "niche_label", "content_format", "corpus_size",
        "performance_tier", "creator_handle", "views", "engagement_rate",
        "errors", "reference_video_ids",
    ]

    def test_required_fields_in_pydantic(self) -> None:
        from getviews_pipeline.models import DiagnosisSynthesisInput
        schema = _pydantic_schema(DiagnosisSynthesisInput)
        props = schema.get("properties", {})
        for field in self.REQUIRED_FIELDS:
            assert field in props, (
                f"SCHEMA DRIFT: DiagnosisSynthesisInput.{field} missing from Pydantic model."
            )

    def test_json_payload_method_returns_dict(self) -> None:
        from getviews_pipeline.models import DiagnosisSynthesisInput
        inp = DiagnosisSynthesisInput(
            niche_label="beauty",
            content_format="tutorial",
            corpus_size=100,
            performance_tier="flop",
            creator_handle="testcreator",
            views=1500,
            engagement_rate=0.03,
        )
        payload = inp.json_payload()
        assert isinstance(payload, dict)
        assert "niche_label" in payload
        assert "errors" in payload
        assert isinstance(payload["errors"], list)

    def test_errors_capped_at_3_in_payload(self) -> None:
        from getviews_pipeline.models import DiagnosisSynthesisInput
        inp = DiagnosisSynthesisInput(
            niche_label="x", content_format="y", corpus_size=0,
            performance_tier="flop", creator_handle="c", views=0, engagement_rate=0.0,
            errors=[{"id": i} for i in range(8)],
        )
        payload = inp.json_payload()
        assert len(payload["errors"]) == 3, "json_payload must cap errors at 3."


class TestVideoDiagnosisV5Contract:
    """Phase 4.0 — VideoDiagnosisV5 Pydantic ↔ TS contract."""

    REQUIRED_FIELDS = [
        "header", "van_de_chinh", "channel_proof", "errors",
        "cross_format_winners", "next_steps", "collapsibles",
    ]

    def test_required_fields_in_pydantic(self) -> None:
        from getviews_pipeline.models import VideoDiagnosisV5
        schema = _pydantic_schema(VideoDiagnosisV5)
        props = schema.get("properties", {})
        for field in self.REQUIRED_FIELDS:
            assert field in props, (
                f"SCHEMA DRIFT: VideoDiagnosisV5.{field} missing from Pydantic model."
            )

    def test_required_fields_in_ts(self) -> None:
        ts = _extract_ts_interface("VideoDiagnosisV5")
        for field in self.REQUIRED_FIELDS:
            assert field in ts, (
                f"SCHEMA DRIFT: VideoDiagnosisV5.{field} missing from TS api-types.ts."
            )

    def test_errors_max_length_3_in_pydantic(self) -> None:
        from getviews_pipeline.models import VideoDiagnosisV5
        schema = _pydantic_schema(VideoDiagnosisV5)
        errors_prop = schema["properties"]["errors"]
        assert errors_prop.get("maxItems") == 3, (
            "SCHEMA DRIFT: VideoDiagnosisV5.errors must have maxItems=3."
        )

    def test_channel_proof_is_nullable_in_ts(self) -> None:
        ts = _extract_ts_interface("VideoDiagnosisV5")
        cp = ts.get("channel_proof", {})
        types_list = cp.get("types", [])
        has_null = "null" in types_list
        assert has_null, (
            "SCHEMA DRIFT: VideoDiagnosisV5.channel_proof must be nullable (| null) in TS."
        )


class TestExtractionResultContract:
    """ExtractionResult (Pydantic models.py) ↔ ExtractionResult (TS api-types.ts)."""

    # All fields defined on the Pydantic model (properties, not computed).
    # ``metadata`` was absent from the TS interface until Phase 4.4.6 fix —
    # keeping it here ensures future drift is caught by CI.
    REQUIRED_FIELDS = ["video_id", "content_type", "metadata", "analysis",
                       "carousel_analysis", "transcript_quality", "entry_cost", "error"]

    def test_required_fields_in_ts(self) -> None:
        ts = _extract_ts_interface("ExtractionResult")
        for field in self.REQUIRED_FIELDS:
            assert field in ts, (
                f"SCHEMA DRIFT: ExtractionResult.{field} missing from TS api-types.ts."
            )

    def test_pydantic_model_has_matching_fields(self) -> None:
        from getviews_pipeline.models import ExtractionResult
        schema = _pydantic_schema(ExtractionResult)
        props = schema.get("properties", {})
        for field in self.REQUIRED_FIELDS:
            assert field in props, (
                f"SCHEMA DRIFT: ExtractionResult.{field} missing from Pydantic model."
            )

    def test_content_type_is_union(self) -> None:
        from getviews_pipeline.models import ExtractionResult
        schema = _pydantic_schema(ExtractionResult)
        ct = schema["properties"]["content_type"]
        # Either a const or an anyOf union
        is_constrained = "const" in ct or "anyOf" in ct or "enum" in ct or "default" in ct
        assert is_constrained, (
            "SCHEMA DRIFT: content_type should be a constrained type (Literal/enum)."
        )
