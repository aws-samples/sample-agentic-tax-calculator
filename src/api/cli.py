"""Minimal CLI for submitting a tax calculation request.

Usage::

    python -m src.api.cli --business-id biz_001 --tax-year 2024

Requirements: 18.2
"""

from __future__ import annotations

import argparse
import sys

from src.api.handler import handle_tax_calculation
from src.api.schemas import TaxCalculationRequest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Agentic Tax Calculator - CLI interface",
    )
    parser.add_argument(
        "--business-id",
        required=True,
        help="Business identifier (e.g. biz_001)",
    )
    parser.add_argument(
        "--tax-year",
        type=int,
        required=True,
        help="Tax year to calculate (e.g. 2024)",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="Optional user ID for preference lookup",
    )

    args = parser.parse_args(argv)

    request = TaxCalculationRequest(
        business_id=args.business_id,
        tax_year=args.tax_year,
        user_id=args.user_id,
    )

    print(f"\n{'='*60}")
    print("  Agentic Tax Calculator")
    print(f"  Business: {request.business_id}  |  Year: {request.tax_year}")
    print(f"{'='*60}\n")

    response = handle_tax_calculation(request)

    if response.status == "clarification_needed" and response.clarifying_questions:
        print("Additional information needed:\n")
        for q in response.clarifying_questions:
            print(f"  [{q.field}] {q.message}")
            if q.options:
                print(f"    Options: {', '.join(q.options)}")
        sys.exit(1)

    if response.status == "failed":
        print(f"ERROR: {response.error}")
        sys.exit(2)

    # -- Pretty-print the result ---------------------------------------------
    print(f"  Workflow ID : {response.workflow_id}")
    print(f"  Business    : {response.business_name}")
    print(f"  Jurisdiction: {response.jurisdiction}")
    print(f"  Method      : {response.accounting_method}")
    print()

    if response.revenue is not None:
        print(f"  Revenue     : ${response.revenue:>12,.2f}")
    if response.expenses is not None:
        print(f"  Expenses    : ${response.expenses:>12,.2f}")
    if response.profit is not None:
        print(f"  Profit      : ${response.profit:>12,.2f}")
    print()

    if response.federal_tax is not None:
        print(f"  Federal Tax : ${response.federal_tax:>12,.2f}")
    if response.provincial_tax is not None:
        print(f"  Provincial  : ${response.provincial_tax:>12,.2f}")
    if response.cpp_contributions is not None:
        print(f"  CPP         : ${response.cpp_contributions:>12,.2f}")
    if response.ei_premiums is not None:
        print(f"  EI          : ${response.ei_premiums:>12,.2f}")

    sep = "\u2500" * 30
    print(f"  {sep}")

    if response.total_tax is not None:
        print(f"  Total Tax   : ${response.total_tax:>12,.2f}")
    print()


if __name__ == "__main__":
    main()
