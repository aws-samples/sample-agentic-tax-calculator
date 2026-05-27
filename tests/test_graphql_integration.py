"""Integration test: validates the full GraphQL data flow.

Requires the local mock GraphQL server to be running:
    python graphql_server.py

Then run:
    TAX_CALC_DATA_SOURCE_MODE=graphql \
    TAX_CALC_GRAPHQL_ENDPOINT=http://localhost:8090/graphql \
    python -m pytest tests/test_graphql_integration.py -v

Or run directly:
    python tests/test_graphql_integration.py
"""

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force GraphQL mode for this test
os.environ["TAX_CALC_DATA_SOURCE_MODE"] = "graphql"
os.environ["TAX_CALC_GRAPHQL_ENDPOINT"] = os.environ.get(
    "TAX_CALC_GRAPHQL_ENDPOINT", "http://localhost:8090/graphql"
)


def test_get_business_info():
    from src.mcp.tools.business_info import get_business_info

    result = get_business_info("BIZ001", 2024)
    assert result["business_id"] == "BIZ001"
    assert result["business_name"] == "Maple Leaf Consulting"
    assert result["accounting_method"] == "cash"
    assert result["jurisdiction"] == "ON"
    assert result["business_type"] == "SOLE_PROPRIETORSHIP"
    print(f"  [PASS] get_business_info: {result['business_name']}")


def test_get_income():
    from src.mcp.tools.income import get_income

    result = get_income("BIZ001", 2024)
    assert result["business_id"] == "BIZ001"
    assert result["total_revenue"] == 135000.00
    assert len(result["accounts"]) == 2
    assert all(a["account_type"] == "CREDIT" for a in result["accounts"])
    print(f"  [PASS] get_income: ${result['total_revenue']:,.2f} revenue")


def test_get_expenses():
    from src.mcp.tools.expenses import get_expenses

    result = get_expenses("BIZ001", 2024)
    assert result["business_id"] == "BIZ001"
    assert result["total_expenses"] == 25800.00
    assert len(result["accounts"]) == 4
    assert all(a["account_type"] == "DEBIT" for a in result["accounts"])
    print(f"  [PASS] get_expenses: ${result['total_expenses']:,.2f} expenses")


def test_get_assets():
    from src.mcp.tools.assets import get_assets

    result = get_assets("BIZ001", 2024)
    assert result["business_id"] == "BIZ001"
    assert result["hst_collected"] == 17550.00
    assert result["hst_paid"] == 3354.00
    assert result["net_hst"] == 14196.00
    assert result["province"] == "ON"
    print(f"  [PASS] get_assets: net HST ${result['net_hst']:,.2f}")


def test_get_tax_rules():
    from src.mcp.tools.tax_rules import get_tax_rules

    result = get_tax_rules("ON", 2024)
    assert result["jurisdiction"] == "ON"
    assert result["tax_year"] == 2024
    assert len(result["federal_brackets"]) == 5
    assert len(result["provincial_brackets"]) == 5
    assert result["cpp"]["max_contribution"] == 3867.50
    assert result["ei"]["max_premium"] == 1049.12
    print(f"  [PASS] get_tax_rules: {len(result['federal_brackets'])} federal brackets")


def test_biz002_full_flow():
    """Test a different business to ensure routing works."""
    from src.mcp.tools.business_info import get_business_info
    from src.mcp.tools.income import get_income
    from src.mcp.tools.expenses import get_expenses
    from src.mcp.tools.assets import get_assets

    biz = get_business_info("BIZ002", 2024)
    assert biz["jurisdiction"] == "BC"
    assert biz["accounting_method"] == "accrual"

    income = get_income("BIZ002", 2024)
    assert income["total_revenue"] == 255000.00

    expenses = get_expenses("BIZ002", 2024)
    assert expenses["total_expenses"] == 136000.00

    assets = get_assets("BIZ002", 2024)
    assert assets["province"] == "BC"
    assert assets["rate"] == 0.05

    print(f"  [PASS] BIZ002 full flow: {biz['business_name']}, "
          f"revenue=${income['total_revenue']:,.0f}, "
          f"expenses=${expenses['total_expenses']:,.0f}")


def main():
    """Run all integration tests."""
    print()
    print("=" * 60)
    print("  GraphQL Integration Tests")
    print(f"  Endpoint: {os.environ['TAX_CALC_GRAPHQL_ENDPOINT']}")
    print("=" * 60)
    print()

    tests = [
        test_get_business_info,
        test_get_income,
        test_get_expenses,
        test_get_assets,
        test_get_tax_rules,
        test_biz002_full_flow,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    print()
    print("-" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("-" * 60)

    if failed > 0:
        sys.exit(1)
    print()
    print("  All tests passed. GraphQL integration is working.")
    print("  You can now point TAX_CALC_GRAPHQL_ENDPOINT at your real API.")
    print()


if __name__ == "__main__":
    main()
