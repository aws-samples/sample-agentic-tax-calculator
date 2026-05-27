"""Tax Agent tools - deterministic tax calculation engine."""

from langchain_core.tools import tool
from shared.tax_engine import calculate_tax as _calculate_tax
from shared.tax_engine import SUPPORTED_JURISDICTIONS


@tool
def calculate_tax(
    revenue: float,
    expenses: float,
    jurisdiction: str,
    accounting_method: str = "cash",
) -> dict:
    """Calculate Canadian tax liability using the deterministic tax engine.

    Computes federal tax, provincial tax, CPP, and EI based on 2024 CRA rates.
    Returns a full breakdown with bracket details.

    Args:
        revenue: Total business revenue
        expenses: Total business expenses
        jurisdiction: Province code (ON, BC, AB, QC)
        accounting_method: 'cash' or 'accrual'
    """
    try:
        return _calculate_tax(
            revenue=revenue,
            expenses=expenses,
            jurisdiction=jurisdiction,
            accounting_method=accounting_method,
        )
    except ValueError as e:
        return {"error": str(e)}


@tool
def get_supported_jurisdictions() -> list[str]:
    """List all supported Canadian provinces/territories for tax calculation."""
    return SUPPORTED_JURISDICTIONS
