"""Streamlit dashboard metrics exposure hook.

Exposes key workflow and tool metrics via a lightweight in-memory
store that a Streamlit dashboard can poll.  This avoids coupling the
core application to Streamlit - the dashboard reads from the shared
``MetricsStore`` singleton.

Requirements: 16.5
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from src.config.settings import AppSettings

logger = logging.getLogger(__name__)


@dataclass
class ToolMetricSnapshot:
    """Aggregated metrics for a single MCP tool."""

    invocations: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        if self.invocations == 0:
            return 0.0
        return self.total_latency_ms / self.invocations

    @property
    def error_rate(self) -> float:
        if self.invocations == 0:
            return 0.0
        return self.errors / self.invocations


@dataclass
class WorkflowMetricSnapshot:
    """Aggregated metrics for workflow executions."""

    total: int = 0
    completed: int = 0
    failed: int = 0
    total_duration_ms: float = 0.0

    @property
    def avg_duration_ms(self) -> float:
        if self.total == 0:
            return 0.0
        return self.total_duration_ms / self.total

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.completed / self.total


class MetricsStore:
    """Thread-safe in-memory metrics store for Streamlit dashboards."""

    _instance: Optional["MetricsStore"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._tool_metrics: dict[str, ToolMetricSnapshot] = defaultdict(
            ToolMetricSnapshot
        )
        self._workflow_metrics = WorkflowMetricSnapshot()
        self._recent_errors: list[dict] = []
        self._data_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "MetricsStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def record_tool_invocation(
        self, tool_name: str, latency_ms: float, success: bool,
        workflow_id: str = "",
    ) -> None:
        with self._data_lock:
            m = self._tool_metrics[tool_name]
            m.invocations += 1
            m.total_latency_ms += latency_ms
            if not success:
                m.errors += 1

    def record_workflow_execution(
        self, workflow_id: str, duration_ms: float, status: str,
    ) -> None:
        with self._data_lock:
            self._workflow_metrics.total += 1
            self._workflow_metrics.total_duration_ms += duration_ms
            if status == "completed":
                self._workflow_metrics.completed += 1
            elif status == "failed":
                self._workflow_metrics.failed += 1

    def record_error(
        self, source: str, message: str, workflow_id: str = "",
    ) -> None:
        with self._data_lock:
            self._recent_errors.append({
                "source": source,
                "message": message,
                "workflow_id": workflow_id,
                "timestamp": time.time(),
            })
            if len(self._recent_errors) > 100:
                self._recent_errors = self._recent_errors[-100:]

    def get_tool_metrics(self) -> dict[str, ToolMetricSnapshot]:
        with self._data_lock:
            return dict(self._tool_metrics)

    def get_workflow_metrics(self) -> WorkflowMetricSnapshot:
        with self._data_lock:
            return self._workflow_metrics

    def get_recent_errors(self, limit: int = 20) -> list[dict]:
        with self._data_lock:
            return list(self._recent_errors[-limit:])


def configure_streamlit_metrics(
    settings: Optional[AppSettings] = None,
) -> bool:
    """Initialise the Streamlit metrics store."""
    settings = settings or AppSettings()
    MetricsStore.instance()
    logger.info(
        "Streamlit metrics store initialised (port=%d)",
        settings.streamlit_metrics_port,
    )
    return True
