"""Persistence contract for owner-scoped planning proposals."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.models.proposal import Proposal, ProposalStatus


class ProposalRepository(ABC):
    """Store proposals without mutating planning or financial records."""

    @abstractmethod
    def create(self, proposal: Proposal) -> Proposal:
        """Persist a validated proposal."""

    @abstractmethod
    def get(self, proposal_id: UUID, event_id: UUID, owner_id: UUID) -> Proposal | None:
        """Return one owned proposal belonging to the event."""

    @abstractmethod
    def list(
        self,
        owner_id: UUID,
        event_id: UUID,
        *,
        status: ProposalStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Proposal], int]:
        """Return a deterministic page of owned proposals."""

    @abstractmethod
    def update(
        self,
        owner_id: UUID,
        proposal: Proposal,
        *,
        expected_version: int,
    ) -> Proposal | None:
        """Replace a proposal only when its version matches."""
