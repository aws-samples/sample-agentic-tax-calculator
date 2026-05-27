"""Expense Agent - retrieves expenses from profit-and-loss DEBIT accounts.

Reads accounting_method from SharedState, calls get_expenses, stores
total expenses.  Zero-data case stores 0 + warning.

Requirements: 9.1, 9.2, 9.3, 9.4
"""

from __future__ import annotations

import logging

from src.agents.base import BaseAgent
from src.mcp.tools.expenses import get_expenses
from src.orchestrator.state import SharedState

logger = logging.getLogger(__name__)


class ExpenseAgent(BaseAgent):
    agent_name = "Expense Workflow"
    allowed_tools = ["get_expenses"]

    def execute(self, state: SharedState) -> SharedState:
        """Call get_expenses, store expenses in state."""
        self.validate_tool_access("get_expenses")

        business_id = state.get("business_id", "")
        tax_year = state.get("tax_year", 2024)
        accounting_method = state.get("accounting_method", "cash")

        try:
            result = get_expenses(business_id, tax_year, accounting_method)
        except Exception as exc:
            logger.error("ExpenseAgent failed: %s", exc)
            return {
                "status": "failed",
                "error": f"ExpenseAgent: {exc}",
            }

        expenses = result.get("total_expenses", 0.0)

        if expenses == 0.0 and not result.get("accounts"):
            logger.warning(
                "ExpenseAgent: no expense data returned for %s/%s - "
                "storing expenses=0",
                business_id,
                tax_year,
            )

        logger.info("ExpenseAgent: expenses=%.2f", expenses)
        return {"expenses": expenses}


def expense_node(state: SharedState) -> SharedState:
    """LangGraph node function for the Expense Agent."""
    return ExpenseAgent().execute(state)
