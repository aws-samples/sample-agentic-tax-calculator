"""Asset Agent tools - retrieves HST/GST tax account data."""

from langchain_core.tools import tool
from shared.mock_data import ASSET_DATA


@tool
def get_assets(business_id: str) -> dict:
    """Retrieve HST/GST tax account data for a business.

    Returns HST collected, HST paid, net HST owing, province, and HST rate.

    Args:
        business_id: The business ID (e.g. 'BIZ001')
    """
    if business_id not in ASSET_DATA:
        return {"error": f"No asset data for '{business_id}'"}
    return ASSET_DATA[business_id]
