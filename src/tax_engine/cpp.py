"""Canada Pension Plan (CPP) contribution calculation.

2024 self-employed rates:
  - Combined rate: 11.90% (employee + employer portions)
  - Maximum pensionable earnings: $68,500
  - Basic exemption: $3,500
  - Maximum contribution (self-employed): $7,735.00

Formula:
  pensionable_earnings = min(income, max_pensionable)
  contribution = min((pensionable_earnings - basic_exemption) * rate, max_contribution)
  Return 0 if income <= basic_exemption.
"""

# 2024 CRA CPP rates for self-employed individuals
CPP_RATE = 0.1190
CPP_MAX_PENSIONABLE_EARNINGS = 68500.0
CPP_BASIC_EXEMPTION = 3500.0
CPP_MAX_CONTRIBUTION = 7735.00


def calculate_cpp(income: float) -> float:
    """Calculate CPP contributions for a self-employed individual.

    Args:
        income: Net self-employment income (profit) for the tax year.

    Returns:
        CPP contribution amount, capped at the annual maximum.
    """
    if income <= CPP_BASIC_EXEMPTION:
        return 0.0

    pensionable_earnings = min(income, CPP_MAX_PENSIONABLE_EARNINGS)
    contribution = (pensionable_earnings - CPP_BASIC_EXEMPTION) * CPP_RATE

    return min(contribution, CPP_MAX_CONTRIBUTION)
