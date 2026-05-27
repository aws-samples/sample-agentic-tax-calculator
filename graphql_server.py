"""Local mock GraphQL server for integration testing.

Serves the same data as src/mock/data/*.json but via a real GraphQL API.
This lets you test the full GraphQL integration plumbing (client, auth
passthrough, error handling, response mapping) without needing a
production API.

Usage:
    python graphql_server.py

    Server starts at http://localhost:8090/graphql
    GraphiQL playground available at http://localhost:8090/graphql (browser)

Then configure the tax calculator:
    TAX_CALC_DATA_SOURCE_MODE=graphql
    TAX_CALC_GRAPHQL_ENDPOINT=http://localhost:8090/graphql
"""

import json
import os
from typing import Optional

import strawberry
from strawberry.asgi import GraphQL

# ---------------------------------------------------------------------------
# Load mock data
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "src", "mock", "data")


def _load_json(filename: str) -> dict:
    with open(os.path.join(DATA_DIR, filename), "r") as f:
        return json.load(f)


BUSINESS_DATA = _load_json("business.json")
INCOME_DATA = _load_json("income.json")
EXPENSES_DATA = _load_json("expenses.json")
ASSETS_DATA = _load_json("assets.json")
TAX_RULES_DATA = _load_json("tax_rules.json")


# ---------------------------------------------------------------------------
# GraphQL Types
# ---------------------------------------------------------------------------


@strawberry.type
class Address:
    city: str
    province: str
    postal_code: str
    country: str


@strawberry.type
class Business:
    id: str
    name: str
    accounting_method: str
    jurisdiction: str
    fiscal_year_end: str
    business_type: str
    address: Address
    gst_hst_number: str
    tax_year: int


@strawberry.type
class Account:
    name: str
    type: str
    amount: float


@strawberry.type
class ProfitAndLoss:
    business_id: str
    tax_year: int
    accounts: list[Account]
    total_revenue: Optional[float] = None
    total_expenses: Optional[float] = None


@strawberry.type
class TaxAccounts:
    business_id: str
    tax_year: int
    hst_collected: float
    hst_paid: float
    net_hst: float
    province: str
    rate: float
    rate_type: str
    description: str


@strawberry.type
class TaxBracket:
    min: float
    max: Optional[float]
    rate: float


@strawberry.type
class FederalRules:
    tax_year: int
    brackets: list[TaxBracket]
    basic_personal_amount: float


@strawberry.type
class ProvincialRules:
    jurisdiction: str
    name: str
    tax_year: int
    brackets: list[TaxBracket]
    basic_personal_amount: float


@strawberry.type
class CPPRules:
    rate: float
    max_pensionable_earnings: float
    basic_exemption: float
    max_contribution: float
    max_self_employed_contribution: float


@strawberry.type
class EIRules:
    rate: float
    max_insurable_earnings: float
    max_premium: float
    max_self_employed_premium: float


@strawberry.type
class TaxRules:
    federal: FederalRules
    provincial: Optional[ProvincialRules]
    cpp: CPPRules
    ei: EIRules


# ---------------------------------------------------------------------------
# Query resolvers
# ---------------------------------------------------------------------------


@strawberry.type
class Query:
    @strawberry.field
    def business(self, id: str, tax_year: int) -> Business:
        if id not in BUSINESS_DATA:
            raise ValueError(f"Business not found: {id}")
        biz = BUSINESS_DATA[id]["business"]
        addr = biz.get("address", {})
        return Business(
            id=biz["id"],
            name=biz["name"],
            accounting_method=biz["accountingMethod"],
            jurisdiction=biz["jurisdiction"],
            fiscal_year_end=biz["fiscalYearEnd"],
            business_type=biz["businessType"],
            address=Address(
                city=addr.get("city", ""),
                province=addr.get("province", ""),
                postal_code=addr.get("postalCode", ""),
                country=addr.get("country", ""),
            ),
            gst_hst_number=biz.get("gstHstNumber", ""),
            tax_year=biz.get("taxYear", tax_year),
        )

    @strawberry.field
    def profit_and_loss(
        self,
        business_id: str,
        tax_year: int,
        accounting_method: Optional[str] = None,
        type: Optional[str] = None,
    ) -> ProfitAndLoss:
        """Return P&L data. If type is CREDIT, use income data. If DEBIT, use expenses."""
        if type == "CREDIT" or type is None:
            # Try income first
            if business_id in INCOME_DATA:
                pnl = INCOME_DATA[business_id]["profitAndLoss"]
                accounts = pnl["accounts"]
                if type:
                    accounts = [a for a in accounts if a["type"] == type]
                return ProfitAndLoss(
                    business_id=pnl["businessId"],
                    tax_year=pnl["taxYear"],
                    accounts=[
                        Account(name=a["name"], type=a["type"], amount=a["amount"])
                        for a in accounts
                    ],
                    total_revenue=pnl.get("totalRevenue"),
                    total_expenses=None,
                )

        if type == "DEBIT":
            if business_id in EXPENSES_DATA:
                pnl = EXPENSES_DATA[business_id]["profitAndLoss"]
                accounts = [a for a in pnl["accounts"] if a["type"] == "DEBIT"]
                return ProfitAndLoss(
                    business_id=pnl["businessId"],
                    tax_year=pnl["taxYear"],
                    accounts=[
                        Account(name=a["name"], type=a["type"], amount=a["amount"])
                        for a in accounts
                    ],
                    total_revenue=None,
                    total_expenses=pnl.get("totalExpenses"),
                )

        raise ValueError(f"Business not found: {business_id}")

    @strawberry.field
    def tax_accounts(self, business_id: str, tax_year: int) -> TaxAccounts:
        if business_id not in ASSETS_DATA:
            raise ValueError(f"Business not found: {business_id}")
        ta = ASSETS_DATA[business_id]["taxAccounts"]
        return TaxAccounts(
            business_id=ta["businessId"],
            tax_year=ta["taxYear"],
            hst_collected=ta["hstCollected"],
            hst_paid=ta["hstPaid"],
            net_hst=ta["netHst"],
            province=ta["province"],
            rate=ta["rate"],
            rate_type=ta["rateType"],
            description=ta["description"],
        )

    @strawberry.field
    def tax_rules(self, jurisdiction: str, tax_year: int) -> TaxRules:
        federal = TAX_RULES_DATA["federal"]
        provincial_data = TAX_RULES_DATA.get("provincial", {})
        cpp_data = TAX_RULES_DATA["cpp"]
        ei_data = TAX_RULES_DATA["ei"]

        if jurisdiction not in provincial_data:
            raise ValueError(f"Jurisdiction not found: {jurisdiction}")

        prov = provincial_data[jurisdiction]

        return TaxRules(
            federal=FederalRules(
                tax_year=federal["taxYear"],
                brackets=[
                    TaxBracket(min=b["min"], max=b["max"], rate=b["rate"])
                    for b in federal["brackets"]
                ],
                basic_personal_amount=federal["basicPersonalAmount"],
            ),
            provincial=ProvincialRules(
                jurisdiction=prov["jurisdiction"],
                name=prov["name"],
                tax_year=prov["taxYear"],
                brackets=[
                    TaxBracket(min=b["min"], max=b["max"], rate=b["rate"])
                    for b in prov["brackets"]
                ],
                basic_personal_amount=prov["basicPersonalAmount"],
            ),
            cpp=CPPRules(
                rate=cpp_data["rate"],
                max_pensionable_earnings=cpp_data["maxPensionableEarnings"],
                basic_exemption=cpp_data["basicExemption"],
                max_contribution=cpp_data["maxContribution"],
                max_self_employed_contribution=cpp_data["maxSelfEmployedContribution"],
            ),
            ei=EIRules(
                rate=ei_data["rate"],
                max_insurable_earnings=ei_data["maxInsurableEarnings"],
                max_premium=ei_data["maxPremium"],
                max_self_employed_premium=ei_data["maxSelfEmployedPremium"],
            ),
        )


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

schema = strawberry.Schema(query=Query)
app = GraphQL(schema)


if __name__ == "__main__":
    import uvicorn

    print("Starting mock GraphQL server at http://localhost:8090/graphql")
    print("GraphiQL playground: http://localhost:8090/graphql (open in browser)")
    print()
    print("Configure tax calculator to use it:")
    print("  TAX_CALC_DATA_SOURCE_MODE=graphql")
    print("  TAX_CALC_GRAPHQL_ENDPOINT=http://localhost:8090/graphql")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8090)
