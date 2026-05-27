"""GraphQL data provider - drop-in replacement for MockDataProvider.

Uses GraphQLClient to fetch data from the accounting GraphQL API.
Returns data in the same shape as MockDataProvider so the MCP tools
don't need to change their response mapping logic.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.graphql.client import GraphQLClient
from src.graphql import queries

logger = logging.getLogger(__name__)


class GraphQLDataProvider:
    """Fetches business data from the accounting GraphQL API.

    Drop-in replacement for MockDataProvider. Same method signatures,
    same return shapes.
    """

    def __init__(self, endpoint: str, token: Optional[str] = None):
        """Initialize with GraphQL endpoint and optional auth token.

        Args:
            endpoint: Full URL to the GraphQL endpoint.
            token: Bearer token for auth passthrough. Can also be
                   passed per-call if token varies by request.
        """
        self._client = GraphQLClient(endpoint=endpoint)
        self._token = token

    def get_business_info(
        self, business_id: str, tax_year: int, token: Optional[str] = None
    ) -> dict[str, Any]:
        """Fetch business metadata. Returns same shape as mock JSON."""
        data = self._client.execute(
            queries.GET_BUSINESS_INFO,
            variables={"businessId": business_id, "taxYear": tax_year},
            token=token or self._token,
        )
        # Wrap in the same structure as mock data
        return {"business": data["business"]}

    def get_income(
        self, business_id: str, tax_year: int, token: Optional[str] = None
    ) -> dict[str, Any]:
        """Fetch income (CREDIT accounts). Returns same shape as mock JSON."""
        data = self._client.execute(
            queries.GET_INCOME,
            variables={"businessId": business_id, "taxYear": tax_year},
            token=token or self._token,
        )
        return {"profitAndLoss": data["profitAndLoss"]}

    def get_expenses(
        self, business_id: str, tax_year: int, token: Optional[str] = None
    ) -> dict[str, Any]:
        """Fetch expenses (DEBIT accounts). Returns same shape as mock JSON."""
        data = self._client.execute(
            queries.GET_EXPENSES,
            variables={"businessId": business_id, "taxYear": tax_year},
            token=token or self._token,
        )
        return {"profitAndLoss": data["profitAndLoss"]}

    def get_assets(
        self, business_id: str, tax_year: int, token: Optional[str] = None
    ) -> dict[str, Any]:
        """Fetch HST/GST tax accounts. Returns same shape as mock JSON."""
        data = self._client.execute(
            queries.GET_ASSETS,
            variables={"businessId": business_id, "taxYear": tax_year},
            token=token or self._token,
        )
        return {"taxAccounts": data["taxAccounts"]}

    def get_tax_rules(
        self, jurisdiction: str, tax_year: int, token: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """Fetch tax rules for a jurisdiction. Returns same shape as mock JSON."""
        data = self._client.execute(
            queries.GET_TAX_RULES,
            variables={"jurisdiction": jurisdiction, "taxYear": tax_year},
            token=token or self._token,
        )
        rules = data.get("taxRules")
        if not rules:
            return None
        return rules
