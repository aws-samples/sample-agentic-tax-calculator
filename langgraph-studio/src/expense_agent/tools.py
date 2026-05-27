"""Expense Agent tools - retrieves expense data."""

from langchain_core.tools import tool
from shared.mock_data import EXPENSE_DATA


@tool
def get_expenses(business_id: str) -> dict:
    """Retrieve profit-and-loss DEBIT accounts and total expenses.

    Returns a list of expense accounts with amounts and the total expenses.

    Args:
        business_id: The business ID (e.g. 'BIZ001')
    """
    if business_id not in EXPENSE_DATA:
        return {"error": f"No expense data for '{business_id}'"}
    return EXPENSE_DATA[business_id]
