"""Business Agent tools - simulates MCP server calls."""

from langchain_core.tools import tool
from shared.mock_data import BUSINESSES


@tool
def get_business_info(business_id: str) -> dict:
    """Retrieve business metadata from the GraphQL API.

    Returns business name, accounting method (cash/accrual),
    jurisdiction (province code), fiscal year end, and business type.

    Args:
        business_id: The business ID (e.g. 'BIZ001')
    """
    if business_id not in BUSINESSES:
        return {"error": f"Business '{business_id}' not found. Available: {list(BUSINESSES.keys())}"}
    return BUSINESSES[business_id]


@tool
def list_businesses() -> list[dict]:
    """List all available businesses in the account.

    Returns a list of business summaries with ID, name, and jurisdiction.
    """
    return [
        {"business_id": k, "business_name": v["business_name"], "jurisdiction": v["jurisdiction"]}
        for k, v in BUSINESSES.items()
    ]
