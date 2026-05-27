"""MCP tool: get_expenses - retrieve DEBIT accounts and total expenses.

Routes to MockDataProvider or GraphQL based on DataSourceMode config.
"""

from src.config.settings import AppSettings, DataSourceMode
from src.mock.provider import MockDataProvider
from src.graphql.provider import GraphQLDataProvider
from src.mcp.tools.schemas import ExpenseResponse, AccountEntry


def _get_settings() -> AppSettings:
    return AppSettings()


def get_expenses(
    business_id: str,
    tax_year: int,
    accounting_method: str = "cash",
) -> dict:
    """Retrieve profit-and-loss DEBIT accounts and calculated expenses.

    Args:
        business_id: Business identifier.
        tax_year: Tax year to query.
        accounting_method: 'cash' or 'accrual' (determines upstream reporting).

    Returns:
        dict with accounts list and total_expenses.
    """
    settings = _get_settings()

    if settings.data_source_mode == DataSourceMode.MOCK:
        provider = MockDataProvider()
        raw = provider.get_expenses(business_id, tax_year)
    else:
        provider = GraphQLDataProvider(endpoint=settings.graphql_endpoint)
        raw = provider.get_expenses(business_id, tax_year)

    pnl = raw.get("profitAndLoss", raw)
    accounts = [
        AccountEntry(
            name=a["name"],
            account_type=a["type"],
            amount=a["amount"],
        )
        for a in pnl.get("accounts", [])
        if a.get("type") == "DEBIT"
    ]

    response = ExpenseResponse(
        business_id=business_id,
        tax_year=tax_year,
        accounting_method=accounting_method.lower(),
        accounts=accounts,
        total_expenses=pnl.get("totalExpenses", 0.0),
    )
    return response.model_dump()
