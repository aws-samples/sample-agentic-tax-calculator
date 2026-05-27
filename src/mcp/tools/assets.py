"""MCP tool: get_assets - retrieve HST/GST tax account data.

Routes to MockDataProvider or GraphQL based on DataSourceMode config.
"""

from src.config.settings import AppSettings, DataSourceMode
from src.mock.provider import MockDataProvider
from src.graphql.provider import GraphQLDataProvider
from src.mcp.tools.schemas import AssetResponse


def _get_settings() -> AppSettings:
    return AppSettings()


def get_assets(business_id: str, tax_year: int) -> dict:
    """Retrieve HST/GST tax account data for a business.

    Args:
        business_id: Business identifier.
        tax_year: Tax year to query.

    Returns:
        dict with hst_collected, hst_paid, net_hst, province, and rate.
    """
    settings = _get_settings()

    if settings.data_source_mode == DataSourceMode.MOCK:
        provider = MockDataProvider()
        raw = provider.get_assets(business_id, tax_year)
    else:
        provider = GraphQLDataProvider(endpoint=settings.graphql_endpoint)
        raw = provider.get_assets(business_id, tax_year)

    ta = raw.get("taxAccounts", raw)
    response = AssetResponse(
        business_id=business_id,
        tax_year=tax_year,
        hst_collected=ta.get("hstCollected", 0.0),
        hst_paid=ta.get("hstPaid", 0.0),
        net_hst=ta.get("netHst", 0.0),
        province=ta.get("province", ""),
        rate=ta.get("rate", 0.0),
    )
    return response.model_dump()
