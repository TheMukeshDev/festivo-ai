"""Vendor persistence contract."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.models.vendor import Vendor, VendorCategory, VendorStatus


class VendorRepository(ABC):
    @abstractmethod
    def create(self, vendor: Vendor) -> Vendor:
        """Create a vendor owned by the event owner."""

    @abstractmethod
    def get(self, vendor_id: UUID, event_id: UUID, owner_id: UUID) -> Vendor | None:
        """Get an owned vendor belonging to the event."""

    @abstractmethod
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
        """List vendors for an owned event with filters and pagination."""

    @abstractmethod
    def update(self, owner_id: UUID, vendor: Vendor) -> Vendor | None:
        """Update an owned vendor."""

    @abstractmethod
    def delete(self, vendor_id: UUID, event_id: UUID, owner_id: UUID) -> bool:
        """Delete an owned vendor."""
