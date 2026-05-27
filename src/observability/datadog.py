"""DataDog forwarding configuration hook.

Configures the OpenTelemetry SDK to export metrics, traces, and logs
to DataDog via the OTLP exporter.  When running on AgentCore, set
``DISABLE_ADOT_OBSERVABILITY=true`` so the ADOT auto-instrumentation
layer does not conflict with the DataDog exporter.

Requirements: 16.4
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from src.config.settings import AppSettings

logger = logging.getLogger(__name__)

_DD_OTLP_ENDPOINT = "http://localhost:4318"


def configure_datadog_export(
    settings: Optional[AppSettings] = None,
) -> bool:
    """Set OTEL environment variables for DataDog OTLP export.

    Call early in application startup - before the OTEL SDK is
    initialised - so the exporter picks up the correct endpoint.

    Returns ``True`` if DataDog export was configured.
    """
    settings = settings or AppSettings()

    if not settings.datadog_api_key:
        logger.info("DataDog API key not set - export disabled")
        return False

    # Disable AgentCore ADOT auto-instrumentation to avoid conflicts
    os.environ.setdefault("DISABLE_ADOT_OBSERVABILITY", "true")

    # Point OTEL exporters at the DataDog OTLP intake
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", _DD_OTLP_ENDPOINT)
    os.environ.setdefault("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")

    # DataDog-specific resource attributes
    os.environ.setdefault("OTEL_SERVICE_NAME", "agentic-tax-calculator")
    os.environ.setdefault(
        "OTEL_RESOURCE_ATTRIBUTES",
        "deployment.environment=production,"
        "service.version=1.0.0,"
        f"dd.api_key={settings.datadog_api_key}",
    )

    # DataDog requires the API key header for direct OTLP ingest
    os.environ.setdefault(
        "OTEL_EXPORTER_OTLP_HEADERS",
        f"DD-API-KEY={settings.datadog_api_key}",
    )

    logger.info("DataDog OTLP export configured (endpoint=%s)", _DD_OTLP_ENDPOINT)
    return True
