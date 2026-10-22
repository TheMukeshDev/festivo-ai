"""Shared monetary precision rules."""

from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTUM = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    """Round a monetary value to two decimal places using half-up rounding."""
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
