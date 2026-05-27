"""Pydantic models for all MCP tool request/response types.

These schemas define the structured data contracts between MCP tools,
agents, and the tax engine. They ensure consistent serialization across
mock and GraphQL data sources.
"""

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class BusinessInfoResponse(BaseModel):
    """Response from get_business_info tool."""

    business_id: str
    business_name: str
    accounting_method: str = Field(description="'cash' or 'accrual'")
    jurisdiction: str = Field(description="Province/territory code, e.g. 'ON'")
    fiscal_year_end: str = ""
    business_type: str = ""


class AccountEntry(BaseModel):
    """A single P&L account line item."""

    name: str
    account_type: str = Field(description="'CREDIT' or 'DEBIT'")
    amount: float


class IncomeResponse(BaseModel):
    """Response from get_income tool."""

    business_id: str
    tax_year: int
    accounting_method: str
    accounts: list[AccountEntry] = Field(default_factory=list)
    total_revenue: float = 0.0


class ExpenseResponse(BaseModel):
    """Response from get_expenses tool."""

    business_id: str
    tax_year: int
    accounting_method: str
    accounts: list[AccountEntry] = Field(default_factory=list)
    total_expenses: float = 0.0


class AssetResponse(BaseModel):
    """Response from get_assets tool."""

    business_id: str
    tax_year: int
    hst_collected: float = 0.0
    hst_paid: float = 0.0
    net_hst: float = 0.0
    province: str = ""
    rate: float = 0.0


class BracketDetail(BaseModel):
    """A single bracket in a tax breakdown."""

    level: str = Field(description="'federal' or 'provincial'")
    min_income: float
    max_income: Optional[float] = None
    rate: float
    taxable_amount: float
    tax: float


class TaxBreakdownResponse(BaseModel):
    """Response from calculate_tax tool."""

    profit: float
    federal_tax: float
    provincial_tax: float
    cpp_contribution: float
    ei_premium: float
    total_tax: float
    jurisdiction: str
    accounting_method: str
    tax_year: int
    bracket_details: list[BracketDetail] = Field(default_factory=list)


class TaxBracketRule(BaseModel):
    """A single bracket rule for display."""

    min_income: float
    max_income: Optional[float] = None
    rate: float


class CPPRules(BaseModel):
    """CPP contribution rules."""

    rate: float
    max_pensionable_earnings: float
    basic_exemption: float
    max_contribution: float


class EIRules(BaseModel):
    """EI premium rules."""

    rate: float
    max_insurable_earnings: float
    max_premium: float


class TaxRulesResponse(BaseModel):
    """Response from get_tax_rules tool."""

    jurisdiction: str
    tax_year: int
    federal_brackets: list[TaxBracketRule] = Field(default_factory=list)
    provincial_brackets: list[TaxBracketRule] = Field(default_factory=list)
    cpp: CPPRules
    ei: EIRules
    basic_personal_amount: float


class ToolErrorResponse(BaseModel):
    """Standard error response from any MCP tool."""

    error: str
    tool_name: str
    details: str = ""
