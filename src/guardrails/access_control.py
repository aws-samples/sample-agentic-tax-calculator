"""Access control guardrail - per-agent tool authorization.

Implements the AgentCore Gateway interceptor pattern for access control.
Gateway interceptors are REQUEST interceptors that execute before the
gateway calls the target.  This module validates agent permissions based
on a static permissions matrix (analogous to JWT claims validation in
the Gateway interceptor model) and controls access at the tool level.

Access control levels supported:
  - Gateway-level:  all requests pass through ``enforce()``
  - Tool-level:     each agent is mapped to its authorized tool set
  - Operation-level: ``enforce()`` checks agent + tool pair

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AccessDeniedError(Exception):
    """Raised when an agent attempts an unauthorized tool invocation."""

    def __init__(self, agent_name: str, tool_name: str, message: str | None = None):
        self.agent_name = agent_name
        self.tool_name = tool_name
        self.message = message or (
            f"Agent '{agent_name}' is not authorized to invoke tool '{tool_name}'"
        )
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# Violation record
# ---------------------------------------------------------------------------

@dataclass
class AccessViolation:
    """Immutable record of a blocked access attempt."""

    agent_name: str
    tool_name: str
    timestamp: str
    message: str


# ---------------------------------------------------------------------------
# Permissions matrix
# ---------------------------------------------------------------------------

AGENT_TOOL_PERMISSIONS: dict[str, list[str]] = {
    "Business Workflow": ["get_business_info"],
    "Income Workflow": ["get_income"],
    "Expense Workflow": ["get_expenses"],
    "Asset Workflow": ["get_assets"],
    "Tax Workflow": ["calculate_tax", "get_tax_rules"],
}


# ---------------------------------------------------------------------------
# AccessControlGuardrail
# ---------------------------------------------------------------------------

class AccessControlGuardrail:
    """Enforces per-agent tool access policies.

    Modelled after the AgentCore Gateway interceptor pattern:
    a REQUEST interceptor that validates the caller's identity (agent
    name, analogous to JWT ``sub`` claim) against a permissions matrix
    before the gateway routes the request to the MCP tool.

    Usage::

        guardrail = AccessControlGuardrail()
        guardrail.enforce("IncomeAgent", "get_income")      # OK
        guardrail.enforce("IncomeAgent", "calculate_tax")    # raises AccessDeniedError
    """

    def __init__(
        self,
        permissions: dict[str, list[str]] | None = None,
    ) -> None:
        self._permissions = permissions or AGENT_TOOL_PERMISSIONS
        self._violations: list[AccessViolation] = []

    # -- public API ----------------------------------------------------------

    def check_access(self, agent_name: str, tool_name: str) -> bool:
        """Return True if *agent_name* is authorized to call *tool_name*."""
        allowed = self._permissions.get(agent_name, [])
        return tool_name in allowed

    def enforce(self, agent_name: str, tool_name: str) -> None:
        """Raise ``AccessDeniedError`` if the agent is not authorized.

        Every denied attempt is logged at WARNING level and recorded in
        the internal violations list for audit purposes.
        """
        if self.check_access(agent_name, tool_name):
            return

        violation = AccessViolation(
            agent_name=agent_name,
            tool_name=tool_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            message=(
                f"ACCESS DENIED: Agent '{agent_name}' attempted "
                f"unauthorized invocation of tool '{tool_name}'"
            ),
        )
        self._violations.append(violation)
        logger.warning(violation.message)

        raise AccessDeniedError(agent_name, tool_name)

    @property
    def violations(self) -> list[AccessViolation]:
        """Return a copy of all recorded access violations."""
        return list(self._violations)

    def get_allowed_tools(self, agent_name: str) -> list[str]:
        """Return the list of tools *agent_name* is authorized to use."""
        return list(self._permissions.get(agent_name, []))
