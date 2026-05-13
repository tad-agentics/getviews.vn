"""Shared pytest fixtures and configuration."""
import os

# Disable OTel during tests — no OTLP collector is running so the BatchSpan
# exporter would emit noisy retries/failures to stderr.
os.environ.setdefault("OTEL_DISABLED", "true")
