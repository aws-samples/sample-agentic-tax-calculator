"""Income Agent tools - retrieves revenue data."""

from langchain_core.tools import tool
from shared.mock_data import INCOME_DATA


@tool
def get_income(business_id: str) -> dict:
    """Retrieve profit-and-loss CREDIT accounts and total revenue.

    Returns a list of income accounts with amounts and the total revenue.

    Args:
        business_id: The business ID (e.g. 'BIZ001')
    """
    if business_id not in INCOME_DATA:
        return {"error": f"No income data for '{business_id}'"}
    return INCOME_DATA[business_id]
