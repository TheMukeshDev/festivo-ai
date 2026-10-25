"""PostgreSQL-backed timeline and task repository."""

from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg.errors import UniqueViolation

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.db.postgres import PostgresDatabase
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.timeline import Timeline
from app.repositories.planning_repository import PlanningRepository

_TIMELINE_COLUMNS = (
    "id, event_id, owner_id, start_date, end_date, timezone, generated_at, "
    "created_at, updated_at"
)
_TASK_COLUMNS = (
    "id, event_id, owner_id, timeline_id, template_key, title, description, status, "
    "priority, due_at, assigned_to, estimated_cost, actual_cost, currency, sort_order, "
    "completed_at, created_at, updated_at"
)

_TIMELINE_CONFLICT = "An event timeline already exists."
_TASK_CONFLICT = "A task with this template key already exists."
_TASK_NOT_FOUND = "Task not found."


def _row_to_timeline(row: dict[str, Any]) -> Timeline:
    return Timeline(
        timeline_id=row["id"],
        event_id=row["event_id"],
        owner_id=row["owner_id"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        timezone=row["timezone"],
        generated_at=row["generated_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_task(row: dict[str, Any]) -> Task:
    return Task(
        task_id=row["id"],
        event_id=row["event_id"],
        owner_id=row["owner_id"],
        timeline_id=row["timeline_id"],
        template_key=row["template_key"],
        title=row["title"],
        description=row["description"],
        status=TaskStatus(row["status"]),
        priority=TaskPriority(row["priority"]),
        due_at=row["due_at"],
        assigned_to=row["assigned_to"],
        estimated_cost=row["estimated_cost"],
        actual_cost=row["actual_cost"],
        currency=row["currency"],
        sort_order=row["sort_order"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _task_values(task: Task) -> tuple[object, ...]:
    return (
        task.task_id,
        task.event_id,
        task.owner_id,
        task.timeline_id,
        task.template_key,
        task.title,
        task.description,
        task.status.value,
        task.priority.value,
        task.due_at,
        task.assigned_to,
        task.estimated_cost,
        task.actual_cost,
        task.currency,
        task.sort_order,
        task.completed_at,
        task.created_at,
        task.updated_at,
    )


class PostgresPlanningRepository(PlanningRepository):
    """Store timelines and tasks in Supabase PostgreSQL with owner-scoped SQL."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def create_timeline(self, timeline: Timeline, tasks: list[Task]) -> Timeline:
        with self._database.connection() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    f"""
                    INSERT INTO public.event_timelines (
                        id, event_id, owner_id, start_date, end_date, timezone,
                        generated_at, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING {_TIMELINE_COLUMNS}
                    """,
                    (
                        timeline.timeline_id,
                        timeline.event_id,
                        timeline.owner_id,
                        timeline.start_date,
                        timeline.end_date,
                        timeline.timezone,
                        timeline.generated_at,
                        timeline.created_at,
                        timeline.updated_at,
                    ),
                )
                row = cursor.fetchone()
                for task in tasks:
                    cursor.execute(
                        """
                        INSERT INTO public.event_tasks (
                            id, event_id, owner_id, timeline_id, template_key, title,
                            description, status, priority, due_at, assigned_to,
                            estimated_cost, actual_cost, currency, sort_order,
                            completed_at, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s)
                        """,
                        _task_values(task),
                    )
            except UniqueViolation as exc:
                raise ResourceConflictError(_TIMELINE_CONFLICT) from exc
        if row is None:
            raise RuntimeError("The timeline insert returned no row.")
        return _row_to_timeline(row)

    def get_timeline(self, event_id: UUID, owner_id: UUID) -> Timeline | None:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_TIMELINE_COLUMNS}
                FROM public.event_timelines
                WHERE event_id = %s AND owner_id = %s
                """,
                (event_id, owner_id),
            )
            row = cursor.fetchone()
        return _row_to_timeline(row) if row is not None else None

    def update_timeline(self, owner_id: UUID, timeline: Timeline) -> Timeline | None:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE public.event_timelines
                SET start_date = %s,
                    end_date = %s,
                    timezone = %s,
                    generated_at = %s,
                    updated_at = %s
                WHERE id = %s AND event_id = %s AND owner_id = %s
                RETURNING {_TIMELINE_COLUMNS}
                """,
                (
                    timeline.start_date,
                    timeline.end_date,
                    timeline.timezone,
                    timeline.generated_at,
                    timeline.updated_at,
                    timeline.timeline_id,
                    timeline.event_id,
                    owner_id,
                ),
            )
            row = cursor.fetchone()
        return _row_to_timeline(row) if row is not None else None

    def add_generated_tasks(
        self,
        owner_id: UUID,
        timeline: Timeline,
        tasks: list[Task],
        *,
        generated_at: datetime,
    ) -> tuple[Timeline, list[Task]]:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE public.event_timelines
                SET generated_at = %s, updated_at = %s
                WHERE id = %s AND event_id = %s AND owner_id = %s
                RETURNING {_TIMELINE_COLUMNS}
                """,
                (
                    generated_at,
                    timeline.updated_at,
                    timeline.timeline_id,
                    timeline.event_id,
                    owner_id,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise ResourceNotFoundError("Timeline not found.")

            added: list[Task] = []
            for task in tasks:
                cursor.execute(
                    f"""
                    INSERT INTO public.event_tasks (
                        id, event_id, owner_id, timeline_id, template_key, title,
                        description, status, priority, due_at, assigned_to,
                        estimated_cost, actual_cost, currency, sort_order,
                        completed_at, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s)
                    ON CONFLICT (event_id, template_key)
                        WHERE template_key IS NOT NULL
                    DO NOTHING
                    RETURNING {_TASK_COLUMNS}
                    """,
                    _task_values(task),
                )
                inserted = cursor.fetchone()
                if inserted is not None:
                    added.append(_row_to_task(inserted))
        return _row_to_timeline(row), added

    def get_task_by_template_key(
        self,
        owner_id: UUID,
        event_id: UUID,
        template_key: str,
    ) -> Task | None:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_TASK_COLUMNS}
                FROM public.event_tasks
                WHERE owner_id = %s AND event_id = %s AND template_key = %s
                """,
                (owner_id, event_id, template_key),
            )
            row = cursor.fetchone()
        return _row_to_task(row) if row is not None else None

    def create_task(self, task: Task) -> Task:
        with self._database.connection() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    f"""
                    INSERT INTO public.event_tasks (
                        id, event_id, owner_id, timeline_id, template_key, title,
                        description, status, priority, due_at, assigned_to,
                        estimated_cost, actual_cost, currency, sort_order,
                        completed_at, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s)
                    RETURNING {_TASK_COLUMNS}
                    """,
                    _task_values(task),
                )
            except UniqueViolation as exc:
                raise ResourceConflictError(_TASK_CONFLICT) from exc
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("The task insert returned no row.")
        return _row_to_task(row)

    def get_task(
        self,
        task_id: UUID,
        event_id: UUID,
        owner_id: UUID,
    ) -> Task | None:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_TASK_COLUMNS}
                FROM public.event_tasks
                WHERE id = %s AND event_id = %s AND owner_id = %s
                """,
                (task_id, event_id, owner_id),
            )
            row = cursor.fetchone()
        return _row_to_task(row) if row is not None else None

    def update_task(self, owner_id: UUID, task: Task) -> Task | None:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE public.event_tasks
                SET timeline_id = %s,
                    title = %s,
                    description = %s,
                    status = %s,
                    priority = %s,
                    due_at = %s,
                    assigned_to = %s,
                    estimated_cost = %s,
                    actual_cost = %s,
                    currency = %s,
                    sort_order = %s,
                    completed_at = %s,
                    updated_at = %s
                WHERE id = %s AND event_id = %s AND owner_id = %s
                RETURNING {_TASK_COLUMNS}
                """,
                (
                    task.timeline_id,
                    task.title,
                    task.description,
                    task.status.value,
                    task.priority.value,
                    task.due_at,
                    task.assigned_to,
                    task.estimated_cost,
                    task.actual_cost,
                    task.currency,
                    task.sort_order,
                    task.completed_at,
                    task.updated_at,
                    task.task_id,
                    task.event_id,
                    owner_id,
                ),
            )
            row = cursor.fetchone()
        return _row_to_task(row) if row is not None else None

    def delete_task(
        self,
        task_id: UUID,
        event_id: UUID,
        owner_id: UUID,
    ) -> bool:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM public.event_tasks
                WHERE id = %s AND event_id = %s AND owner_id = %s
                RETURNING id
                """,
                (task_id, event_id, owner_id),
            )
            row = cursor.fetchone()
        return row is not None

    def list_tasks(
        self,
        owner_id: UUID,
        event_id: UUID,
        *,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        timeline_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Task], int]:
        clauses = ["owner_id = %s", "event_id = %s"]
        params: list[object] = [owner_id, event_id]
        if status is not None:
            clauses.append("status = %s")
            params.append(status.value)
        if priority is not None:
            clauses.append("priority = %s")
            params.append(priority.value)
        if timeline_id is not None:
            clauses.append("timeline_id = %s")
            params.append(timeline_id)
        where_clause = " AND ".join(clauses)

        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT count(*) AS total FROM public.event_tasks WHERE {where_clause}",
                tuple(params),
            )
            count_row = cursor.fetchone()
            total = int(count_row["total"]) if count_row is not None else 0
            cursor.execute(
                f"""
                SELECT {_TASK_COLUMNS}
                FROM public.event_tasks
                WHERE {where_clause}
                ORDER BY sort_order ASC, created_at ASC, id ASC
                LIMIT %s OFFSET %s
                """,
                (*params, limit, offset),
            )
            rows = cursor.fetchall()
        return [_row_to_task(row) for row in rows], total

    def list_timeline_tasks(
        self,
        owner_id: UUID,
        event_id: UUID,
        timeline_id: UUID,
    ) -> list[Task]:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_TASK_COLUMNS}
                FROM public.event_tasks
                WHERE owner_id = %s AND event_id = %s AND timeline_id = %s
                ORDER BY sort_order ASC, created_at ASC, id ASC
                """,
                (owner_id, event_id, timeline_id),
            )
            rows = cursor.fetchall()
        return [_row_to_task(row) for row in rows]
