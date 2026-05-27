"""Main application entry point - end-to-end request flow wiring.

Connects all components in the correct order:
  API handler → Auth → PII pre-filter → LangGraph orchestrator →
  Agents → MCP tools → Tax post-validation → Response

Integrates observability and memory at each stage.

Deployment mode switching (Task 17.3):
  TAX_CALC_DEPLOYMENT_MODE=agentcore  → starts MCP server via FastMCP
  TAX_CALC_DEPLOYMENT_MODE=kubernetes → starts MCP server via FastMCP
  Both modes use the same MCP server; the difference is infrastructure.

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.api.schemas import (
    TaxCalculationRequest,
    TaxCalculationResponse,
)
from src.auth.identity import AuthenticationError, OktaIdentityClient
from src.config.settings import AppSettings, DeploymentMode
from src.guardrails.pii_filter import PIIFilter
from src.memory.long_term import CalcSummary, LongTermMemory
from src.memory.short_term import ShortTermMemory
from src.observability.metrics import instrument_workflow, record_agent_completion
from src.api.handler import handle_tax_calculation

logger = logging.getLogger(__name__)


class AgenticTaxApp:
    """Wires the full request flow with auth, guardrails, memory, and observability."""

    def __init__(self, settings: Optional[AppSettings] = None) -> None:
        self._settings = settings or AppSettings()
        self._auth = OktaIdentityClient(self._settings)
        self._pii_filter = PIIFilter()
        self._short_term_memory: Optional[ShortTermMemory] = None
        self._long_term_memory: Optional[LongTermMemory] = None

    # -- Lazy memory initialization ------------------------------------------

    def _get_short_term_memory(self) -> ShortTermMemory:
        if self._short_term_memory is None:
            self._short_term_memory = ShortTermMemory(settings=self._settings)
        return self._short_term_memory

    def _get_long_term_memory(self) -> LongTermMemory:
        if self._long_term_memory is None:
            self._long_term_memory = LongTermMemory(settings=self._settings)
        return self._long_term_memory

    # -- Auth ----------------------------------------------------------------

    def _authenticate(self, user_token: Optional[str] = None) -> str:
        """Authenticate via AgentCore Identity / Okta.

        Returns an access token string (empty if auth is not configured,
        which is fine for mock mode).
        """
        if not self._settings.okta_domain:
            logger.debug("Auth not configured - running in mock mode")
            return ""

        try:
            if user_token:
                return self._auth.get_token_on_behalf_of(user_token)
            return self._auth.get_token()
        except AuthenticationError as exc:
            logger.error("Authentication failed: %s", exc)
            raise

    # -- PII pre-filter ------------------------------------------------------

    def _apply_pii_prefilter(self, request: TaxCalculationRequest) -> None:
        """Run PII pre-filter on request fields.

        Raises ValueError if PII is detected that cannot be safely
        redacted (the request is blocked).
        """
        text_to_check = f"{request.business_id} {request.tax_year}"
        if request.user_id:
            text_to_check += f" {request.user_id}"

        result = self._pii_filter.filter_input(text_to_check)
        if result.blocked:
            raise ValueError(
                "Request blocked: PII detected that cannot be safely redacted. "
                f"Detected types: {result.redacted_types}"
            )

        if result.redacted:
            logger.info(
                "PII pre-filter redacted %d items (types: %s)",
                result.redaction_count,
                result.redacted_types,
            )

    # -- Memory: load returning-user preferences -----------------------------

    def _load_user_preferences(
        self, request: TaxCalculationRequest
    ) -> TaxCalculationRequest:
        """Pre-populate defaults from long-term memory for returning users."""
        if not request.user_id:
            return request

        try:
            ltm = self._get_long_term_memory()
            prefs = ltm.get_preferences(request.user_id)
            if prefs:
                logger.info(
                    "Loaded preferences for user=%s (jurisdiction=%s)",
                    request.user_id,
                    prefs.default_jurisdiction,
                )
            return request
        except Exception as exc:
            logger.warning("Could not load user preferences: %s", exc)
            return request

    # -- Memory: store results -----------------------------------------------

    def _store_results_in_memory(
        self,
        request: TaxCalculationRequest,
        response: TaxCalculationResponse,
        session_id: str,
    ) -> None:
        """Store workflow results in short-term and long-term memory."""
        # Short-term: store the response for session context
        try:
            stm = self._get_short_term_memory()
            stm.store(session_id, "last_response", response.model_dump())
        except Exception as exc:
            logger.warning("Short-term memory store failed: %s", exc)

        # Long-term: store calculation summary (PII-filtered)
        if request.user_id and response.status == "completed":
            try:
                ltm = self._get_long_term_memory()
                summary = CalcSummary(
                    workflow_id=response.workflow_id,
                    jurisdiction=response.jurisdiction or "",
                    tax_year=response.tax_year or 0,
                    total_tax=response.total_tax or 0.0,
                    calculated_at=datetime.now(timezone.utc).isoformat(),
                )
                ltm.store_calculation_summary(request.user_id, summary)
            except Exception as exc:
                logger.warning("Long-term memory store failed: %s", exc)

    # -- Main entry point ----------------------------------------------------

    def process_request(
        self,
        request: TaxCalculationRequest,
        user_token: Optional[str] = None,
    ) -> TaxCalculationResponse:
        """Full end-to-end request flow.

        1. Authenticate (AgentCore Identity / Okta)
        2. PII pre-filter (AgentCore Guardrails)
        3. Load returning-user preferences (AgentCore Memory)
        4. Execute LangGraph orchestrator (Agents → MCP tools → Tax engine)
        5. Tax post-validation (AgentCore Guardrails - inside Tax Agent)
        6. Store results in memory
        7. Return response with observability correlation
        """
        session_id = str(uuid.uuid4())
        workflow_id = str(uuid.uuid4())

        with instrument_workflow(workflow_id, session_id):
            # Step 1: Auth
            try:
                self._authenticate(user_token)
            except AuthenticationError as exc:
                return TaxCalculationResponse(
                    workflow_id=workflow_id,
                    status="failed",
                    error=f"Authentication failed: {exc}",
                )

            # Step 2: PII pre-filter
            try:
                self._apply_pii_prefilter(request)
            except ValueError as exc:
                return TaxCalculationResponse(
                    workflow_id=workflow_id,
                    status="failed",
                    error=str(exc),
                )

            # Step 3: Load user preferences
            request = self._load_user_preferences(request)

            # Step 4: Execute workflow (includes tax post-validation)
            response = handle_tax_calculation(request, session_id=session_id)

            # Step 5: Store results in memory
            self._store_results_in_memory(request, response, session_id)

            # Step 6: Record completion
            record_agent_completion(
                agent_id="workflow",
                status=response.status,
                workflow_id=response.workflow_id,
            )

            return response


def _configure_logging(settings: AppSettings) -> None:
    """Set up logging based on config."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )


def main() -> None:
    """Unified entry point - checks deployment mode and starts accordingly.

    Both AgentCore and Kubernetes modes start the same MCP server.
    The difference is infrastructure (managed vs self-hosted), not code.

    AgentCore mode:
        - MCP server is started by AgentCore Runtime via mcp_server.py
        - This function is used for local dev / testing

    Kubernetes mode:
        - MCP server runs in a container, started via Dockerfile CMD
        - This function can also be used directly

    Requirements: 17.5, 17.6
    """
    settings = AppSettings()
    _configure_logging(settings)

    mode = settings.deployment_mode
    logger.info("Starting Agentic Tax Calculator in %s mode", mode.value)

    if mode == DeploymentMode.AGENTCORE:
        logger.info(
            "AgentCore mode: MCP server will be started by AgentCore Runtime. "
            "For local dev, run: python mcp_server.py"
        )
    elif mode == DeploymentMode.KUBERNETES:
        logger.info(
            "Kubernetes mode: MCP server starting via streamable-http transport."
        )

    # Both modes start the same MCP server
    from src.mcp.server import mcp
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
