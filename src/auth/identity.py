"""Authentication integration - configurable auth strategies.

Supports multiple auth modes via TAX_CALC_AUTH_MODE:
  - passthrough: Forward bearer token from request to GraphQL. No
    validation on agent side - GraphQL handles it. Default mode.
  - okta: Okta OAuth 2.0 via AgentCore Identity (client-credentials).
  - auth0: Auth0 OAuth 2.0 (future - planned).
  - agentcore_identity: AgentCore Identity with registered IDP.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional, Protocol

import httpx

from src.config.settings import AppSettings, AuthMode

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails after refresh attempt."""


@dataclass
class TokenInfo:
    """Cached OAuth 2.0 token with expiry tracking."""

    access_token: str = ""
    token_type: str = "Bearer"
    expires_at: float = 0.0
    refresh_token: str = ""
    scope: str = ""


class IdentityClient(Protocol):
    """Protocol for auth clients - all modes implement this."""

    def get_token(self) -> str: ...
    def get_auth_header(self) -> dict[str, str]: ...


class PassthroughIdentityClient:
    """Forward bearer token from incoming request to downstream APIs.

    No token acquisition or validation - the token is passed through
    to GraphQL, which handles all authorization. This is the default
    for architectures where GraphQL owns auth.
    """

    def __init__(self) -> None:
        self._token: str = ""

    def set_token(self, token: str) -> None:
        """Set the bearer token from the incoming request."""
        self._token = token

    def get_token(self) -> str:
        return self._token

    def get_auth_header(self) -> dict[str, str]:
        if not self._token:
            return {}
        return {"Authorization": f"Bearer {self._token}"}


class OktaIdentityClient:
    """OAuth 2.0 client for Okta via AgentCore Identity.

    Supports two flows:
    1. Client-credentials (service-to-service)
    2. On-behalf-of-user (delegated user context)

    Token refresh is automatic - callers just call ``get_token()``
    and receive a valid access token.
    """

    _REFRESH_BUFFER_SECONDS = 60

    def __init__(self, settings: Optional[AppSettings] = None) -> None:
        self._settings = settings or AppSettings()
        self._token: Optional[TokenInfo] = None

        self._okta_domain = self._settings.okta_domain
        self._client_id = self._settings.okta_client_id
        self._client_secret = self._settings.okta_client_secret

        if self._okta_domain:
            self._token_url = (
                f"https://{self._okta_domain}/oauth2/default/v1/token"
            )
        else:
            self._token_url = ""

    def get_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        if not self._okta_domain:
            logger.debug("No Okta domain configured - returning empty token")
            return ""

        if self._token and not self._is_expired(self._token):
            return self._token.access_token

        if self._token and self._token.refresh_token:
            try:
                self._refresh()
                return self._token.access_token
            except AuthenticationError:
                logger.warning("Token refresh failed, attempting fresh auth")

        self._authenticate()
        return self._token.access_token

    def get_token_on_behalf_of(self, user_token: str) -> str:
        """Exchange a user token for a delegated access token."""
        if not self._okta_domain:
            return ""

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    self._token_url,
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "subject_token": user_token,
                        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                        "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                    },
                )
                resp.raise_for_status()
                return resp.json().get("access_token", "")

        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            msg = f"On-behalf-of token exchange failed: {exc}"
            logger.error(msg)
            raise AuthenticationError(msg) from exc

    def get_auth_header(self) -> dict[str, str]:
        token = self.get_token()
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def _authenticate(self) -> None:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    self._token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "scope": "openid",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                self._token = TokenInfo(
                    access_token=data["access_token"],
                    token_type=data.get("token_type", "Bearer"),
                    expires_at=time.time() + data.get("expires_in", 3600),
                    refresh_token=data.get("refresh_token", ""),
                    scope=data.get("scope", ""),
                )
                logger.info("Acquired fresh Okta access token")

        except (httpx.HTTPStatusError, httpx.RequestError, KeyError) as exc:
            msg = f"Authentication failed for Okta domain '{self._okta_domain}': {exc}"
            logger.error(msg)
            raise AuthenticationError(msg) from exc

    def _refresh(self) -> None:
        if not self._token or not self._token.refresh_token:
            raise AuthenticationError("No refresh token available")

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    self._token_url,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "refresh_token": self._token.refresh_token,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                self._token = TokenInfo(
                    access_token=data["access_token"],
                    token_type=data.get("token_type", "Bearer"),
                    expires_at=time.time() + data.get("expires_in", 3600),
                    refresh_token=data.get(
                        "refresh_token", self._token.refresh_token
                    ),
                    scope=data.get("scope", ""),
                )
                logger.info("Refreshed Okta access token")

        except (httpx.HTTPStatusError, httpx.RequestError, KeyError) as exc:
            msg = f"Token refresh failed: {exc}"
            logger.error(msg)
            raise AuthenticationError(msg) from exc

    def _is_expired(self, token: TokenInfo) -> bool:
        return time.time() >= (token.expires_at - self._REFRESH_BUFFER_SECONDS)


def create_identity_client(
    settings: Optional[AppSettings] = None,
) -> PassthroughIdentityClient | OktaIdentityClient:
    """Factory - returns the right auth client based on TAX_CALC_AUTH_MODE."""
    settings = settings or AppSettings()

    if settings.auth_mode == AuthMode.PASSTHROUGH:
        logger.info("Auth mode: passthrough - token forwarded to GraphQL")
        return PassthroughIdentityClient()

    if settings.auth_mode == AuthMode.OKTA:
        logger.info("Auth mode: okta - using Okta client-credentials flow")
        return OktaIdentityClient(settings)

    if settings.auth_mode == AuthMode.AUTH0:
        # Auth0 support planned - placeholder for future
        logger.warning("Auth mode: auth0 - not yet implemented, falling back to passthrough")
        return PassthroughIdentityClient()

    if settings.auth_mode == AuthMode.AGENTCORE_IDENTITY:
        logger.warning("Auth mode: agentcore_identity - not yet implemented, falling back to passthrough")
        return PassthroughIdentityClient()

    return PassthroughIdentityClient()
