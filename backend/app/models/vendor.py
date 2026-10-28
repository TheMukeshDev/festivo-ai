"""Immutable vendor domain model."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class VendorCategory(StrEnum):
    """Vendor categories supported for event planning."""

    VENUE = "venue"
    CATERING = "catering"
    DECORATION = "decoration"
    PHOTOGRAPHY_VIDEOGRAPHY = "photography_videography"
    ENTERTAINMENT_MUSIC = "entertainment_music"
    MAKEUP_STYLING = "makeup_styling"
    INVITATIONS_PRINTING = "invitations_printing"
    TRANSPORTATION = "transportation"
    EQUIPMENT_RENTALS = "equipment_rentals"
    EVENT_COORDINATION = "event_coordination"
    OTHER = "other"


class VendorStatus(StrEnum):
    """Lifecycle state of a vendor in the decision workflow."""

    DISCOVERED = "discovered"
    SHORTLISTED = "shortlisted"
    CONTACTED = "contacted"
    QUOTED = "quoted"
    SELECTED = "selected"
    BOOKED = "booked"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


ALLOWED_VENDOR_TRANSITIONS: dict[VendorStatus, set[VendorStatus]] = {
    VendorStatus.DISCOVERED: {
        VendorStatus.SHORTLISTED,
        VendorStatus.CONTACTED,
        VendorStatus.REJECTED,
        VendorStatus.CANCELLED,
    },
    VendorStatus.SHORTLISTED: {
        VendorStatus.CONTACTED,
        VendorStatus.QUOTED,
        VendorStatus.REJECTED,
        VendorStatus.CANCELLED,
    },
    VendorStatus.CONTACTED: {
        VendorStatus.QUOTED,
        VendorStatus.SHORTLISTED,
        VendorStatus.REJECTED,
        VendorStatus.CANCELLED,
    },
    VendorStatus.QUOTED: {
        VendorStatus.SELECTED,
        VendorStatus.CONTACTED,
        VendorStatus.REJECTED,
        VendorStatus.CANCELLED,
    },
    VendorStatus.SELECTED: {
        VendorStatus.BOOKED,
        VendorStatus.QUOTED,
        VendorStatus.REJECTED,
        VendorStatus.CANCELLED,
    },
    VendorStatus.BOOKED: {VendorStatus.CANCELLED},
    VendorStatus.REJECTED: set(),
    VendorStatus.CANCELLED: set(),
}


@dataclass(frozen=True, slots=True)
class Vendor:
    """A vendor associated with an event."""

    vendor_id: UUID
    event_id: UUID
    owner_id: UUID
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
