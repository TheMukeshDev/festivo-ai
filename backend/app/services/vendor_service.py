"""Vendor comparison and workflow service."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.core.clock import Clock, coerce_utc, utc_now
from app.core.exceptions import DomainValidationError, ResourceNotFoundError, ValidationIssue
from app.core.ids import parse_uuid
from app.models.event import Event
from app.models.vendor import ALLOWED_VENDOR_TRANSITIONS, Vendor, VendorCategory, VendorStatus
from app.repositories.event_repository import EventRepository
from app.repositories.vendor_repository import VendorRepository
from app.schemas.vendor import VendorCompareRequest, VendorCreate, VendorUpdate
from app.services.event_service import EventService
from app.services.task_service import TaskService

_EVENT_NOT_FOUND = "Event not found."
_VENDOR_NOT_FOUND = "Vendor not found."


@dataclass(frozen=True, slots=True)
class ComparisonItem:
    vendor: Vendor
    budget_fit: str | None
    preference_match: list[str]
    missing: list[str]
    comparable_price: bool
    reasons_cannot_compare_fairly: list[str]


class VendorService:
    def __init__(
        self,
        event_repository: EventRepository,
        vendor_repository: VendorRepository,
        event_service: EventService,
        task_service: TaskService,
        clock: Clock | None = None,
    ) -> None:
        self._event_repository = event_repository
        self._vendor_repository = vendor_repository
        self._event_service = event_service
        self._task_service = task_service
        self._clock = clock or utc_now

    def create(self, owner_id: UUID, raw_event_id: str, payload: VendorCreate) -> Vendor:
        event = self._require_event(owner_id, raw_event_id)
        now = self._now()
        if (
            payload.price_min is not None
            and payload.price_max is not None
            and payload.price_min > payload.price_max
        ):
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.price_min", message="price_min cannot exceed price_max."
                    )
                ]
            )
        vendor = Vendor(
            vendor_id=uuid4(),
            event_id=event.event_id,
            owner_id=owner_id,
            name=payload.name,
            category=payload.category,
            description=payload.description,
            contact_name=payload.contact_name,
            email=payload.email,
            phone=payload.phone,
            website_url=str(payload.website_url) if payload.website_url else None,
            service_area=payload.service_area,
            price_min=payload.price_min,
            price_max=payload.price_max,
            currency=payload.currency,
            estimated_cost=payload.estimated_cost,
            quoted_cost=payload.quoted_cost,
            final_cost=None,
            pricing_notes=payload.pricing_notes,
            status=payload.status,
            rating=payload.rating,
            notes=payload.notes,
            availability=payload.availability,
            created_at=now,
            updated_at=now,
        )
        created = self._vendor_repository.create(vendor)
        self._task_service.ensure_vendor_tasks(owner_id, event, created)
        return created

    def get(self, owner_id: UUID, raw_event_id: str, raw_vendor_id: str) -> Vendor:
        event = self._require_event(owner_id, raw_event_id)
        vendor_id = parse_uuid(raw_vendor_id, _VENDOR_NOT_FOUND)
        vendor = self._vendor_repository.get(vendor_id, event.event_id, owner_id)
        if vendor is None:
            raise ResourceNotFoundError(_VENDOR_NOT_FOUND)
        return vendor

    def list_vendors(
        self,
        owner_id: UUID,
        raw_event_id: str,
        *,
        category: VendorCategory | None,
        status: VendorStatus | None,
        min_price: float | None,
        max_price: float | None,
        name: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Vendor], int]:
        event = self._require_event(owner_id, raw_event_id)
        return self._vendor_repository.list(
            owner_id,
            event.event_id,
            category=category,
            status=status,
            min_price=min_price,
            max_price=max_price,
            name_query=name,
            limit=limit,
            offset=offset,
        )

    def update(
        self, owner_id: UUID, raw_event_id: str, raw_vendor_id: str, payload: VendorUpdate
    ) -> Vendor:
        event = self._require_event(owner_id, raw_event_id)
        vendor_id = parse_uuid(raw_vendor_id, _VENDOR_NOT_FOUND)
        vendor = self._vendor_repository.get(vendor_id, event.event_id, owner_id)
        if vendor is None:
            raise ResourceNotFoundError(_VENDOR_NOT_FOUND)

        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return vendor

        self._reject_protected_fields(changes)
        self._validate_price_range(vendor, changes)

        if "website_url" in changes and changes["website_url"] is not None:
            changes["website_url"] = str(changes["website_url"])
        new_status = self._validate_status_transition(vendor, changes)

        now = self._now()
        updated = replace(
            vendor,
            **changes,
            updated_at=max(now, vendor.updated_at + timedelta(microseconds=1)),
        )
        saved = self._vendor_repository.update(owner_id, updated)
        if saved is None:
            raise ResourceNotFoundError(_VENDOR_NOT_FOUND)
        if new_status is not None and new_status != vendor.status:
            self._task_service.ensure_vendor_tasks(owner_id, event, saved)
        return saved

    @staticmethod
    def _reject_protected_fields(changes: dict[str, Any]) -> None:
        """Refuse direct writes to identity and timestamp fields."""
        issues = []
        for field in ("vendor_id", "event_id", "owner_id", "created_at", "updated_at"):
            if field in changes:
                issues.append(
                    ValidationIssue(field=f"body.{field}", message="This field cannot be assigned.")
                )
        if issues:
            raise DomainValidationError(issues)

    @staticmethod
    def _validate_price_range(vendor: Vendor, changes: dict[str, Any]) -> None:
        """Ensure the effective price range stays ordered after the update."""
        new_min = changes.get("price_min")
        new_max = changes.get("price_max")
        effective_min = new_min if new_min is not None else vendor.price_min
        effective_max = new_max if new_max is not None else vendor.price_max
        if (
            effective_min is not None
            and effective_max is not None
            and effective_min > effective_max
        ):
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.price_min",
                        message="price_min cannot exceed price_max.",
                    )
                ]
            )

    @staticmethod
    def _validate_status_transition(vendor: Vendor, changes: dict[str, Any]) -> VendorStatus | None:
        """Validate a requested status change and return it when it differs."""
        new_status: VendorStatus | None = changes.get("status")
        if new_status is None or new_status == vendor.status:
            return new_status
        allowed = ALLOWED_VENDOR_TRANSITIONS.get(vendor.status, set())
        if new_status not in allowed:
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.status",
                        message="Invalid vendor status transition.",
                    )
                ]
            )
        if new_status == VendorStatus.BOOKED:
            final_or_quote = (
                vendor.final_cost is not None
                or vendor.quoted_cost is not None
                or changes.get("final_cost") is not None
                or changes.get("quoted_cost") is not None
            )
            if not final_or_quote:
                raise DomainValidationError(
                    [
                        ValidationIssue(
                            field="body.status",
                            message=("Booking requires confirmation details or quoted/final cost."),
                        )
                    ]
                )
        return new_status

    def delete(self, owner_id: UUID, raw_event_id: str, raw_vendor_id: str) -> None:
        event = self._require_event(owner_id, raw_event_id)
        vendor_id = parse_uuid(raw_vendor_id, _VENDOR_NOT_FOUND)
        vendor = self._vendor_repository.get(vendor_id, event.event_id, owner_id)
        if vendor is None:
            raise ResourceNotFoundError(_VENDOR_NOT_FOUND)
        if vendor.status == VendorStatus.BOOKED:
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.status",
                        message="Booked vendors cannot be deleted under the documented lifecycle policy.",
                    )
                ]
            )
        if not self._vendor_repository.delete(vendor_id, event.event_id, owner_id):
            raise ResourceNotFoundError(_VENDOR_NOT_FOUND)

    def compare(
        self, owner_id: UUID, raw_event_id: str, payload: VendorCompareRequest
    ) -> dict[str, Any]:
        event = self._require_event(owner_id, raw_event_id)
        vendors = self._load_compared_vendors(owner_id, event, payload)

        # Deterministic ordering by category, then name, then id.
        categories = {v.category for v in vendors}
        ordered = sorted(
            vendors, key=lambda v: (v.category.value, v.name.lower(), str(v.vendor_id))
        )
        currency = event.currency
        budget_limit = getattr(event, "budget_amount", None)

        items_out = [
            self._compare_item(
                v,
                payload,
                categories=categories,
                currency=currency,
                budget_limit=budget_limit,
            )
            for v in ordered
        ]
        criteria = [
            "Category compatibility",
            "Comparable price (same currency)",
            "Service area match (if specified)",
            "Budget fit (when budget data available)",
            "Preference matches (explicit)",
            "Available recorded info (no fabricated defaults)",
        ]
        limitations = [
            "Do not mix currencies without conversion rates (none implemented).",
            "Missing data remains missing.",
            "Lowest price is not the only factor.",
            "Availability/ratings only used if explicitly recorded.",
        ]
        return {
            "items": items_out,
            "criteria": criteria,
            "limitations": limitations,
            "ordering": "category, name, vendor_id (deterministic)",
        }

    def _load_compared_vendors(
        self,
        owner_id: UUID,
        event: Event,
        payload: VendorCompareRequest,
    ) -> "list[Vendor]":
        """Resolve and authorize every vendor referenced by the comparison."""
        vendors = []
        for raw_vid in payload.vendor_ids:
            vid = parse_uuid(raw_vid, _VENDOR_NOT_FOUND)
            vendor = self._vendor_repository.get(vid, event.event_id, owner_id)
            if vendor is None:
                raise ResourceNotFoundError(_VENDOR_NOT_FOUND)
            vendors.append(vendor)
        return vendors

    def _compare_item(
        self,
        v: Vendor,
        payload: VendorCompareRequest,
        *,
        categories: set[VendorCategory],
        currency: str,
        budget_limit: Decimal | None,
    ) -> dict[str, Any]:
        """Build the comparison entry for a single vendor."""
        missing, reasons, comparable_price, comp_price = self._item_price_context(
            v, payload, currency, categories
        )
        budget_fit = self._budget_fit(budget_limit, comparable_price, comp_price)
        pref_match = self._preference_matches(payload, v)
        return {
            "vendor_id": str(v.vendor_id),
            "name": v.name,
            "category": v.category,
            "status": v.status,
            "currency": v.currency,
            "price_min": v.price_min,
            "price_max": v.price_max,
            "estimated_cost": v.estimated_cost,
            "quoted_cost": v.quoted_cost,
            "final_cost": v.final_cost,
            "rating": v.rating,
            "service_area": v.service_area,
            "availability": v.availability,
            "budget_fit": budget_fit,
            "preference_match": pref_match,
            "missing": missing,
            "comparable_price": comparable_price,
            "reasons_cannot_compare_fairly": reasons,
            "notes": v.notes,
        }

    @staticmethod
    def _item_price_context(
        v: Vendor,
        payload: VendorCompareRequest,
        currency: str,
        categories: set[VendorCategory],
    ) -> "tuple[list[str], list[str], bool, Decimal | None]":
        """Collect missing-data notes, fairness reasons, and the comparable price."""
        missing = []
        reasons = []
        if len(categories) > 1:
            reasons.append("Different categories; not ranked together for a single 'best' choice.")
        comparable_price = False
        comp_price = None
        if v.quoted_cost is not None or v.estimated_cost is not None or v.price_min is not None:
            if v.currency != currency:
                reasons.append(
                    "Currency differs from event currency; price not numerically compared."
                )
            else:
                comparable_price = True
                comp_price = v.quoted_cost or v.estimated_cost or v.price_min
        else:
            missing.append("price/quote")
        if v.rating is None:
            missing.append("rating")
        if v.availability is None:
            missing.append("availability")
        if v.service_area is None and payload.prefer_service_area:
            missing.append("service_area")
        return missing, reasons, comparable_price, comp_price

    @staticmethod
    def _budget_fit(
        budget_limit: Decimal | None,
        comparable_price: bool,
        comp_price: Decimal | None,
    ) -> str | None:
        """Classify the comparable price against the event budget, when known."""
        if budget_limit is not None and comparable_price and comp_price is not None:
            if comp_price <= budget_limit:
                return "within_event_budget"
            return "over_event_budget"
        if budget_limit is not None and not comparable_price:
            return "unknown_due_to_missing_price_or_currency"
        return None

    @staticmethod
    def _preference_matches(payload: VendorCompareRequest, v: Vendor) -> "list[str]":
        """Record which explicit user preferences this vendor satisfies."""
        pref_match = []
        if (
            payload.prefer_service_area
            and v.service_area
            and payload.prefer_service_area.lower() in v.service_area.lower()
        ):
            pref_match.append("service_area_match")
        if payload.prefer_quick_response and v.status in {
            VendorStatus.CONTACTED,
            VendorStatus.QUOTED,
        }:
            pref_match.append("active_response_state")
        if v.rating is not None and v.rating >= Decimal("4.0"):
            pref_match.append("high_recorded_rating")
        return pref_match

    def _require_event(self, owner_id: UUID, raw_event_id: str) -> Event:
        event_id = parse_uuid(raw_event_id, _EVENT_NOT_FOUND)
        event = self._event_repository.get(event_id, owner_id)
        if event is None:
            raise ResourceNotFoundError(_EVENT_NOT_FOUND)
        return event

    def _now(self) -> datetime:
        return coerce_utc(self._clock())
