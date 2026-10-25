"""PostgreSQL-backed planning proposal repository."""

from typing import Any
from uuid import UUID

from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from app.core.exceptions import ResourceConflictError
from app.db.postgres import PostgresDatabase
from app.models.proposal import Proposal, ProposalStatus, ProposalType
from app.repositories.proposal_repository import ProposalRepository

_COLUMNS = (
    "id, event_id, owner_id, proposal_type, title, summary, payload, status, version, "
    "source_snapshot, created_at, updated_at, expires_at, approved_at, rejected_at"
)


def _row_to_proposal(row: dict[str, Any]) -> Proposal:
    return Proposal(
        proposal_id=row["id"],
        event_id=row["event_id"],
        owner_id=row["owner_id"],
        proposal_type=ProposalType(row["proposal_type"]),
        title=row["title"],
        summary=row["summary"],
        payload=dict(row["payload"] or {}),
        status=ProposalStatus(row["status"]),
        version=row["version"],
        source_snapshot=dict(row["source_snapshot"] or {}),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        expires_at=row["expires_at"],
        approved_at=row["approved_at"],
        rejected_at=row["rejected_at"],
    )


class PostgresProposalRepository(ProposalRepository):
    """Store proposals with owner-scoped SQL and optimistic version checks."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def create(self, proposal: Proposal) -> Proposal:
        with self._database.connection() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    f"""
                    INSERT INTO public.planning_proposals (
                        id, event_id, owner_id, proposal_type, title, summary, payload,
                        status, version, source_snapshot, created_at, updated_at,
                        expires_at, approved_at, rejected_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING {_COLUMNS}
                    """,
                    (
                        proposal.proposal_id,
                        proposal.event_id,
                        proposal.owner_id,
                        proposal.proposal_type.value,
                        proposal.title,
                        proposal.summary,
                        Jsonb(proposal.payload),
                        proposal.status.value,
                        proposal.version,
                        Jsonb(proposal.source_snapshot),
                        proposal.created_at,
                        proposal.updated_at,
                        proposal.expires_at,
                        proposal.approved_at,
                        proposal.rejected_at,
                    ),
                )
            except UniqueViolation as exc:
                raise ResourceConflictError(
                    "A proposal with this identifier already exists."
                ) from exc
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("The proposal insert returned no row.")
        return _row_to_proposal(row)

    def get(self, proposal_id: UUID, event_id: UUID, owner_id: UUID) -> Proposal | None:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_COLUMNS}
                FROM public.planning_proposals
                WHERE id = %s AND event_id = %s AND owner_id = %s
                """,
                (proposal_id, event_id, owner_id),
            )
            row = cursor.fetchone()
        return _row_to_proposal(row) if row is not None else None

    def list(
        self,
        owner_id: UUID,
        event_id: UUID,
        *,
        status: ProposalStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Proposal], int]:
        clauses = ["owner_id = %s", "event_id = %s"]
        params: list[object] = [owner_id, event_id]
        if status is not None:
            clauses.append("status = %s")
            params.append(status.value)
        where_clause = " AND ".join(clauses)

        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT count(*) AS total FROM public.planning_proposals WHERE {where_clause}",
                tuple(params),
            )
            count_row = cursor.fetchone()
            total = int(count_row["total"]) if count_row is not None else 0
            cursor.execute(
                f"""
                SELECT {_COLUMNS}
                FROM public.planning_proposals
                WHERE {where_clause}
                ORDER BY created_at ASC, id ASC
                LIMIT %s OFFSET %s
                """,
                (*params, limit, offset),
            )
            rows = cursor.fetchall()
        return [_row_to_proposal(row) for row in rows], total

    def update(
        self,
        owner_id: UUID,
        proposal: Proposal,
        *,
        expected_version: int,
    ) -> Proposal | None:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE public.planning_proposals
                SET payload = %s,
                    status = %s,
                    version = %s,
                    source_snapshot = %s,
                    updated_at = %s,
                    approved_at = %s,
                    rejected_at = %s
                WHERE id = %s AND event_id = %s AND owner_id = %s AND version = %s
                RETURNING {_COLUMNS}
                """,
                (
                    Jsonb(proposal.payload),
                    proposal.status.value,
                    proposal.version,
                    Jsonb(proposal.source_snapshot),
                    proposal.updated_at,
                    proposal.approved_at,
                    proposal.rejected_at,
                    proposal.proposal_id,
                    proposal.event_id,
                    owner_id,
                    expected_version,
                ),
            )
            row = cursor.fetchone()
        return _row_to_proposal(row) if row is not None else None
