"""Business Agent - retrieves and validates business metadata.

Runs first in the workflow.  Stores accounting_method and jurisdiction
in SharedState so downstream agents have the context they need.

Requirements: 7.1, 7.2, 7.3
"""

from __future__ import annotations

import logging

from src.agents.base import BaseAgent
from src.mcp.tools.business_info import get_business_info
from src.orchestrator.state import SharedState

logger = logging.getLogger(__name__)


class BusinessAgent(BaseAgent):
    agent_name = "Business Workflow"
    allowed_tools = ["get_business_info"]

    def execute(self, state: SharedState) -> SharedState:
        """Call get_business_info, validate completeness, update state."""
        self.validate_tool_access("get_business_info")

        business_id = state.get("business_id", "")
        tax_year = state.get("tax_year", 2024)

        try:
            result = get_business_info(business_id, tax_year)
        except Exception as exc:
            logger.error("BusinessAgent failed: %s", exc)
            return {
                "status": "failed",
                "error": f"BusinessAgent: {exc}",
            }

        accounting_method = result.get("accounting_method", "")
        jurisdiction = result.get("jurisdiction", "")

        # Validate completeness - both fields are required
        if not accounting_method or not jurisdiction:
            missing = []
            if not accounting_method:
                missing.append("accounting_method")
            if not jurisdiction:
                missing.append("jurisdiction")
            msg = (
                f"BusinessAgent: incomplete metadata - missing "
                f"{', '.join(missing)}"
            )
            logger.error(msg)
            return {"status": "failed", "error": msg}

        logger.info(
            "BusinessAgent: %s | method=%s jurisdiction=%s",
            result.get("business_name", ""),
            accounting_method,
            jurisdiction,
        )

        return {
            "business_name": result.get("business_name", ""),
            "accounting_method": accounting_method,
            "jurisdiction": jurisdiction,
            "fiscal_year_end": result.get("fiscal_year_end", ""),
            "business_type": result.get("business_type", ""),
            "business_metadata": result,
            "status": "running",
        }


def business_node(state: SharedState) -> SharedState:
    """LangGraph node function for the Business Agent."""
    return BusinessAgent().execute(state)
