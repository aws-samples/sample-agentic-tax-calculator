"""Observability metrics using OpenTelemetry conventions.

Provides per-tool invocation metrics (latency, success/failure counts)
and workflow-level metrics (duration, agent completion status).  Emits
correlation identifiers linking failures to originating workflow
sessions.

Auto-instrumentation is handled by ``opentelemetry-instrument`` at
startup.  Set ``DISABLE_ADOT_OBSERVABILITY=true`` when running outside
AgentCore (e.g. local dev with DataDog).

Requirements: 16.1, 16.2, 16.6
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Generator, Optional

from opentelemetry import metrics, trace
from opentelemetry.trace import StatusCode

logger = logging.getLogger(__name__)

# -- Meter and tracer singletons -------------------------------------------

_tracer = trace.get_tracer("agentic-tax-calculator")
_meter = metrics.get_meter("agentic-tax-calculator")

# -- Per-tool invocation metrics -------------------------------------------

_tool_invocation_counter = _meter.create_counter(
    name="tool.invocations",
    description="Number of MCP tool invocations",
    unit="1",
)

_tool_error_counter = _meter.create_counter(
    name="tool.errors",
    description="Number of failed MCP tool invocations",
    unit="1",
)

_tool_latency_histogram = _meter.create_histogram(
    name="tool.latency",
    description="Latency of MCP tool invocations",
    unit="ms",
)

# -- Workflow-level metrics ------------------------------------------------

_workflow_duration_histogram = _meter.create_histogram(
    name="workflow.duration",
    description="Total duration of a tax calculation workflow",
    unit="ms",
)

_workflow_counter = _meter.create_counter(
    name="workflow.executions",
    description="Number of workflow executions",
    unit="1",
)

_agent_completion_counter = _meter.create_counter(
    name="agent.completions",
    description="Number of agent completions by status",
    unit="1",
)


@contextmanager
def instrument_tool(
    tool_name: str,
    workflow_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Generator[dict[str, Any], None, None]:
    """Context manager that instruments an MCP tool invocation.

    Usage::

        with instrument_tool("get_income", workflow_id="abc") as ctx:
            result = await get_income(...)
            ctx["result"] = result
    """
    attributes: dict[str, str] = {"tool.name": tool_name}
    if workflow_id:
        attributes["workflow.id"] = workflow_id
    if session_id:
        attributes["session.id"] = session_id

    ctx: dict[str, Any] = {}
    start = time.monotonic()

    with _tracer.start_as_current_span(
        f"tool.{tool_name}", attributes=attributes
    ) as span:
        try:
            _tool_invocation_counter.add(1, attributes)
            yield ctx

            elapsed_ms = (time.monotonic() - start) * 1000
            _tool_latency_histogram.record(elapsed_ms, attributes)
            span.set_status(StatusCode.OK)

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            _tool_latency_histogram.record(elapsed_ms, attributes)
            _tool_error_counter.add(1, attributes)
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            logger.error(
                "Tool %s failed (workflow=%s): %s",
                tool_name, workflow_id, exc,
            )
            raise


@contextmanager
def instrument_workflow(
    workflow_id: str,
    session_id: Optional[str] = None,
) -> Generator[dict[str, Any], None, None]:
    """Context manager that instruments a full tax workflow execution."""
    attributes: dict[str, str] = {"workflow.id": workflow_id}
    if session_id:
        attributes["session.id"] = session_id

    ctx: dict[str, Any] = {}
    start = time.monotonic()

    with _tracer.start_as_current_span(
        "workflow.tax_calculation", attributes=attributes
    ) as span:
        try:
            _workflow_counter.add(1, {**attributes, "status": "started"})
            yield ctx

            elapsed_ms = (time.monotonic() - start) * 1000
            _workflow_duration_histogram.record(elapsed_ms, attributes)
            _workflow_counter.add(1, {**attributes, "status": "completed"})
            span.set_status(StatusCode.OK)

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            _workflow_duration_histogram.record(elapsed_ms, attributes)
            _workflow_counter.add(1, {**attributes, "status": "failed"})
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            logger.error("Workflow %s failed: %s", workflow_id, exc)
            raise


def record_agent_completion(
    agent_id: str,
    status: str,
    workflow_id: Optional[str] = None,
) -> None:
    """Record an agent completion event."""
    attributes: dict[str, str] = {
        "agent.id": agent_id,
        "agent.status": status,
    }
    if workflow_id:
        attributes["workflow.id"] = workflow_id

    _agent_completion_counter.add(1, attributes)

    if status == "failed":
        logger.warning("Agent %s failed in workflow %s", agent_id, workflow_id)
