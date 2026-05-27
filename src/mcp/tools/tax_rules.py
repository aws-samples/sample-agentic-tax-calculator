"""MCP tool: get_tax_rules - return CRA bracket rules for a jurisdiction.

Routes to MockDataProvider (for raw JSON rules) or the DeterministicTaxEngine
(for structured JurisdictionRules) based on DataSourceMode config.
"""

from src.config.settings import AppSettings, DataSourceMode
from src.mock.provider import MockDataProvider
from src.tax_engine.engine import DeterministicTaxEngine
from src.mcp.tools.schemas import (
    TaxRulesResponse,
    TaxBracketRule,
    CPPRules,
    EIRules,
)


def _get_settings() -> AppSettings:
    return AppSettings()


def get_tax_rules(jurisdiction: str, tax_year: int) -> dict:
    """Return deterministic CRA tax bracket rules for a jurisdiction.

    Args:
        jurisdiction: Province/territory code (e.g. 'ON', 'BC').
        tax_year: Tax year for bracket lookup.

    Returns:
        dict with federal_brackets, provincial_brackets, cpp, ei,
        and basic_personal_amount.

    Raises:
        ValueError: If jurisdiction is not supported in Phase 1.
    """
    settings = _get_settings()

    if settings.data_source_mode == DataSourceMode.MOCK:
        # Use the tax engine directly - it has the canonical bracket data
        engine = DeterministicTaxEngine()
        rules = engine.get_tax_rules(jurisdiction, tax_year)

        federal_brackets = [
            TaxBracketRule(
                min_income=b.min_income,
                max_income=b.max_income,
                rate=b.rate,
            )
            for b in rules.federal_brackets
        ]
        provincial_brackets = [
            TaxBracketRule(
                min_income=b.min_income,
                max_income=b.max_income,
                rate=b.rate,
            )
            for b in rules.provincial_brackets
        ]

        response = TaxRulesResponse(
            jurisdiction=rules.jurisdiction,
            tax_year=rules.tax_year,
            federal_brackets=federal_brackets,
            provincial_brackets=provincial_brackets,
            cpp=CPPRules(
                rate=rules.cpp_rate,
                max_pensionable_earnings=rules.cpp_max_pensionable,
                basic_exemption=rules.cpp_basic_exemption,
                max_contribution=rules.cpp_max_contribution,
            ),
            ei=EIRules(
                rate=rules.ei_rate,
                max_insurable_earnings=rules.ei_max_insurable,
                max_premium=rules.ei_max_premium,
            ),
            basic_personal_amount=rules.basic_personal_amount,
        )
        return response.model_dump()
    else:
        from src.graphql.provider import GraphQLDataProvider

        provider = GraphQLDataProvider(endpoint=settings.graphql_endpoint)
        raw = provider.get_tax_rules(jurisdiction, tax_year)
        if raw is None:
            raise ValueError(
                f"Jurisdiction '{jurisdiction}' not found in tax rules."
            )

        fed = raw.get("federal", {})
        prov = raw.get("provincial", {})
        cpp_data = raw.get("cpp", {})
        ei_data = raw.get("ei", {})

        federal_brackets = [
            TaxBracketRule(
                min_income=b["min"],
                max_income=b.get("max"),
                rate=b["rate"],
            )
            for b in fed.get("brackets", [])
        ]
        provincial_brackets = [
            TaxBracketRule(
                min_income=b["min"],
                max_income=b.get("max"),
                rate=b["rate"],
            )
            for b in prov.get("brackets", [])
        ]

        response = TaxRulesResponse(
            jurisdiction=jurisdiction,
            tax_year=tax_year,
            federal_brackets=federal_brackets,
            provincial_brackets=provincial_brackets,
            cpp=CPPRules(
                rate=cpp_data.get("rate", 0),
                max_pensionable_earnings=cpp_data.get("maxPensionableEarnings", 0),
                basic_exemption=cpp_data.get("basicExemption", 0),
                max_contribution=cpp_data.get("maxContribution", 0),
            ),
            ei=EIRules(
                rate=ei_data.get("rate", 0),
                max_insurable_earnings=ei_data.get("maxInsurableEarnings", 0),
                max_premium=ei_data.get("maxPremium", 0),
            ),
            basic_personal_amount=fed.get("basicPersonalAmount", 0),
        )
        return response.model_dump()
