"""Deterministic Canadian tax engine.

Phase 1 implementation: rules-based calculation for all 13 Canadian
provinces and territories. Applies federal brackets, provincial brackets,
CPP contributions, and EI premiums using 2024 CRA rates.

The engine implements TaxEngineInterface so it can be swapped for a
future LLM-based US implementation without changing agent orchestration.
"""

from src.tax_engine.interface import (
    TaxEngineInterface,
    TaxInput,
    TaxBreakdown,
    TaxBracket,
    JurisdictionRules,
)
from src.tax_engine.brackets import (
    FEDERAL_BRACKETS_2024,
    PROVINCIAL_BRACKETS_2024,
    SUPPORTED_JURISDICTIONS,
    FEDERAL_BASIC_PERSONAL_AMOUNT_2024,
    PROVINCIAL_BASIC_PERSONAL_AMOUNTS_2024,
)
from src.tax_engine.cpp import (
    calculate_cpp,
    CPP_RATE,
    CPP_MAX_PENSIONABLE_EARNINGS,
    CPP_BASIC_EXEMPTION,
    CPP_MAX_CONTRIBUTION,
)
from src.tax_engine.ei import (
    calculate_ei,
    EI_RATE,
    EI_MAX_INSURABLE_EARNINGS,
    EI_MAX_PREMIUM,
)


def _apply_brackets(income: float, brackets: list[TaxBracket]) -> float:
    """Calculate tax by applying progressive brackets to taxable income.

    For each bracket the tax owed is:
        (min(income, max_income or inf) - min_income) * rate
    only for the portion of income that falls within the bracket.
    """
    if income <= 0:
        return 0.0

    tax = 0.0
    for bracket in brackets:
        if income <= bracket.min_income:
            break
        upper = bracket.max_income if bracket.max_income is not None else income
        taxable_in_bracket = min(income, upper) - bracket.min_income
        tax += taxable_in_bracket * bracket.rate

    return tax


def _bracket_details(income: float, brackets: list[TaxBracket], label: str) -> list[dict]:
    """Build a per-bracket breakdown for transparency / audit."""
    details = []
    for bracket in brackets:
        if income <= bracket.min_income:
            break
        upper = bracket.max_income if bracket.max_income is not None else income
        taxable_in_bracket = min(income, upper) - bracket.min_income
        tax_in_bracket = taxable_in_bracket * bracket.rate
        details.append({
            "level": label,
            "min_income": bracket.min_income,
            "max_income": bracket.max_income,
            "rate": bracket.rate,
            "taxable_amount": round(taxable_in_bracket, 2),
            "tax": round(tax_in_bracket, 2),
        })
    return details


class DeterministicTaxEngine(TaxEngineInterface):
    """Rules-based Canadian tax engine for all 13 provinces/territories.

    Supports both Cash and Accrual accounting methods - the accounting
    method determines how revenue and expenses are reported upstream;
    the engine treats the resulting numbers identically since profit
    calculation is the same regardless of method.
    """

    # ------------------------------------------------------------------
    # TaxEngineInterface implementation
    # ------------------------------------------------------------------

    def calculate(self, tax_input: TaxInput) -> TaxBreakdown:
        """Compute full tax breakdown for a Canadian self-employed individual."""
        jurisdiction = tax_input.jurisdiction.upper()

        if jurisdiction not in SUPPORTED_JURISDICTIONS:
            raise ValueError(
                f"Unsupported jurisdiction '{jurisdiction}'. "
                f"Phase 1 supports Canadian provinces/territories only: "
                f"{', '.join(SUPPORTED_JURISDICTIONS)}"
            )

        # Validate accounting method
        method = tax_input.accounting_method.lower()
        if method not in ("cash", "accrual"):
            raise ValueError(
                f"Unsupported accounting method '{tax_input.accounting_method}'. "
                f"Must be 'cash' or 'accrual'."
            )

        # Step 1: Compute profit
        profit = tax_input.revenue - tax_input.expenses

        # Step 2: Federal tax with basic personal amount credit
        federal_brackets = FEDERAL_BRACKETS_2024
        gross_federal_tax = _apply_brackets(profit, federal_brackets)

        # Basic personal amount credit: reduce federal tax by
        # basic_personal_amount * lowest federal rate
        lowest_federal_rate = federal_brackets[0].rate
        bpa_credit = FEDERAL_BASIC_PERSONAL_AMOUNT_2024 * lowest_federal_rate
        federal_tax = max(gross_federal_tax - bpa_credit, 0.0)

        # Step 3: Provincial tax with provincial basic personal amount credit
        provincial_brackets = PROVINCIAL_BRACKETS_2024[jurisdiction]
        gross_provincial_tax = _apply_brackets(profit, provincial_brackets)

        provincial_bpa = PROVINCIAL_BASIC_PERSONAL_AMOUNTS_2024[jurisdiction]
        lowest_provincial_rate = provincial_brackets[0].rate
        provincial_bpa_credit = provincial_bpa * lowest_provincial_rate
        provincial_tax = max(gross_provincial_tax - provincial_bpa_credit, 0.0)

        # Step 4: CPP and EI (based on profit)
        cpp_contribution = calculate_cpp(profit)
        ei_premium = calculate_ei(profit)

        # Step 5: Total
        total_tax = federal_tax + provincial_tax + cpp_contribution + ei_premium

        # Build bracket details for audit trail
        details = (
            _bracket_details(profit, federal_brackets, "federal")
            + _bracket_details(profit, provincial_brackets, "provincial")
        )

        return TaxBreakdown(
            profit=round(profit, 2),
            federal_tax=round(federal_tax, 2),
            provincial_tax=round(provincial_tax, 2),
            cpp_contribution=round(cpp_contribution, 2),
            ei_premium=round(ei_premium, 2),
            total_tax=round(total_tax, 2),
            jurisdiction=jurisdiction,
            accounting_method=method,
            tax_year=tax_input.tax_year,
            bracket_details=details,
        )

    def get_tax_rules(self, jurisdiction: str, tax_year: int) -> JurisdictionRules:
        """Return the complete tax rules for a Canadian jurisdiction."""
        jurisdiction = jurisdiction.upper()

        if jurisdiction not in SUPPORTED_JURISDICTIONS:
            raise ValueError(
                f"Unsupported jurisdiction '{jurisdiction}'. "
                f"Phase 1 supports Canadian provinces/territories only: "
                f"{', '.join(SUPPORTED_JURISDICTIONS)}"
            )

        return JurisdictionRules(
            jurisdiction=jurisdiction,
            tax_year=tax_year,
            federal_brackets=FEDERAL_BRACKETS_2024,
            provincial_brackets=PROVINCIAL_BRACKETS_2024[jurisdiction],
            cpp_rate=CPP_RATE,
            cpp_max_pensionable=CPP_MAX_PENSIONABLE_EARNINGS,
            cpp_basic_exemption=CPP_BASIC_EXEMPTION,
            cpp_max_contribution=CPP_MAX_CONTRIBUTION,
            ei_rate=EI_RATE,
            ei_max_insurable=EI_MAX_INSURABLE_EARNINGS,
            ei_max_premium=EI_MAX_PREMIUM,
            basic_personal_amount=FEDERAL_BASIC_PERSONAL_AMOUNT_2024,
        )
