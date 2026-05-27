"""MCP tool: get_income - retrieve CREDIT accounts and total revenue.

Routes to MockDataProvider or GraphQL based on DataSourceMode config.
"""

from src.config.settings import AppSettings, DataSourceMode
from src.mock.provider import MockDataProvider
from src.graphql.provider import GraphQLDataProvider
from src.mcp.tools.schemas import IncomeResponse, AccountEntry


def _get_settings() -> AppSettings:
    return AppSettings()


def get_income(
    business_id: str,
    tax_year: int,
    accounting_method: str = "cash",
) -> dict:
    """Retrieve profit-and-loss CREDIT accounts and calculated revenue.

    Args:
        business_id: Business identifier.
        tax_year: Tax year to query.
        accounting_method: 'cash' or 'accrual' (determines upstream reporting).

    Returns:
        dict with accounts list and total_revenue.
    """
    settings = _get_settings()

    if settings.data_source_mode == DataSourceMode.MOCK:
        provider = MockDataProvider()
        raw = provider.get_income(business_id, tax_year)
    else:
        provider = GraphQLDataProvider(endpoint=settings.graphql_endpoint)
        raw = provider.get_income(business_id, tax_year)

    pnl = raw.get("profitAndLoss", raw)
    accounts = [
        AccountEntry(
            name=a["name"],
            account_type=a["type"],
            amount=a["amount"],
        )
        for a in pnl.get("accounts", [])
        if a.get("type") == "CREDIT"
    ]

    response = IncomeResponse(
        business_id=business_id,
        tax_year=tax_year,
        accounting_method=accounting_method.lower(),
        accounts=accounts,
        total_revenue=pnl.get("totalRevenue", 0.0),
    )
    return response.model_dump()
