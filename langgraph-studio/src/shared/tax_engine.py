"""Simplified deterministic Canadian tax engine for the Studio demo.

Uses 2024 CRA rates. Supports ON, BC, AB, QC provinces.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TaxBracket:
    min_income: float
    max_income: Optional[float]
    rate: float


# --- 2024 Federal brackets ---
FEDERAL_BRACKETS = [
    TaxBracket(0, 55867, 0.15),
    TaxBracket(55867, 111733, 0.205),
    TaxBracket(111733, 154906, 0.26),
    TaxBracket(154906, 220000, 0.29),
    TaxBracket(220000, None, 0.33),
]

FEDERAL_BPA = 15705  # Basic Personal Amount 2024

# --- 2024 Provincial brackets (subset for demo) ---
PROVINCIAL_BRACKETS = {
    "ON": [
        TaxBracket(0, 51446, 0.0505),
        TaxBracket(51446, 102894, 0.0915),
        TaxBracket(102894, 150000, 0.1116),
        TaxBracket(150000, 220000, 0.1216),
        TaxBracket(220000, None, 0.1316),
    ],
    "BC": [
        TaxBracket(0, 45654, 0.0506),
        TaxBracket(45654, 91310, 0.077),
        TaxBracket(91310, 104835, 0.105),
        TaxBracket(104835, 127299, 0.1229),
        TaxBracket(127299, 172602, 0.147),
        TaxBracket(172602, 240716, 0.168),
        TaxBracket(240716, None, 0.205),
    ],
    "AB": [
        TaxBracket(0, 148269, 0.10),
        TaxBracket(148269, 177922, 0.12),
        TaxBracket(177922, 237230, 0.13),
        TaxBracket(237230, 355845, 0.14),
        TaxBracket(355845, None, 0.15),
    ],
    "QC": [
        TaxBracket(0, 51780, 0.14),
        TaxBracket(51780, 103545, 0.19),
        TaxBracket(103545, 126000, 0.24),
        TaxBracket(126000, None, 0.2575),
    ],
}

PROVINCIAL_BPA = {
    "ON": 11865,
    "BC": 11981,
    "AB": 21003,
    "QC": 17183,
}

# CPP 2024
CPP_RATE = 0.1190
CPP_MAX_PENSIONABLE = 68500
CPP_BASIC_EXEMPTION = 3500
CPP_MAX_CONTRIBUTION = 7735.00

# EI 2024 (self-employed voluntary)
EI_RATE = 0.0166
EI_MAX_INSURABLE = 63200
EI_MAX_PREMIUM = 1049.12

SUPPORTED_JURISDICTIONS = list(PROVINCIAL_BRACKETS.keys())


def _apply_brackets(income: float, brackets: list[TaxBracket]) -> float:
    if income <= 0:
        return 0.0
    tax = 0.0
    for b in brackets:
        if income <= b.min_income:
            break
        upper = b.max_income if b.max_income is not None else income
        taxable = min(income, upper) - b.min_income
        tax += taxable * b.rate
    return tax


def _bracket_details(income: float, brackets: list[TaxBracket], level: str) -> list[dict]:
    details = []
    for b in brackets:
        if income <= b.min_income:
            break
        upper = b.max_income if b.max_income is not None else income
        taxable = min(income, upper) - b.min_income
        details.append({
            "level": level,
            "min_income": b.min_income,
            "max_income": b.max_income,
            "rate": b.rate,
            "taxable_amount": round(taxable, 2),
            "tax": round(taxable * b.rate, 2),
        })
    return details


def calculate_tax(
    revenue: float,
    expenses: float,
    jurisdiction: str,
    accounting_method: str = "cash",
    tax_year: int = 2024,
    assets: Optional[dict] = None,
) -> dict:
    """Compute full Canadian tax breakdown."""
    jurisdiction = jurisdiction.upper()
    if jurisdiction not in SUPPORTED_JURISDICTIONS:
        raise ValueError(f"Unsupported jurisdiction: {jurisdiction}. Supported: {SUPPORTED_JURISDICTIONS}")

    profit = revenue - expenses

    # Federal
    gross_federal = _apply_brackets(profit, FEDERAL_BRACKETS)
    bpa_credit = FEDERAL_BPA * FEDERAL_BRACKETS[0].rate
    federal_tax = max(gross_federal - bpa_credit, 0.0)

    # Provincial
    prov_brackets = PROVINCIAL_BRACKETS[jurisdiction]
    gross_provincial = _apply_brackets(profit, prov_brackets)
    prov_bpa = PROVINCIAL_BPA.get(jurisdiction, 0)
    prov_bpa_credit = prov_bpa * prov_brackets[0].rate
    provincial_tax = max(gross_provincial - prov_bpa_credit, 0.0)

    # CPP
    pensionable = min(max(profit - CPP_BASIC_EXEMPTION, 0), CPP_MAX_PENSIONABLE - CPP_BASIC_EXEMPTION)
    cpp = min(pensionable * CPP_RATE, CPP_MAX_CONTRIBUTION)

    # EI
    insurable = min(max(profit, 0), EI_MAX_INSURABLE)
    ei = min(insurable * EI_RATE, EI_MAX_PREMIUM)

    total = federal_tax + provincial_tax + cpp + ei

    bracket_details = (
        _bracket_details(profit, FEDERAL_BRACKETS, "federal")
        + _bracket_details(profit, prov_brackets, "provincial")
    )

    return {
        "profit": round(profit, 2),
        "federal_tax": round(federal_tax, 2),
        "provincial_tax": round(provincial_tax, 2),
        "cpp_contribution": round(cpp, 2),
        "ei_premium": round(ei, 2),
        "total_tax": round(total, 2),
        "effective_rate": round((total / profit * 100) if profit > 0 else 0, 2),
        "jurisdiction": jurisdiction,
        "accounting_method": accounting_method,
        "tax_year": tax_year,
        "bracket_details": bracket_details,
    }
