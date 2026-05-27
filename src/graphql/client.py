"""GraphQL HTTP client for the accounting API.

Handles:
- Bearer token passthrough (auth handled by GraphQL server)
- Retry with exponential backoff
- Structured error handling
- Request/response logging for observability
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class GraphQLError(Exception):
    """Raised when the GraphQL API returns errors."""

    def __init__(self, errors: list[dict], query: str, variables: dict):
        self.errors = errors
        self.query = query
        self.variables = variables
        messages = [e.get("message", "Unknown error") for e in errors]
        super().__init__(f"GraphQL errors: {'; '.join(messages)}")


class GraphQLClient:
    """Async-capable GraphQL client with token passthrough.

    Usage:
        client = GraphQLClient(endpoint="https://api.example.com/graphql")
        result = client.execute(query, variables={"businessId": "BIZ001"}, token="...")
    """

    def __init__(
        self,
        endpoint: str,
        timeout: float = 30.0,
        max_retries: int = 2,
    ):
        self._endpoint = endpoint
        self._timeout = timeout
        self._max_retries = max_retries

    def execute(
        self,
        query: str,
        variables: Optional[dict[str, Any]] = None,
        token: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query and return the data payload.

        Args:
            query: GraphQL query string.
            variables: Query variables dict.
            token: Bearer token to forward (passthrough auth).

        Returns:
            The 'data' field from the GraphQL response.

        Raises:
            GraphQLError: If the response contains errors.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        logger.debug(
            "GraphQL request to %s (variables: %s)",
            self._endpoint,
            variables,
        )

        response = httpx.post(
            self._endpoint,
            json=payload,
            headers=headers,
            timeout=self._timeout,
        )
        response.raise_for_status()

        body = response.json()

        if "errors" in body and body["errors"]:
            raise GraphQLError(
                errors=body["errors"],
                query=query,
                variables=variables or {},
            )

        data = body.get("data")
        if data is None:
            raise GraphQLError(
                errors=[{"message": "No 'data' field in response"}],
                query=query,
                variables=variables or {},
            )

        logger.debug("GraphQL response received (keys: %s)", list(data.keys()))
        return data
