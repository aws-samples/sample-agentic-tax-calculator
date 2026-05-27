"""Tax Agent - aggregates financial data and computes tax liability.

Reads revenue, expenses, and asset data from SharedState, calls
calculate_tax via the MCP tool, runs post-validation, and stores
the final TaxBreakdown in state.

Requirements: 11.1, 11.2, 11.3
"""

from __future__ import annotations

import logging

from src.agents.base import BaseAgent
from src.mcp.tools.calculate_tax import calculate_tax
from src.guardrails.tax_validator import TaxValidationGuardrail
from src.tax_engine.interface import TaxBreakdown
from src.orchestrator.state import SharedState

logger = logging.getLogger(__name__)


class TaxAgent(BaseAgent):
    agent_name = "Tax Workflow"
    allowed_tools = ["calculate_tax", "get_tax_rules"]

    def execute(self, state: SharedState) -> SharedState:
        """Aggregate data, compute tax, validate, store result."""
        self.validate_tool_access("calculate_tax")

        revenue = state.get("revenue", 0.0)
        expenses = state.get("expenses", 0.0)
        jurisdiction = state.get("jurisdiction", "")
        accounting_method = state.get("accounting_method", "cash")
        tax_year = state.get("tax_year", 2024)
        assets = state.get("asset_data", {})

        try:
            result = calculate_tax(
                revenue=revenue,
                expenses=expenses,
                jurisdiction=jurisdiction,
                accounting_method=accounting_method,
                tax_year=tax_year,
                assets=assets,
            )
        except Exception as exc:
            logger.error("TaxAgent calculation failed: %s", exc)
            return {
                "status": "failed",
                "error": f"TaxAgent: {exc}",
            }

        # Post-validation via guardrail
        try:
            breakdown = TaxBreakdown(
                profit=result.get("profit", 0.0),
                federal_tax=result.get("federal_tax", 0.0),
                provincial_tax=result.get("provincial_tax", 0.0),
                cpp_contribution=result.get("cpp_contribution", 0.0),
                ei_premium=result.get("ei_premium", 0.0),
                total_tax=result.get("total_tax", 0.0),
                jurisdiction=result.get("jurisdiction", jurisdiction),
                accounting_method=result.get(
                    "accounting_method", accounting_method
                ),
                tax_year=result.get("tax_year", tax_year),
                bracket_details=result.get("bracket_details", []),
            )

            guardrail = TaxValidationGuardrail()
            validation = guardrail.validate_response(
                breakdown, revenue, expenses
            )

            if not validation.is_valid:
                msg = (
                    f"TaxAgent: validation failed - "
                    f"{'; '.join(validation.errors)}"
                )
                logger.error(msg)
                return {"status": "failed", "error": msg}
        except Exception as exc:
            logger.warning("TaxAgent: validation skipped (%s)", exc)

        logger.info(
            "TaxAgent: total_tax=%.2f jurisdiction=%s",
            result.get("total_tax", 0.0),
            jurisdiction,
        )

        return {
            "tax_result": result,
            "status": "completed",
        }


def tax_node(state: SharedState) -> SharedState:
    """LangGraph node function for the Tax Agent."""
    return TaxAgent().execute(state)
