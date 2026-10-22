"""Injectable UTC clock helpers."""

from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)


def coerce_utc(moment: datetime) -> datetime:
    """Require a timezone-aware clock value and normalize it to UTC."""
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise RuntimeError("The clock must return a timezone-aware datetime.")
    return moment.astimezone(UTC)
