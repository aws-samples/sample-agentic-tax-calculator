"""Tax validation guardrail - post-filter wrapper around ValidationEngine.

Implements the AgentCore Guardrails post-filter pattern: after the
Tax_Agent produces a TaxBreakdown, this guardrail validates the result
using the deterministic ValidationEngine.  If validation fails the
response is blocked before it reaches the user.

Requirements: 14.1, 14.5
"""

from __future__ import annotations

from src.tax_engine.interface import TaxBreakdown
from src.validation.validator import ValidationEngine, ValidationResult


class TaxValidationGuardrail:
    """Post-filter that blocks Tax_Agent responses failing validation.

    Usage::

        guardrail = TaxValidationGuardrail()
        result = guardrail.validate_response(tax_breakdown, revenue, expenses)
        if not result.is_valid:
            # block the response - errors list explains why
            ...
    """

    def __init__(self, engine: ValidationEngine | None = None) -> None:
        self._engine = engine or ValidationEngine()

    def validate_response(
        self,
        tax_breakdown: TaxBreakdown,
        revenue: float,
        expenses: float,
    ) -> ValidationResult:
        """Validate a tax calculation result.

        Delegates to :class:`ValidationEngine` and returns its
        :class:`ValidationResult`.  The caller should inspect
        ``result.is_valid`` - when ``False`` the response must be
        blocked and the errors surfaced to the orchestrator.

        Args:
            tax_breakdown: The computed tax result from the Tax_Agent.
            revenue: Original revenue input.
            expenses: Original expenses input.

        Returns:
            ValidationResult from the engine.
        """
        return self._engine.validate(tax_breakdown, revenue, expenses)
