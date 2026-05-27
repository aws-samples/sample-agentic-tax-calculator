"""Employment Insurance (EI) premium calculation.

2024 rates:
  - Employee/self-employed rate: 2.29%
  - Maximum insurable earnings: $63,200
  - Maximum annual premium: $1,049.12

Note: EI is optional for self-employed Canadians, but the calculation
is included for completeness. Self-employed individuals who opt in
pay the same rate as employees (no employer portion).

Formula:
  insurable_earnings = min(income, max_insurable)
  premium = min(insurable_earnings * rate, max_premium)
"""

# 2024 CRA EI rates
EI_RATE = 0.0229
EI_MAX_INSURABLE_EARNINGS = 63200.0
EI_MAX_PREMIUM = 1049.12


def calculate_ei(income: float) -> float:
    """Calculate EI premiums for a self-employed individual.

    Args:
        income: Net self-employment income (profit) for the tax year.

    Returns:
        EI premium amount, capped at the annual maximum.
    """
    if income <= 0:
        return 0.0

    insurable_earnings = min(income, EI_MAX_INSURABLE_EARNINGS)
    premium = insurable_earnings * EI_RATE

    return min(premium, EI_MAX_PREMIUM)
