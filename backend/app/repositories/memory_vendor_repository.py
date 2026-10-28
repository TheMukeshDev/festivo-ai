"""Thread-safe in-memory vendor repository."""

import copy
from threading import RLock
from uuid import UUID

from app.models.vendor import Vendor, VendorCategory, VendorStatus
from app.repositories.vendor_repository import VendorRepository


class InMemoryVendorRepository(VendorRepository):
    def __init__(self) -> None:
        self._vendors: dict[UUID, Vendor] = {}
        self._lock = RLock()

    def create(self, vendor: Vendor) -> Vendor:
        with self._lock:
            self._vendors[vendor.vendor_id] = copy.deepcopy(vendor)
            return copy.deepcopy(vendor)

    def get(self, vendor_id: UUID, event_id: UUID, owner_id: UUID) -> Vendor | None:
        with self._lock:
            vendor = self._vendors.get(vendor_id)
            if vendor is None or vendor.owner_id != owner_id or vendor.event_id != event_id:
                return None
            return copy.deepcopy(vendor)

    def list(
        self,
        owner_id: UUID,
        event_id: UUID,
        *,
        category: VendorCategory | None,
        status: VendorStatus | None,
        min_price: float | None,
        max_price: float | None,
        name_query: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Vendor], int]:
        with self._lock:
            matches = []
            for vendor in self._vendors.values():
                if vendor.owner_id != owner_id or vendor.event_id != event_id:
                    continue
                if category is not None and vendor.category != category:
                    continue
                if status is not None and vendor.status != status:
                    continue
                if name_query and name_query.lower() not in vendor.name.lower():
                    continue
                if min_price is not None:
                    # only compare when comparable price exists
                    comp = vendor.quoted_cost or vendor.estimated_cost or vendor.price_min
                    if comp is None or float(comp) < min_price:
                        continue
                if max_price is not None:
                    comp = vendor.quoted_cost or vendor.estimated_cost or vendor.price_max
                    if comp is None or float(comp) > max_price:
                        continue
                matches.append(copy.deepcopy(vendor))
            matches.sort(key=lambda v: (v.created_at, v.vendor_id))
            total = len(matches)
            page = matches[offset : offset + limit]
            return page, total

    def update(self, owner_id: UUID, vendor: Vendor) -> Vendor | None:
        with self._lock:
            existing = self._vendors.get(vendor.vendor_id)
            if (
                existing is None
                or existing.owner_id != owner_id
                or existing.event_id != vendor.event_id
            ):
                return None
            self._vendors[vendor.vendor_id] = copy.deepcopy(vendor)
            return copy.deepcopy(vendor)

    def delete(self, vendor_id: UUID, event_id: UUID, owner_id: UUID) -> bool:
        with self._lock:
            existing = self._vendors.get(vendor_id)
            if existing is None or existing.owner_id != owner_id or existing.event_id != event_id:
                return False
            del self._vendors[vendor_id]
            return True
