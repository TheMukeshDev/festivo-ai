"""PostgreSQL-backed event repository."""

from typing import Any
from uuid import UUID

from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from app.core.exceptions import ResourceConflictError
from app.db.postgres import PostgresDatabase
from app.models.event import Event, EventType
from app.repositories.event_repository import EventRepository

_COLUMNS = (
    "id, owner_id, name, event_type, event_date, location, guest_count, "
    "budget_amount, currency, timezone, description, preferences, event_constraints, "
    "created_at, updated_at"
)


def _row_to_event(row: dict[str, Any]) -> Event:
    return Event(
        event_id=row["id"],
        owner_id=row["owner_id"],
        name=row["name"],
        event_type=EventType(row["event_type"]),
        event_date=row["event_date"],
        location=row["location"],
        guest_count=row["guest_count"],
        budget_amount=row["budget_amount"],
        currency=row["currency"],
        timezone=row["timezone"],
        description=row["description"],
        preferences=tuple(row["preferences"] or ()),
        constraints=tuple(row["event_constraints"] or ()),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresEventRepository(EventRepository):
    """Store events in the Supabase PostgreSQL `public.events` table."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def save(self, event: Event) -> Event:
        with self._database.connection() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    f"""
                    INSERT INTO public.events (
                        id, owner_id, name, event_type, event_date, location, guest_count,
                        budget_amount, currency, timezone, description, preferences,
                        event_constraints, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING {_COLUMNS}
                    """,
                    (
                        event.event_id,
                        event.owner_id,
                        event.name,
                        event.event_type.value,
                        event.event_date,
                        event.location,
                        event.guest_count,
                        event.budget_amount,
                        event.currency,
                        event.timezone,
                        event.description,
                        Jsonb(list(event.preferences)),
                        Jsonb(list(event.constraints)),
                        event.created_at,
                        event.updated_at,
                    ),
                )
            except UniqueViolation as exc:
                raise ResourceConflictError(
                    "An event with this identifier already exists."
                ) from exc
            row = cursor.fetchone()

        if row is None:
            raise RuntimeError("The event insert returned no row.")
        return _row_to_event(row)

    def get(self, event_id: UUID, owner_id: UUID) -> Event | None:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_COLUMNS} FROM public.events WHERE id = %s AND owner_id = %s",
                (event_id, owner_id),
            )
            row = cursor.fetchone()
        return _row_to_event(row) if row is not None else None

    def list(
        self,
        owner_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Event], int]:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) AS total FROM public.events WHERE owner_id = %s",
                (owner_id,),
            )
            count_row = cursor.fetchone()
            total = int(count_row["total"]) if count_row is not None else 0

            cursor.execute(
                f"""
                SELECT {_COLUMNS}
                FROM public.events
                WHERE owner_id = %s
                ORDER BY created_at ASC, id ASC
                LIMIT %s OFFSET %s
                """,
                (owner_id, limit, offset),
            )
            rows = cursor.fetchall()

        return [_row_to_event(row) for row in rows], total

    def update(self, owner_id: UUID, event: Event) -> Event | None:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE public.events
                SET name = %s,
                    event_type = %s,
                    event_date = %s,
                    location = %s,
                    guest_count = %s,
                    budget_amount = %s,
                    currency = %s,
                    timezone = %s,
                    description = %s,
                    preferences = %s,
                    event_constraints = %s,
                    updated_at = %s
                WHERE id = %s AND owner_id = %s
                RETURNING {_COLUMNS}
                """,
                (
                    event.name,
                    event.event_type.value,
                    event.event_date,
                    event.location,
                    event.guest_count,
                    event.budget_amount,
                    event.currency,
                    event.timezone,
                    event.description,
                    Jsonb(list(event.preferences)),
                    Jsonb(list(event.constraints)),
                    event.updated_at,
                    event.event_id,
                    owner_id,
                ),
            )
            row = cursor.fetchone()
        return _row_to_event(row) if row is not None else None

    def delete(self, event_id: UUID, owner_id: UUID) -> bool:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM public.events WHERE id = %s AND owner_id = %s RETURNING id",
                (event_id, owner_id),
            )
            row = cursor.fetchone()
        return row is not None
