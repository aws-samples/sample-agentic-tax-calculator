"""Base agent interface for the tax calculation workflow.

All agents inherit from BaseAgent which provides tool-access validation
via the AccessControlGuardrail.

Requirements: 7.1, 15.1
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.guardrails.access_control import AccessControlGuardrail
from src.orchestrator.state import SharedState


class BaseAgent(ABC):
    """Abstract base for all agents in the tax calculation workflow.

    Each agent declares its identity and the tools it is allowed to call.
    The ``validate_tool_access`` helper delegates to the access-control
    guardrail so unauthorized calls are blocked before they reach the
    MCP server.
    """

    agent_name: str = ""
    allowed_tools: list[str] = []

    def __init__(self) -> None:
        self._guardrail = AccessControlGuardrail()

    def validate_tool_access(self, tool_name: str) -> None:
        """Raise AccessDeniedError if this agent may not call *tool_name*."""
        self._guardrail.enforce(self.agent_name, tool_name)

    @abstractmethod
    def execute(self, state: SharedState) -> SharedState:
        """Run agent logic, returning an updated SharedState dict."""
        ...
