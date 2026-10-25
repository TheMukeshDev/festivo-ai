"""Shared monetary precision rules."""

from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTUM = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    """Round a monetary value to two decimal places using half-up rounding."""
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def to_decimal(value) -> Decimal:
    """Convert common input types to Decimal with a sane default."""
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise ValueError(f"Cannot convert {value!r} to Decimal")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        v = value.strip()
        if v == "":
            return Decimal("0.00")
        return Decimal(v)
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"Cannot convert {value!r} to Decimal") from exc
