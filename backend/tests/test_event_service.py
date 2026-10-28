"""Deterministic event service policy, timestamp, and isolation tests."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.core.exceptions import DomainValidationError, ResourceNotFoundError
from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate
from app.services.event_service import EventService
from tests.conftest import FIXED_NOW, TEST_USER_ID, MutableClock

EventPayloadFactory = Callable[..., dict[str, Any]]


def test_service_uses_injected_clock_for_timestamps(
    event_service: EventService,
    event_payload: EventPayloadFactory,
) -> None:
    event = event_service.create(TEST_USER_ID, EventCreate(**event_payload()))

    assert event.created_at == FIXED_NOW
    assert event.updated_at == FIXED_NOW
    assert event.created_at.utcoffset() == timedelta(0)
    assert event.updated_at.utcoffset() == timedelta(0)


def test_event_date_policy_uses_the_configured_timezone_at_utc_boundary(
    event_service: EventService,
    clock: MutableClock,
    event_payload: EventPayloadFactory,
) -> None:
    clock.now = datetime(2030, 5, 15, 20, 0, tzinfo=UTC)

    with pytest.raises(DomainValidationError) as exc_info:
        event_service.create(TEST_USER_ID, EventCreate(**event_payload(event_date="2030-05-15")))

    assert exc_info.value.issues[0].field == "body.event_date"
    assert "Asia/Kolkata" in exc_info.value.issues[0].message

    event = event_service.create(
        TEST_USER_ID, EventCreate(**event_payload(event_date="2030-05-16"))
    )
    assert event.event_date.isoformat() == "2030-05-16"


def test_service_rejects_past_event_dates(
    event_service: EventService,
    event_payload: EventPayloadFactory,
) -> None:
    with pytest.raises(DomainValidationError) as exc_info:
        event_service.create(TEST_USER_ID, EventCreate(**event_payload(event_date="2029-12-31")))

    assert "Event date must be today or later" in exc_info.value.issues[0].message


def test_service_requires_a_timezone_aware_clock(
    event_service: EventService,
    clock: MutableClock,
    event_payload: EventPayloadFactory,
) -> None:
    clock.now = datetime(2030, 5, 15, 8, 0)

    with pytest.raises(RuntimeError, match="timezone-aware"):
        event_service.create(TEST_USER_ID, EventCreate(**event_payload()))


def test_update_timestamp_remains_monotonic_with_a_backward_clock(
    event_service: EventService,
    clock: MutableClock,
    event_payload: EventPayloadFactory,
) -> None:
    created = event_service.create(TEST_USER_ID, EventCreate(**event_payload()))
    clock.now = FIXED_NOW - timedelta(days=1)

    updated = event_service.update(TEST_USER_ID, str(created.event_id), EventUpdate(name="Renamed"))

    assert updated.created_at == created.created_at
    assert updated.updated_at == created.updated_at + timedelta(microseconds=1)
    assert updated.name == "Renamed"


def test_update_rejects_null_non_nullable_fields_without_mutation(
    event_service: EventService,
    event_payload: EventPayloadFactory,
) -> None:
    created = event_service.create(TEST_USER_ID, EventCreate(**event_payload()))

    with pytest.raises(DomainValidationError) as exc_info:
        event_service.update(
            TEST_USER_ID,
            str(created.event_id),
            EventUpdate.model_validate({"name": None, "guest_count": None}),
        )

    assert {issue.field for issue in exc_info.value.issues} == {
        "body.name",
        "body.guest_count",
    }
    stored = event_service.get(TEST_USER_ID, str(created.event_id))
    assert stored == created


def test_service_returns_isolated_domain_copies(
    event_service: EventService,
    event_payload: EventPayloadFactory,
) -> None:
    created = event_service.create(TEST_USER_ID, EventCreate(**event_payload()))
    first_copy = event_service.get(TEST_USER_ID, str(created.event_id))
    second_copy = event_service.get(TEST_USER_ID, str(created.event_id))

    assert first_copy is not second_copy
    object.__setattr__(first_copy, "name", "Tampered Name")

    assert event_service.get(TEST_USER_ID, str(created.event_id)).name == created.name


@pytest.mark.parametrize(
    "invalid_id",
    ["not-a-uuid", "0" * 36, "{00000000-0000-4000-8000-000000000000}"],
)
def test_invalid_identifiers_are_treated_as_missing(
    invalid_id: str,
    event_service: EventService,
) -> None:
    with pytest.raises(ResourceNotFoundError):
        event_service.get(TEST_USER_ID, invalid_id)
    with pytest.raises(ResourceNotFoundError):
        event_service.update(TEST_USER_ID, invalid_id, EventUpdate(name="Renamed"))
    with pytest.raises(ResourceNotFoundError):
        event_service.delete(TEST_USER_ID, invalid_id)


def test_missing_identifiers_are_treated_as_not_found(
    event_service: EventService,
    event_payload: EventPayloadFactory,
) -> None:
    created = event_service.create(TEST_USER_ID, EventCreate(**event_payload()))

    event_service.delete(TEST_USER_ID, str(created.event_id))

    with pytest.raises(ResourceNotFoundError):
        event_service.get(TEST_USER_ID, str(created.event_id))
    with pytest.raises(ResourceNotFoundError):
        event_service.update(TEST_USER_ID, str(created.event_id), EventUpdate(name="Renamed"))
    with pytest.raises(ResourceNotFoundError):
        event_service.delete(TEST_USER_ID, str(created.event_id))


def test_in_memory_repository_handles_concurrent_creates(
    event_service: EventService,
    event_payload: EventPayloadFactory,
) -> None:
    def create(index: int) -> Event:
        return event_service.create(
            TEST_USER_ID, EventCreate(**event_payload(name=f"Event {index}"))
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        events = list(executor.map(create, range(100)))

    stored, total = event_service.list_events(TEST_USER_ID, limit=100, offset=0)

    assert len(events) == 100
    assert len({event.event_id for event in events}) == 100
    assert total == 100
    assert len(stored) == 100
