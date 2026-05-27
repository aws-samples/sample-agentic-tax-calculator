"""Consolidated MCP server for the Agentic Tax Calculator.

Uses FastMCP from the official MCP SDK with @mcp.tool() decorators.
All 6 tool groups are registered on a single server instance.

Stateful mode (stateless_http=False) is used because the workflow
requires shared state across tool invocations within a session.

Entry point: mcp.run(transport="streamable-http")
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from src.mcp.tools.business_info import (
    get_business_info as _get_business_info,
)
from src.mcp.tools.income import get_income as _get_income
from src.mcp.tools.expenses import get_expenses as _get_expenses
from src.mcp.tools.assets import get_assets as _get_assets
from src.mcp.tools.calculate_tax import calculate_tax as _calculate_tax
from src.mcp.tools.tax_rules import get_tax_rules as _get_tax_rules


# Create the consolidated MCP server
mcp = FastMCP(
    "Agentic Tax Calculator",
    stateless_http=False,  # stateful - shared state across invocations
)


# ---------------------------------------------------------------------------
# Tool registrations
# ---------------------------------------------------------------------------

@mcp.tool()
def get_business_info(business_id: str, tax_year: int) -> dict:
    """Retrieve business metadata including accounting method and jurisdiction.

    Args:
        business_id: Business identifier (e.g. 'BIZ001').
        tax_year: Tax year to query (e.g. 2024).
    """
    return _get_business_info(business_id, tax_year)


@mcp.tool()
def get_income(
    business_id: str,
    tax_year: int,
    accounting_method: str = "cash",
) -> dict:
    """Retrieve profit-and-loss CREDIT accounts and total revenue.

    Args:
        business_id: Business identifier.
        tax_year: Tax year to query.
        accounting_method: 'cash' or 'accrual'.
    """
    return _get_income(business_id, tax_year, accounting_method)


@mcp.tool()
def get_expenses(
    business_id: str,
    tax_year: int,
    accounting_method: str = "cash",
) -> dict:
    """Retrieve profit-and-loss DEBIT accounts and total expenses.

    Args:
        business_id: Business identifier.
        tax_year: Tax year to query.
        accounting_method: 'cash' or 'accrual'.
    """
    return _get_expenses(business_id, tax_year, accounting_method)


@mcp.tool()
def get_assets(business_id: str, tax_year: int) -> dict:
    """Retrieve HST/GST tax account data for a business.

    Args:
        business_id: Business identifier.
        tax_year: Tax year to query.
    """
    return _get_assets(business_id, tax_year)


@mcp.tool()
def calculate_tax(
    revenue: float,
    expenses: float,
    jurisdiction: str,
    accounting_method: str,
    tax_year: int,
    assets: Optional[dict] = None,
) -> dict:
    """Compute Canadian tax breakdown using the deterministic tax engine.

    Calculates federal tax, provincial tax, CPP contributions, and EI
    premiums based on profit (revenue - expenses) and jurisdiction.

    Args:
        revenue: Total revenue from Income Agent.
        expenses: Total expenses from Expense Agent.
        jurisdiction: Province/territory code (e.g. 'ON', 'BC').
        accounting_method: 'cash' or 'accrual'.
        tax_year: Tax year for bracket lookup.
        assets: Optional HST/GST asset data from Asset Agent.
    """
    return _calculate_tax(
        revenue=revenue,
        expenses=expenses,
        jurisdiction=jurisdiction,
        accounting_method=accounting_method,
        tax_year=tax_year,
        assets=assets,
    )


@mcp.tool()
def get_tax_rules(jurisdiction: str, tax_year: int) -> dict:
    """Return CRA tax bracket rules for a Canadian jurisdiction.

    Returns federal brackets, provincial brackets, CPP rates, EI rates,
    and the basic personal amount.

    Args:
        jurisdiction: Province/territory code (e.g. 'ON', 'BC').
        tax_year: Tax year for bracket lookup.
    """
    return _get_tax_rules(jurisdiction, tax_year)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
