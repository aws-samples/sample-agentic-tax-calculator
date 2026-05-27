"""Deterministic post-validation of tax calculations.

Verifies that a TaxBreakdown is internally consistent:
  - profit equals revenue minus expenses
  - federal tax falls within the valid bracket range for the reported profit
  - provincial tax falls within the valid bracket range for the reported
    jurisdiction and profit

Uses the same bracket data the engine uses so the validator is an
independent cross-check, not a re-run of the engine.
"""

from dataclasses import dataclass, field

from src.tax_engine.interface import TaxBreakdown, TaxBracket
from src.tax_engine.brackets import (
    FEDERAL_BRACKETS_2024,
    PROVINCIAL_BRACKETS_2024,
    SUPPORTED_JURISDICTIONS,
)


@dataclass
class ValidationResult:
    """Outcome of a tax-breakdown validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)


def _max_tax_for_brackets(profit: float, brackets: list[TaxBracket]) -> float:
    """Compute the maximum possible tax by applying brackets with no credits."""
    if profit <= 0:
        return 0.0
    tax = 0.0
    for bracket in brackets:
        if profit <= bracket.min_income:
            break
        upper = bracket.max_income if bracket.max_income is not None else profit
        taxable = min(profit, upper) - bracket.min_income
        tax += taxable * bracket.rate
    return tax


class ValidationEngine:
    """Deterministic post-validation of tax calculations."""

    _TOLERANCE = 0.01  # rounding tolerance in dollars

    def validate(
        self,
        tax_breakdown: TaxBreakdown,
        revenue: float,
        expenses: float,
    ) -> ValidationResult:
        """Verify tax calculation correctness.

        Args:
            tax_breakdown: The computed tax result to validate.
            revenue: The original revenue input.
            expenses: The original expenses input.

        Returns:
            ValidationResult with is_valid flag and any error messages.
        """
        errors: list[str] = []

        # --- Check 1: profit == revenue - expenses ---
        expected_profit = revenue - expenses
        if abs(tax_breakdown.profit - expected_profit) > self._TOLERANCE:
            errors.append(
                f"Profit mismatch: expected {expected_profit:.2f}, "
                f"got {tax_breakdown.profit:.2f}"
            )

        profit = tax_breakdown.profit

        # --- Check 2: federal tax in valid bracket range ---
        if not self._federal_tax_in_range(profit, tax_breakdown.federal_tax):
            errors.append(
                f"Federal tax {tax_breakdown.federal_tax:.2f} outside valid "
                f"bracket range for profit {profit:.2f}"
            )

        # --- Check 3: provincial tax in valid bracket range ---
        if not self._provincial_tax_in_range(
            profit,
            tax_breakdown.provincial_tax,
            tax_breakdown.jurisdiction,
        ):
            errors.append(
                f"Provincial tax {tax_breakdown.provincial_tax:.2f} outside valid "
                f"bracket range for jurisdiction {tax_breakdown.jurisdiction} "
                f"and profit {profit:.2f}"
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _federal_tax_in_range(self, profit: float, federal_tax: float) -> bool:
        """Return True if federal_tax is between 0 and the gross bracket max."""
        if profit <= 0:
            return federal_tax <= self._TOLERANCE

        max_tax = _max_tax_for_brackets(profit, FEDERAL_BRACKETS_2024)
        return -self._TOLERANCE <= federal_tax <= max_tax + self._TOLERANCE

    def _provincial_tax_in_range(
        self,
        profit: float,
        provincial_tax: float,
        jurisdiction: str,
    ) -> bool:
        """Return True if provincial_tax is between 0 and the gross bracket max."""
        jurisdiction = jurisdiction.upper()

        if jurisdiction not in SUPPORTED_JURISDICTIONS:
            # Unknown jurisdiction - can't validate, treat as invalid
            return False

        if profit <= 0:
            return provincial_tax <= self._TOLERANCE

        brackets = PROVINCIAL_BRACKETS_2024[jurisdiction]
        max_tax = _max_tax_for_brackets(profit, brackets)
        return -self._TOLERANCE <= provincial_tax <= max_tax + self._TOLERANCE
