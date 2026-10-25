"""Thread-safe in-memory planning proposal repository."""

import copy
from threading import RLock
from uuid import UUID

from app.models.proposal import Proposal, ProposalStatus
from app.repositories.proposal_repository import ProposalRepository


class InMemoryProposalRepository(ProposalRepository):
    """Process-local proposal store with optimistic version checks."""

    def __init__(self) -> None:
        self._proposals: dict[UUID, Proposal] = {}
        self._lock = RLock()

    def create(self, proposal: Proposal) -> Proposal:
        with self._lock:
            self._proposals[proposal.proposal_id] = copy.deepcopy(proposal)
            return copy.deepcopy(proposal)

    def get(self, proposal_id: UUID, event_id: UUID, owner_id: UUID) -> Proposal | None:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            if (
                proposal is None
                or proposal.owner_id != owner_id
                or proposal.event_id != event_id
            ):
                return None
            return copy.deepcopy(proposal)

    def list(
        self,
        owner_id: UUID,
        event_id: UUID,
        *,
        status: ProposalStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Proposal], int]:
        with self._lock:
            matches = [
                proposal
                for proposal in self._proposals.values()
                if proposal.owner_id == owner_id
                and proposal.event_id == event_id
                and (status is None or proposal.status == status)
            ]
            matches.sort(
                key=lambda proposal: (
                    proposal.created_at,
                    str(proposal.proposal_id),
                )
            )
            total = len(matches)
            page = matches[offset : offset + limit]
            return [copy.deepcopy(proposal) for proposal in page], total

    def update(
        self,
        owner_id: UUID,
        proposal: Proposal,
        *,
        expected_version: int,
    ) -> Proposal | None:
        with self._lock:
            existing = self._proposals.get(proposal.proposal_id)
            if (
                existing is None
                or existing.owner_id != owner_id
                or existing.event_id != proposal.event_id
                or existing.version != expected_version
            ):
                return None
            self._proposals[proposal.proposal_id] = copy.deepcopy(proposal)
            return copy.deepcopy(proposal)
