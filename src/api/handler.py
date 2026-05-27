"""Framework-agnostic request handler for tax calculations.

Accepts a ``TaxCalculationRequest``, invokes the LangGraph workflow,
and returns a ``TaxCalculationResponse``.  When required information
is missing the handler returns ``ClarifyingQuestion`` items instead
of running the workflow.

Requirements: 18.1, 18.3, 18.4, 18.6
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from src.api.schemas import (
    ClarifyingQuestion,
    TaxCalculationRequest,
    TaxCalculationResponse,
)
from src.orchestrator.graph import run_tax_workflow

logger = logging.getLogger(__name__)


def _validate_request(
    request: TaxCalculationRequest,
) -> list[ClarifyingQuestion]:
    """Return clarifying questions for missing / invalid fields."""
    questions: list[ClarifyingQuestion] = []

    if not request.business_id or not request.business_id.strip():
        questions.append(
            ClarifyingQuestion(
                field="business_id",
                message="Which business would you like to calculate taxes for?",
            )
        )

    if request.tax_year is None:
        questions.append(
            ClarifyingQuestion(
                field="tax_year",
                message="Which tax year should be calculated?",
                options=["2025", "2024"],
            )
        )
    elif request.tax_year < 2000 or request.tax_year > 2099:
        questions.append(
            ClarifyingQuestion(
                field="tax_year",
                message=(
                    f"Tax year {request.tax_year} looks invalid. "
                    "Please provide a year between 2000 and 2099."
                ),
            )
        )

    return questions


def handle_tax_calculation(
    request: TaxCalculationRequest,
    session_id: Optional[str] = None,
) -> TaxCalculationResponse:
    """Run a full tax calculation workflow for *request*.

    Returns a ``TaxCalculationResponse`` with either the computed tax
    breakdown or a list of clarifying questions when required fields
    are missing.
    """
    workflow_id = str(uuid.uuid4())

    # -- Pre-flight validation -----------------------------------------------
    questions = _validate_request(request)
    if questions:
        return TaxCalculationResponse(
            workflow_id=workflow_id,
            status="clarification_needed",
            clarifying_questions=questions,
        )

    # -- Execute the LangGraph workflow --------------------------------------
    try:
        logger.info(
            "Starting tax workflow %s for business=%s year=%d",
            workflow_id,
            request.business_id,
            request.tax_year,
        )

        result = run_tax_workflow(
            business_id=request.business_id,
            tax_year=request.tax_year,
            session_id=session_id,
            workflow_id=workflow_id,
        )

        # -- Map SharedState -> TaxCalculationResponse -----------------------
        if result.get("status") == "failed":
            return TaxCalculationResponse(
                workflow_id=workflow_id,
                status="failed",
                error=result.get("error", "Unknown workflow error"),
            )

        tax = result.get("tax_result", {})

        return TaxCalculationResponse(
            workflow_id=workflow_id,
            status="completed",
            business_name=result.get("business_name"),
            jurisdiction=result.get("jurisdiction"),
            tax_year=result.get("tax_year"),
            accounting_method=result.get("accounting_method"),
            revenue=result.get("revenue"),
            expenses=result.get("expenses"),
            profit=tax.get("profit"),
            federal_tax=tax.get("federal_tax"),
            provincial_tax=tax.get("provincial_tax"),
            cpp_contributions=tax.get("cpp_contribution"),
            ei_premiums=tax.get("ei_premium"),
            total_tax=tax.get("total_tax"),
            bracket_details=tax.get("bracket_details"),
        )

    except Exception as exc:
        logger.exception("Workflow %s failed: %s", workflow_id, exc)
        return TaxCalculationResponse(
            workflow_id=workflow_id,
            status="failed",
            error=str(exc),
        )
