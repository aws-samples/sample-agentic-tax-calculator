"""MCP tool: get_business_info - retrieve business metadata.

Routes to MockDataProvider or GraphQL based on DataSourceMode config.
"""

from src.config.settings import AppSettings, DataSourceMode
from src.mock.provider import MockDataProvider
from src.graphql.provider import GraphQLDataProvider
from src.mcp.tools.schemas import BusinessInfoResponse


def _get_settings() -> AppSettings:
    """Lazy-load settings to avoid import-time env var resolution."""
    return AppSettings()


def get_business_info(business_id: str, tax_year: int) -> dict:
    """Retrieve business metadata including accounting method and jurisdiction.

    Args:
        business_id: Business identifier (e.g. 'BIZ001').
        tax_year: Tax year to query.

    Returns:
        dict with business_id, business_name, accounting_method,
        jurisdiction, fiscal_year_end, and business_type.

    Raises:
        KeyError: If business_id is not found.
    """
    settings = _get_settings()

    if settings.data_source_mode == DataSourceMode.MOCK:
        provider = MockDataProvider()
        raw = provider.get_business_info(business_id, tax_year)
    else:
        provider = GraphQLDataProvider(endpoint=settings.graphql_endpoint)
        raw = provider.get_business_info(business_id, tax_year)

    biz = raw.get("business", raw)
    response = BusinessInfoResponse(
        business_id=biz.get("id", business_id),
        business_name=biz.get("name", ""),
        accounting_method=biz.get("accountingMethod", "").lower(),
        jurisdiction=biz.get("jurisdiction", ""),
        fiscal_year_end=biz.get("fiscalYearEnd", ""),
        business_type=biz.get("businessType", ""),
    )
    return response.model_dump()
