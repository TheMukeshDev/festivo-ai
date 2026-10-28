"""Shared monetary precision rules."""

from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTUM = Decimal("0.01")
_ZERO_MONEY = Decimal("0.00")


def quantize_money(value: Decimal) -> Decimal:
    """Round a monetary value to two decimal places using half-up rounding."""
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def to_decimal(value) -> Decimal:
    """Convert common input types to Decimal with a sane default."""
    if value is None:
        return _ZERO_MONEY
    if isinstance(value, bool):
        raise ValueError(f"Cannot convert {value!r} to Decimal")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        return _decimal_from_string(value)
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"Cannot convert {value!r} to Decimal") from exc


def _decimal_from_string(value: str) -> Decimal:
    stripped = value.strip()
    return _ZERO_MONEY if stripped == "" else Decimal(stripped)
