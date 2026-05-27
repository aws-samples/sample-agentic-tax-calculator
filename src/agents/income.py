"""Income Agent - retrieves revenue from profit-and-loss CREDIT accounts.

Reads accounting_method from SharedState, calls get_income, stores
total revenue.  Zero-data case stores 0 + warning.

Requirements: 8.1, 8.2, 8.3, 8.4
"""

from __future__ import annotations

import logging

from src.agents.base import BaseAgent
from src.mcp.tools.income import get_income
from src.orchestrator.state import SharedState

logger = logging.getLogger(__name__)


class IncomeAgent(BaseAgent):
    agent_name = "Income Workflow"
    allowed_tools = ["get_income"]

    def execute(self, state: SharedState) -> SharedState:
        """Call get_income, store revenue in state."""
        self.validate_tool_access("get_income")

        business_id = state.get("business_id", "")
        tax_year = state.get("tax_year", 2024)
        accounting_method = state.get("accounting_method", "cash")

        try:
            result = get_income(business_id, tax_year, accounting_method)
        except Exception as exc:
            logger.error("IncomeAgent failed: %s", exc)
            return {
                "status": "failed",
                "error": f"IncomeAgent: {exc}",
            }

        revenue = result.get("total_revenue", 0.0)

        if revenue == 0.0 and not result.get("accounts"):
            logger.warning(
                "IncomeAgent: no income data returned for %s/%s - "
                "storing revenue=0",
                business_id,
                tax_year,
            )

        logger.info("IncomeAgent: revenue=%.2f", revenue)
        return {"revenue": revenue}


def income_node(state: SharedState) -> SharedState:
    """LangGraph node function for the Income Agent."""
    return IncomeAgent().execute(state)
