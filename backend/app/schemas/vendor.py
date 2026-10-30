"""Validated vendor request and response schemas."""

import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

from app.core.money import quantize_money
from app.models.budget import MAX_MONEY
from app.models.vendor import Vendor, VendorCategory, VendorStatus

MAX_TEXT = 200
MAX_LONG = 2000
MAX_NAME = 120
MAX_CONTACT = 120
MAX_AREA = 200
MAX_NOTES = 2000
MAX_PRICING = 1000

VendorName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_NAME),
    Field(description="Vendor business name."),
]
ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TEXT),
    Field(description="Short text field."),
]
LongText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=MAX_LONG),
    Field(description="Optional long text."),
]
PricingNotes = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=MAX_PRICING),
    Field(description="Optional pricing notes."),
]
CurrencyCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=3),
    Field(description="Three-letter currency code."),
]
EmailStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=254),
    Field(description="Optional vendor email."),
]
PhoneStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=40),
    Field(description="Optional phone/contact string."),
]
UrlStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=5, max_length=2048),
    Field(description="Optional http(s) website URL."),
]
RatingValue = Annotated[
    Decimal,
    Field(ge=Decimal("0"), le=Decimal("5"), max_digits=3, decimal_places=1, allow_inf_nan=False),
    AfterValidator(lambda v: v.quantize(Decimal("0.1"))),
]


def _normalize_currency(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z]{3}", value):
        raise ValueError("Currency must be a three-letter ISO-style code.")
    return value.upper()


def _validate_email(value: str) -> str:
    candidate = value.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", candidate):
        raise ValueError("Invalid email address.")
    return candidate


def _validate_url(value: str) -> str:
    candidate = value.strip()
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Website URL must be a valid http(s) URL.")
    return candidate


def _validate_phone(value: str) -> str:
    candidate = value.strip()
    if not re.fullmatch(r"[0-9+\-\s()]{3,40}", candidate):
        raise ValueError("Phone must be a contact string with valid characters.")
    return candidate


def _normalize_money(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("Monetary value must be finite.")
    if value < 0:
        raise ValueError("Monetary value cannot be negative.")
    if value > MAX_MONEY:
        raise ValueError("Monetary value exceeds the supported limit.")
    return quantize_money(value)


MoneyValue = Annotated[
    Decimal,
    Field(ge=Decimal("0"), le=MAX_MONEY, max_digits=12, decimal_places=2, allow_inf_nan=False),
    AfterValidator(_normalize_money),
]
Currency = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=3),
    AfterValidator(_normalize_currency),
]
Email = Annotated[str, AfterValidator(_validate_email)]
Phone = Annotated[str, AfterValidator(_validate_phone)]
Website = Annotated[str, AfterValidator(_validate_url)]


class VendorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: VendorName
    category: VendorCategory
    description: LongText | None = None
    contact_name: ShortText | None = None
    email: Email | None = None
    phone: Phone | None = None
    website_url: Website | None = None
    service_area: ShortText | None = None
    price_min: MoneyValue | None = None
    price_max: MoneyValue | None = None
    currency: Currency = "INR"
    estimated_cost: MoneyValue | None = None
    quoted_cost: MoneyValue | None = None
    pricing_notes: PricingNotes | None = None
    status: VendorStatus = VendorStatus.DISCOVERED
    rating: RatingValue | None = None
    notes: LongText | None = None
    availability: ShortText | None = None


class VendorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: VendorName | None = None
    category: VendorCategory | None = None
    description: LongText | None = None
    contact_name: ShortText | None = None
    email: Email | None = None
    phone: Phone | None = None
    website_url: Website | None = None
    service_area: ShortText | None = None
    price_min: MoneyValue | None = None
    price_max: MoneyValue | None = None
    currency: Currency | None = None
    estimated_cost: MoneyValue | None = None
    quoted_cost: MoneyValue | None = None
    final_cost: MoneyValue | None = None
    pricing_notes: PricingNotes | None = None
    status: VendorStatus | None = None
    rating: RatingValue | None = None
    notes: LongText | None = None
    availability: ShortText | None = None


class VendorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_id: str
    event_id: str
    name: str
    category: VendorCategory
    description: str | None
    contact_name: str | None
    email: str | None
    phone: str | None
    website_url: str | None
    service_area: str | None
    price_min: Decimal | None
    price_max: Decimal | None
    currency: str
    estimated_cost: Decimal | None
    quoted_cost: Decimal | None
    final_cost: Decimal | None
    pricing_notes: str | None
    status: VendorStatus
    rating: Decimal | None
    notes: str | None
    availability: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_vendor(cls, vendor: Vendor) -> Self:
        return cls(
            vendor_id=str(vendor.vendor_id),
            event_id=str(vendor.event_id),
            name=vendor.name,
            category=vendor.category,
            description=vendor.description,
            contact_name=vendor.contact_name,
            email=vendor.email,
            phone=vendor.phone,
            website_url=vendor.website_url,
            service_area=vendor.service_area,
            price_min=vendor.price_min,
            price_max=vendor.price_max,
            currency=vendor.currency,
            estimated_cost=vendor.estimated_cost,
            quoted_cost=vendor.quoted_cost,
            final_cost=vendor.final_cost,
            pricing_notes=vendor.pricing_notes,
            status=vendor.status,
            rating=vendor.rating,
            notes=vendor.notes,
            availability=vendor.availability,
            created_at=vendor.created_at,
            updated_at=vendor.updated_at,
        )


class VendorListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[VendorResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class VendorCompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_ids: list[str] = Field(min_length=2, max_length=10)
    max_price: Decimal | None = Field(default=None, ge=Decimal("0"), allow_inf_nan=False)
    prefer_service_area: str | None = Field(default=None, max_length=200)
    prefer_quick_response: bool = False


class VendorCompareItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_id: str
    name: str
    category: VendorCategory
    status: VendorStatus
    currency: str
    price_min: Decimal | None
    price_max: Decimal | None
    estimated_cost: Decimal | None
    quoted_cost: Decimal | None
    final_cost: Decimal | None
    rating: Decimal | None
    service_area: str | None
    availability: str | None
    budget_fit: str | None
    preference_match: list[str]
    missing: list[str]
    comparable_price: bool
    reasons_cannot_compare_fairly: list[str]
    notes: str | None


class VendorCompareResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[VendorCompareItem]
    criteria: list[str]
    limitations: list[str]
    ordering: str
