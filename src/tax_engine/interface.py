"""Tax engine interfaces and data models.

Defines the standard input/output contract for tax engines. The interface is
designed to be swappable - a future LLM-based US implementation can replace
the deterministic engine without changing agent orchestration.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TaxInput:
    """Input data for a tax calculation."""

    revenue: float
    expenses: float
    jurisdiction: str  # Province/territory code: "ON", "BC", "AB", etc.
    accounting_method: str  # "cash" or "accrual"
    tax_year: int
    assets: Optional[dict] = field(default_factory=dict)


@dataclass
class TaxBreakdown:
    """Result of a tax calculation with full breakdown."""

    profit: float
    federal_tax: float
    provincial_tax: float
    cpp_contribution: float
    ei_premium: float
    total_tax: float
    jurisdiction: str
    accounting_method: str
    tax_year: int = 0
    bracket_details: list = field(default_factory=list)


@dataclass
class TaxBracket:
    """A single tax bracket with income range and rate."""

    min_income: float
    max_income: Optional[float]  # None = no upper limit
    rate: float


@dataclass
class JurisdictionRules:
    """Complete tax rules for a jurisdiction and tax year."""

    jurisdiction: str
    tax_year: int
    federal_brackets: list  # list[TaxBracket]
    provincial_brackets: list  # list[TaxBracket]
    cpp_rate: float
    cpp_max_pensionable: float
    cpp_basic_exemption: float
    cpp_max_contribution: float
    ei_rate: float
    ei_max_insurable: float
    ei_max_premium: float
    basic_personal_amount: float


class TaxEngineInterface(ABC):
    """Standard interface for tax engines.

    Phase 1: DeterministicTaxEngine (rules-based, Canada only)
    Phase 2: LLMTaxEngine (non-deterministic, US support)

    Swapping implementations does not change agent orchestration.
    """

    @abstractmethod
    def calculate(self, tax_input: TaxInput) -> TaxBreakdown:
        """Compute tax breakdown for the given input."""
        ...

    @abstractmethod
    def get_tax_rules(self, jurisdiction: str, tax_year: int) -> JurisdictionRules:
        """Return the tax rules for a given jurisdiction and tax year."""
        ...
