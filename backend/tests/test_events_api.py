"""Event CRUD, validation, pagination, and isolation API tests."""

import json
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import FIXED_NOW, MutableClock

EventPayloadFactory = Callable[..., dict[str, Any]]


def _create_event(
    client: TestClient,
    event_payload: EventPayloadFactory,
    **overrides: Any,
) -> dict[str, Any]:
    response = client.post("/api/v1/events", json=event_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def _field_paths(response: Any) -> set[str]:
    return {field["field"] for field in response.json().get("error", {}).get("fields", [])}


def _timezone_aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    assert parsed.utcoffset() is not None
    return parsed


def test_create_event_returns_server_managed_event(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    payload = event_payload(
        name="  Ananya and Rohan Wedding  ",
        currency="inr",
        budget_amount=750000,
    )

    response = client.post("/api/v1/events", json=payload)

    assert response.status_code == 201, response.text
    event = response.json()
    assert UUID(event["event_id"])
    assert event["name"] == "Ananya and Rohan Wedding"
    assert event["event_type"] == "wedding"
    assert event["event_date"] == "2030-06-15"
    assert event["location"] == "Bengaluru"
    assert event["guest_count"] == 150
    assert event["budget_amount"] == "750000.00"
    assert event["currency"] == "INR"
    assert event["description"] == "A relaxed celebration with family and friends."
    assert event["preferences"] == ["Pastel decor", "Vegetarian menu"]
    assert event["constraints"] == ["No loud music after 10 PM"]
    assert _timezone_aware(event["created_at"]) == FIXED_NOW
    assert event["updated_at"] == event["created_at"]


def test_optional_event_fields_receive_safe_defaults(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    payload = event_payload()
    for field in ("currency", "description", "preferences", "constraints"):
        payload.pop(field)

    event = _create_event(client, lambda: payload)

    assert event["currency"] == "INR"
    assert event["description"] is None
    assert event["preferences"] == []
    assert event["constraints"] == []


@pytest.mark.parametrize(
    "event_type",
    ["wedding", "birthday", "college_event", "community_event"],
)
def test_supported_event_types_are_accepted(
    event_type: str,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(client, event_payload, event_type=event_type)

    assert event["event_type"] == event_type


@pytest.mark.parametrize(
    "field",
    ["name", "event_type", "event_date", "location", "guest_count", "budget_amount"],
)
def test_missing_required_fields_are_rejected(
    field: str,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    payload = event_payload()
    payload.pop(field)

    response = client.post("/api/v1/events", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert f"body.{field}" in _field_paths(response)


@pytest.mark.parametrize("field", ["event_id", "created_at", "updated_at"])
def test_clients_cannot_supply_server_managed_fields(
    field: str,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    response = client.post(
        "/api/v1/events",
        json=event_payload(**{field: "client-controlled"}),
    )

    assert response.status_code == 422
    assert f"body.{field}" in _field_paths(response)


def test_unknown_event_fields_are_rejected(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    response = client.post(
        "/api/v1/events",
        json=event_payload(secret_note="must not be stored"),
    )

    assert response.status_code == 422
    assert "body.secret_note" in _field_paths(response)
    assert "must not be stored" not in response.text


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "   "),
        ("name", "x" * 101),
        ("location", "\t"),
        ("location", "x" * 201),
        ("description", "x" * 2_001),
    ],
)
def test_invalid_text_fields_are_rejected(
    field: str,
    value: str,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    response = client.post(
        "/api/v1/events",
        json=event_payload(**{field: value}),
    )

    assert response.status_code == 422
    assert f"body.{field}" in _field_paths(response)


@pytest.mark.parametrize(
    "event_date",
    ["2030-06-15T10:00:00", "15-06-2030", "2030-02-30", "not-a-date"],
)
def test_invalid_event_date_formats_are_rejected(
    event_date: str,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    response = client.post(
        "/api/v1/events",
        json=event_payload(event_date=event_date),
    )

    assert response.status_code == 422
    assert "body.event_date" in _field_paths(response)


def test_past_event_date_is_rejected_using_configured_timezone(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    response = client.post(
        "/api/v1/events",
        json=event_payload(event_date="2030-05-14"),
    )

    assert response.status_code == 422
    assert "body.event_date" in _field_paths(response)
    assert "Asia/Kolkata" in response.text


def test_event_today_is_accepted(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(
        client,
        event_payload,
        event_date=FIXED_NOW.date().isoformat(),
    )

    assert event["event_date"] == "2030-05-15"


@pytest.mark.parametrize("guest_count", [0, -1, True, 1.5, "150", None, 10_001])
def test_invalid_guest_counts_are_rejected(
    guest_count: Any,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    response = client.post(
        "/api/v1/events",
        json=event_payload(guest_count=guest_count),
    )

    assert response.status_code == 422
    assert "body.guest_count" in _field_paths(response)


def test_guest_count_upper_boundary_is_accepted(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(client, event_payload, guest_count=10_000)

    assert event["guest_count"] == 10_000


@pytest.mark.parametrize(
    "budget_amount",
    ["-1", "0", "0.001", "100000000.01", "not-a-number", "NaN", "Infinity", True, None],
)
def test_invalid_budget_amounts_are_rejected(
    budget_amount: Any,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    response = client.post(
        "/api/v1/events",
        json=event_payload(budget_amount=budget_amount),
    )

    assert response.status_code == 422
    assert "body.budget_amount" in _field_paths(response)


@pytest.mark.parametrize("non_finite", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_json_budget_numbers_are_rejected(
    non_finite: str,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    payload = event_payload(budget_amount="__NON_FINITE__")
    raw_body = json.dumps(payload).replace('"__NON_FINITE__"', non_finite)

    response = client.post(
        "/api/v1/events",
        content=raw_body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert "body.budget_amount" in _field_paths(response)


def test_fractional_json_budget_is_preserved_as_decimal_string(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(client, event_payload, budget_amount=0.1)

    assert event["budget_amount"] == "0.10"


@pytest.mark.parametrize("currency", ["IN", "RUPEE", "I1R", "₹", 150, None])
def test_invalid_currencies_are_rejected(
    currency: Any,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    response = client.post(
        "/api/v1/events",
        json=event_payload(currency=currency),
    )

    assert response.status_code == 422
    assert "body.currency" in _field_paths(response)


@pytest.mark.parametrize("currency", ["inr", " usd "])
def test_currency_codes_are_normalized(
    currency: str,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(client, event_payload, currency=currency)

    assert event["currency"] == currency.strip().upper()


def test_excessive_preferences_are_rejected(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    response = client.post(
        "/api/v1/events",
        json=event_payload(preferences=[f"Preference {index}" for index in range(21)]),
    )

    assert response.status_code == 422
    assert "body.preferences" in _field_paths(response)


@pytest.mark.parametrize(
    "field,value",
    [
        ("preferences", ["valid", " "]),
        ("preferences", ["x" * 201]),
        ("preferences", "Pastel decor"),
        ("constraints", [f"Constraint {index}" for index in range(21)]),
        ("constraints", ["valid", ""]),
        ("constraints", "No loud music"),
    ],
)
def test_invalid_preferences_and_constraints_are_rejected(
    field: str,
    value: Any,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    response = client.post(
        "/api/v1/events",
        json=event_payload(**{field: value}),
    )

    assert response.status_code == 422
    assert any(path.startswith(f"body.{field}") for path in _field_paths(response))


def test_empty_event_list_has_stable_pagination_metadata(client: TestClient) -> None:
    response = client.get("/api/v1/events")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_get_event_returns_created_event(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    created = _create_event(client, event_payload)

    response = client.get(f"/api/v1/events/{created['event_id']}")

    assert response.status_code == 200
    assert response.json() == created


@pytest.mark.parametrize(
    "event_id",
    [
        str(uuid4()),
        "not-a-uuid",
        "{00000000-0000-4000-8000-000000000000}",
        "0" * 36,
    ],
)
def test_missing_or_invalid_event_ids_return_consistent_not_found(
    event_id: str,
    client: TestClient,
) -> None:
    response = client.get(f"/api/v1/events/{event_id}")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "The requested resource was not found.",
        }
    }
    assert "Traceback" not in response.text


def test_event_listing_preserves_creation_order(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    created = [
        _create_event(client, event_payload, name=name)
        for name in ("First Event", "Second Event", "Third Event")
    ]

    first_response = client.get("/api/v1/events")
    second_response = client.get("/api/v1/events")

    assert first_response.status_code == 200
    assert first_response.json()["total"] == 3
    assert [item["event_id"] for item in first_response.json()["items"]] == [
        event["event_id"] for event in created
    ]
    assert first_response.json() == second_response.json()


def test_event_listing_supports_bounded_pagination(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    created = [
        _create_event(client, event_payload, name=name)
        for name in ("First Event", "Second Event", "Third Event")
    ]

    response = client.get("/api/v1/events", params={"limit": 2, "offset": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["limit"] == 2
    assert payload["offset"] == 1
    assert [item["event_id"] for item in payload["items"]] == [
        created[1]["event_id"],
        created[2]["event_id"],
    ]

    past_end = client.get("/api/v1/events", params={"limit": 2, "offset": 3})
    assert past_end.status_code == 200
    assert past_end.json()["items"] == []
    assert past_end.json()["total"] == 3


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"limit": "invalid"},
        {"offset": -1},
        {"offset": 1_000_001},
    ],
)
def test_invalid_pagination_is_rejected(
    params: dict[str, Any],
    client: TestClient,
) -> None:
    response = client.get("/api/v1/events", params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_partial_update_changes_only_supplied_fields(
    client: TestClient,
    event_payload: EventPayloadFactory,
    clock: MutableClock,
) -> None:
    created = _create_event(client, event_payload)
    clock.now = FIXED_NOW + timedelta(seconds=30)

    response = client.patch(
        f"/api/v1/events/{created['event_id']}",
        json={"name": "Updated Wedding Name"},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Updated Wedding Name"
    assert updated["location"] == created["location"]
    assert updated["event_date"] == created["event_date"]
    assert updated["created_at"] == created["created_at"]
    assert _timezone_aware(updated["updated_at"]) == clock.now
    assert updated["updated_at"] != created["updated_at"]


def test_empty_or_noop_update_does_not_change_updated_at(
    client: TestClient,
    event_payload: EventPayloadFactory,
    clock: MutableClock,
) -> None:
    created = _create_event(client, event_payload)
    clock.now = FIXED_NOW + timedelta(days=1)

    empty_response = client.patch(
        f"/api/v1/events/{created['event_id']}",
        json={},
    )
    noop_response = client.patch(
        f"/api/v1/events/{created['event_id']}",
        json={"name": created["name"], "guest_count": created["guest_count"]},
    )

    assert empty_response.status_code == 200
    assert noop_response.status_code == 200
    assert empty_response.json()["updated_at"] == created["updated_at"]
    assert noop_response.json()["updated_at"] == created["updated_at"]


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "event_type",
        "event_date",
        "location",
        "guest_count",
        "budget_amount",
        "currency",
        "preferences",
        "constraints",
    ],
)
def test_null_non_nullable_updates_are_rejected(
    field: str,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    created = _create_event(client, event_payload)

    response = client.patch(
        f"/api/v1/events/{created['event_id']}",
        json={field: None},
    )

    assert response.status_code == 422
    assert f"body.{field}" in _field_paths(response)


def test_description_preferences_and_constraints_can_be_cleared(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    created = _create_event(client, event_payload)

    response = client.patch(
        f"/api/v1/events/{created['event_id']}",
        json={"description": None, "preferences": [], "constraints": []},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["description"] is None
    assert updated["preferences"] == []
    assert updated["constraints"] == []


@pytest.mark.parametrize(
    "changes",
    [
        {"name": " "},
        {"event_type": "festival"},
        {"event_date": "not-a-date"},
        {"event_date": "2029-12-31"},
        {"location": ""},
        {"guest_count": 0},
        {"guest_count": True},
        {"budget_amount": "-1"},
        {"budget_amount": "0.001"},
        {"currency": "IN"},
        {"preferences": [f"Preference {index}" for index in range(21)]},
        {"constraints": [" "]},
    ],
)
def test_invalid_updates_are_rejected(
    changes: dict[str, Any],
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    created = _create_event(client, event_payload)

    response = client.patch(
        f"/api/v1/events/{created['event_id']}",
        json=changes,
    )

    assert response.status_code == 422
    field = next(iter(changes))
    assert any(path.startswith(f"body.{field}") for path in _field_paths(response))


@pytest.mark.parametrize("field", ["event_id", "created_at", "updated_at"])
def test_clients_cannot_update_server_managed_fields(
    field: str,
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    created = _create_event(client, event_payload)

    response = client.patch(
        f"/api/v1/events/{created['event_id']}",
        json={field: "client-controlled"},
    )

    assert response.status_code == 422
    assert f"body.{field}" in _field_paths(response)


def test_unknown_update_fields_are_rejected(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    created = _create_event(client, event_payload)

    response = client.patch(
        f"/api/v1/events/{created['event_id']}",
        json={"secret_note": "must not be stored"},
    )

    assert response.status_code == 422
    assert "body.secret_note" in _field_paths(response)
    assert "must not be stored" not in response.text


def test_updating_missing_or_invalid_event_returns_not_found(
    client: TestClient,
) -> None:
    for event_id in (str(uuid4()), "not-a-uuid"):
        response = client.patch(
            f"/api/v1/events/{event_id}",
            json={"name": "Updated"},
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


def test_delete_removes_only_the_requested_event(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    first = _create_event(client, event_payload, name="First Event")
    second = _create_event(client, event_payload, name="Second Event")

    response = client.delete(f"/api/v1/events/{first['event_id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/v1/events/{first['event_id']}").status_code == 404

    remaining = client.get(f"/api/v1/events/{second['event_id']}")
    assert remaining.status_code == 200
    assert remaining.json()["name"] == "Second Event"
    assert client.get("/api/v1/events").json()["total"] == 1


def test_deleting_missing_or_invalid_event_returns_not_found_or_repeat_delete(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    created = _create_event(client, event_payload)
    assert client.delete(f"/api/v1/events/{created['event_id']}").status_code == 204

    repeat = client.delete(f"/api/v1/events/{created['event_id']}")
    missing = client.delete(f"/api/v1/events/{uuid4()}")
    malformed = client.delete("/api/v1/events/not-a-uuid")

    assert repeat.status_code == 404
    assert missing.status_code == 404
    assert malformed.status_code == 404
    assert malformed.json()["error"]["code"] == "not_found"


def test_separate_application_instances_have_isolated_event_storage(
    client: TestClient,
    event_payload: EventPayloadFactory,
    make_settings: Callable[..., Settings],
) -> None:
    _create_event(client, event_payload)

    with TestClient(create_app(make_settings())) as other_client:
        response = other_client.get("/api/v1/events")

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_event_error_responses_do_not_echo_sensitive_input(
    client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    sensitive_value = "private-guest-medical-note-3d9a"

    response = client.post(
        "/api/v1/events",
        json=event_payload(
            description=sensitive_value,
            guest_count=-5,
            secret_note=sensitive_value,
        ),
    )

    assert response.status_code == 422
    assert sensitive_value not in response.text
    assert "Traceback" not in response.text
    assert "C:\\" not in response.text
