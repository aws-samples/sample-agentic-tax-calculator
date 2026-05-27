"""Framework-agnostic API request/response schemas.

These Pydantic models define the external contract for tax calculation
requests.  They are intentionally decoupled from Flask/Django/FastAPI
so any frontend (form, chat, CLI, MCP client) can use them.

Requirements: 18.1, 18.4, 18.5
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TaxCalculationRequest(BaseModel):
    """Input accepted from any client - form, chat, or API."""

    business_id: str = Field(
        description="Business identifier (e.g. 'biz_001')"
    )
    tax_year: int = Field(
        description="Tax year to calculate (e.g. 2024)"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional user ID for memory/preference lookup",
    )


class ClarifyingQuestion(BaseModel):
    """Returned when required info is missing - renderable by any frontend."""

    field: str = Field(description="Name of the missing/ambiguous field")
    message: str = Field(description="Human-readable question for the user")
    options: Optional[list[str]] = Field(
        default=None,
        description="Suggested values the user can pick from",
    )


class TaxCalculationResponse(BaseModel):
    """Structured result renderable by any frontend."""

    workflow_id: str = Field(description="Unique workflow run identifier")
    status: str = Field(description="'completed' | 'failed' | 'clarification_needed'")

    # Business context
    business_name: Optional[str] = None
    jurisdiction: Optional[str] = None
    tax_year: Optional[int] = None
    accounting_method: Optional[str] = None

    # Financial summary
    revenue: Optional[float] = None
    expenses: Optional[float] = None
    profit: Optional[float] = None

    # Tax breakdown
    federal_tax: Optional[float] = None
    provincial_tax: Optional[float] = None
    cpp_contributions: Optional[float] = None
    ei_premiums: Optional[float] = None
    total_tax: Optional[float] = None
    bracket_details: Optional[list[dict]] = None

    # Error / clarification
    error: Optional[str] = None
    clarifying_questions: Optional[list[ClarifyingQuestion]] = None
