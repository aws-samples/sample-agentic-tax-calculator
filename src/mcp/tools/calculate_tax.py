"""MCP tool: calculate_tax - invoke DeterministicTaxEngine.

This tool aggregates financial data and computes the full Canadian
tax breakdown (federal, provincial, CPP, EI).
"""

from typing import Optional

from src.tax_engine.engine import DeterministicTaxEngine
from src.tax_engine.interface import TaxInput
from src.mcp.tools.schemas import TaxBreakdownResponse, BracketDetail


def calculate_tax(
    revenue: float,
    expenses: float,
    jurisdiction: str,
    accounting_method: str,
    tax_year: int,
    assets: Optional[dict] = None,
) -> dict:
    """Invoke the deterministic tax engine with aggregated financial data.

    Args:
        revenue: Total revenue (from Income Agent).
        expenses: Total expenses (from Expense Agent).
        jurisdiction: Province/territory code (e.g. 'ON').
        accounting_method: 'cash' or 'accrual'.
        tax_year: Tax year for bracket lookup.
        assets: Optional HST/GST asset data.

    Returns:
        dict with full tax breakdown including bracket details.

    Raises:
        ValueError: If jurisdiction is unsupported or accounting_method invalid.
    """
    engine = DeterministicTaxEngine()

    tax_input = TaxInput(
        revenue=revenue,
        expenses=expenses,
        jurisdiction=jurisdiction,
        accounting_method=accounting_method,
        tax_year=tax_year,
        assets=assets or {},
    )

    result = engine.calculate(tax_input)

    bracket_details = [
        BracketDetail(
            level=d["level"],
            min_income=d["min_income"],
            max_income=d.get("max_income"),
            rate=d["rate"],
            taxable_amount=d["taxable_amount"],
            tax=d["tax"],
        )
        for d in result.bracket_details
    ]

    response = TaxBreakdownResponse(
        profit=result.profit,
        federal_tax=result.federal_tax,
        provincial_tax=result.provincial_tax,
        cpp_contribution=result.cpp_contribution,
        ei_premium=result.ei_premium,
        total_tax=result.total_tax,
        jurisdiction=result.jurisdiction,
        accounting_method=result.accounting_method,
        tax_year=result.tax_year,
        bracket_details=bracket_details,
    )
    return response.model_dump()
