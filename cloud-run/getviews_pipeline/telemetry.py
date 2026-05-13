"""OpenTelemetry bootstrapper for the GetViews Cloud Run pipeline.

Usage — call ``setup_telemetry()`` once at application startup (in main.py /
the FastAPI factory) before any requests are handled.  All spans are then
exported to Cloud Trace via the OTLP gRPC exporter which Cloud Run wires up
automatically when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set (or falls through to
the GCP metadata-server URL when running inside Cloud Run).

Boundary spans are emitted via the ``span()`` context manager exported from
this module:

    with telemetry.span("gemini.extract_video_errors", video_id=video_id):
        ...

The module is safe to import even when OTel is not installed: every public
symbol degrades to a no-op so tests and local dev don't need the SDK.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)

_TRACER_NAME = "getviews.pipeline"
_tracer: Any = None
_otel_available = False


def setup_telemetry(service_name: str = "getviews-pipeline") -> None:
    """Bootstrap OTel SDK + Cloud Trace exporter.

    Idempotent — safe to call multiple times. No-ops when
    ``OTEL_DISABLED=true`` or when the SDK is not installed.
    """
    global _tracer, _otel_available  # noqa: PLW0603

    if os.environ.get("OTEL_DISABLED", "").lower() in ("1", "true", "yes"):
        logger.info("[telemetry] OTel disabled via OTEL_DISABLED env var")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning("[telemetry] opentelemetry-sdk not installed; spans disabled")
        return

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    except ImportError:
        OTLPSpanExporter = None  # type: ignore[assignment,misc]

    resource = Resource.create({
        "service.name": service_name,
        "service.version": os.environ.get("K_REVISION", "local"),
        "cloud.region": os.environ.get("CLOUD_RUN_REGION", "unknown"),
    })
    provider = TracerProvider(resource=resource)

    if OTLPSpanExporter is not None:
        endpoint = os.environ.get(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "http://localhost:4317",
        )
        try:
            exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("[telemetry] OTLP gRPC exporter → %s", endpoint)
        except Exception as exc:
            logger.warning("[telemetry] OTLP exporter init failed, spans will be no-ops: %s", exc)
    else:
        logger.warning("[telemetry] OTLP exporter not installed; spans will not be exported")

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(_TRACER_NAME)
    _otel_available = True
    logger.info("[telemetry] OpenTelemetry initialised, service=%s", service_name)


def instrument_fastapi(app: Any) -> None:
    """Instrument a FastAPI application for automatic HTTP span generation."""
    if not _otel_available:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("[telemetry] FastAPI auto-instrumentation active")
    except Exception as exc:
        logger.warning("[telemetry] FastAPI instrumentation failed: %s", exc)


@contextmanager
def span(name: str, **attrs: Any) -> Generator[Any, None, None]:
    """Context manager that wraps a block in an OTel span.

    Attributes are set as span attributes (str / int / float / bool).
    Exceptions are recorded on the span then re-raised.

    When OTel is not available, this is a transparent no-op.

        with telemetry.span("gemini.extract", video_id="xxx", niche_id=3):
            result = extract_video_errors(...)
    """
    if not _otel_available or _tracer is None:
        yield None
        return

    from opentelemetry import trace
    from opentelemetry.trace import StatusCode

    with _tracer.start_as_current_span(name) as s:
        for k, v in attrs.items():
            if isinstance(v, (str, int, float, bool)) and v is not None:
                s.set_attribute(k, v)
        try:
            yield s
        except Exception as exc:
            s.set_status(StatusCode.ERROR, str(exc))
            s.record_exception(exc)
            raise


def current_trace_id() -> str | None:
    """Return the active W3C trace-id hex string, or None outside a span."""
    if not _otel_available:
        return None
    try:
        from opentelemetry import trace

        ctx = trace.get_current_span().get_span_context()
        if ctx.is_valid:
            return format(ctx.trace_id, "032x")
    except Exception:
        pass
    return None
