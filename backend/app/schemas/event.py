"""Validated event request and response schemas."""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
)

from app.models.event import Event, EventType

MAX_GUEST_COUNT = 10_000
MAX_BUDGET = Decimal("100000000.00")
MAX_PREFERENCES = 20
MAX_CONSTRAINTS = 20


def _parse_calendar_date(value: object) -> date:
    if isinstance(value, datetime):
        raise ValueError("Event date must be a calendar date in YYYY-MM-DD format.")
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("Event date must be a calendar date in YYYY-MM-DD format.")

    candidate = value.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", candidate):
        raise ValueError("Event date must be a calendar date in YYYY-MM-DD format.")
    try:
        return date.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError("Event date must be a valid calendar date in YYYY-MM-DD format.") from exc


def _normalize_currency_code(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z]{3}", value):
        raise ValueError("Currency must be a three-letter ISO-style code such as INR.")
    return value.upper()


def _normalize_budget_amount(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _validate_timezone(value: str) -> str:
    try:
        return ZoneInfo(value).key
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("Timezone must be a valid IANA timezone such as Asia/Kolkata.") from exc


EventDate = Annotated[
    date,
    BeforeValidator(_parse_calendar_date),
    Field(description="Calendar date in YYYY-MM-DD format."),
]
EventName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    Field(description="User-facing event name."),
]
Location = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    Field(description="City, venue, or short location description."),
]
GuestCount = Annotated[
    StrictInt,
    Field(gt=0, le=MAX_GUEST_COUNT, description="Expected number of guests."),
]
BudgetAmount = Annotated[
    Decimal,
    Field(
        gt=Decimal("0"),
        le=MAX_BUDGET,
        max_digits=12,
        decimal_places=2,
        allow_inf_nan=False,
        description="Positive budget amount with at most two decimal places.",
    ),
    AfterValidator(_normalize_budget_amount),
]
CurrencyCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=3),
    AfterValidator(_normalize_currency_code),
    Field(description="Three-letter currency code; defaults to INR."),
]
TimezoneName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    AfterValidator(_validate_timezone),
    Field(description="IANA timezone used to interpret the event date and deadlines."),
]
DescriptionText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=2_000),
    Field(description="Optional free-form event description."),
]
PreferenceText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    Field(description="A planning preference."),
]
ConstraintText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    Field(description="A planning constraint."),
]
PreferenceList = Annotated[
    list[PreferenceText],
    Field(max_length=MAX_PREFERENCES, description="Up to 20 planning preferences."),
]
ConstraintList = Annotated[
    list[ConstraintText],
    Field(max_length=MAX_CONSTRAINTS, description="Up to 20 planning constraints."),
]


class EventCreate(BaseModel):
    """Client-supplied fields for creating an event."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Ananya and Rohan Wedding",
                "event_type": "wedding",
                "event_date": "2030-06-15",
                "location": "Bengaluru",
                "guest_count": 150,
                "budget_amount": "750000.00",
                "currency": "INR",
                "timezone": "Asia/Kolkata",
                "description": "A relaxed celebration with family and friends.",
                "preferences": ["Pastel decor", "Vegetarian menu"],
                "constraints": ["No loud music after 10 PM"],
            }
        },
    )

    name: EventName
    event_type: EventType
    event_date: EventDate
    location: Location
    guest_count: GuestCount
    budget_amount: BudgetAmount
    currency: CurrencyCode = "INR"
    timezone: TimezoneName | None = None
    description: DescriptionText | None = None
    preferences: PreferenceList = Field(default_factory=list)
    constraints: ConstraintList = Field(default_factory=list)


class EventUpdate(BaseModel):
    """Client-editable event fields; omitted fields remain unchanged."""

    model_config = ConfigDict(extra="forbid")

    name: EventName | None = None
    event_type: EventType | None = None
    event_date: EventDate | None = None
    location: Location | None = None
    guest_count: GuestCount | None = None
    budget_amount: BudgetAmount | None = None
    currency: CurrencyCode | None = None
    timezone: TimezoneName | None = None
    description: DescriptionText | None = None
    preferences: PreferenceList | None = None
    constraints: ConstraintList | None = None


class EventResponse(BaseModel):
    """Complete server representation of an event."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    name: str
    event_type: EventType
    event_date: date
    location: str
    guest_count: int
    budget_amount: Decimal
    currency: str
    timezone: str
    description: str | None
    preferences: list[str]
    constraints: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_event(cls, event: Event) -> Self:
        """Build a response without leaking mutable domain state."""
        return cls(
            event_id=str(event.event_id),
            name=event.name,
            event_type=event.event_type,
            event_date=event.event_date,
            location=event.location,
            guest_count=event.guest_count,
            budget_amount=event.budget_amount,
            currency=event.currency,
            timezone=event.timezone,
            description=event.description,
            preferences=list(event.preferences),
            constraints=list(event.constraints),
            created_at=event.created_at,
            updated_at=event.updated_at,
        )


class EventListResponse(BaseModel):
    """Bounded, deterministic event collection response."""

    model_config = ConfigDict(extra="forbid")

    items: list[EventResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
